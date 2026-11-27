"""Parse Enbridge billing exports and prepare hourly external statistics."""

import csv
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from decimal import Decimal, InvalidOperation
from io import StringIO
import re
from typing import TypedDict
import xml.etree.ElementTree as ET

MAX_PERIODS = 2_000
MAX_STATISTIC_HOURS = 100_000
XML_UNSAFE_DECLARATION = re.compile(
    r"<!\s*(?:DOCTYPE|ENTITY)\b", re.IGNORECASE
)

FIELD_ALIASES = {
    "start": {"billedfrom", "billingfrom", "periodstart", "fromdate"},
    "end": {"billedto", "billingto", "periodend", "todate"},
    "consumption": {
        "consumptionm3",
        "gasconsumptionm3",
        "gasusage",
        "consumption",
        "volume",
    },
}


class ExportError(ValueError):
    """An uploaded export is invalid or cannot be interpreted."""


@dataclass(frozen=True)
class BillingPeriod:
    """A billed usage total and its inclusive billing dates."""

    start: date
    end: date
    consumption_m3: Decimal


class HourlyStatistic(TypedDict):
    """A cumulative gas statistic at the start of an hour."""

    start: datetime
    sum: float


def parse_export(filename: str, contents: str) -> list[BillingPeriod]:
    """Parse a supported Enbridge CSV or XML export."""
    if not contents.strip():
        raise ExportError("The selected file is empty")
    if filename.lower().endswith(".csv"):
        periods = _parse_csv(contents)
    elif filename.lower().endswith(".xml"):
        periods = _parse_xml(contents)
    else:
        raise ExportError("Choose an Enbridge CSV or XML export")

    return _validate_periods(periods)


def _parse_csv(contents: str) -> list[BillingPeriod]:
    """Read periods from Enbridge's invoice CSV columns."""
    contents = contents.lstrip("\ufeff")
    try:
        dialect = csv.Sniffer().sniff(contents[:8192], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel

    reader = csv.reader(StringIO(contents), dialect)
    headers = next(reader, None)
    if not headers:
        raise ExportError("The CSV file does not contain a header row")

    field_indexes = _resolve_fields(
        {_normalize(header): index for index, header in enumerate(headers)}
    )
    periods = []
    for row in reader:
        if not any(value.strip() for value in row):
            continue
        values = {
            field: row[index].strip() if index < len(row) else ""
            for field, index in field_indexes.items()
        }
        periods.append(_period_from_values(values))
    return periods


def _parse_xml(contents: str) -> list[BillingPeriod]:
    """Read XML records with direct billing-date and consumption fields."""
    if XML_UNSAFE_DECLARATION.search(contents):
        raise ExportError(
            "XML documents with DTD or entity declarations are not allowed"
        )

    try:
        root = ET.fromstring(contents)
    except ET.ParseError as err:
        raise ExportError("The XML file is not well formed") from err

    candidates = []
    for node in root.iter():
        values = {
            _normalize(child.tag.rsplit("}", 1)[-1]): "".join(
                child.itertext()
            ).strip()
            for child in node
        }
        if _has_required_fields(values):
            candidates.append(values)

    if not candidates:
        raise ExportError(
            "XML records must contain Billed From, Billed To, "
            "and Consumption M3 fields"
        )

    return [
        _period_from_values(_resolve_values(values)) for values in candidates
    ]


def _normalize(value: str) -> str:
    """Normalize a CSV header or XML tag for alias matching."""
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _has_required_fields(values: dict[str, object]) -> bool:
    """Return whether a mapping contains all required bill fields."""
    return all(
        any(alias in values for alias in aliases)
        for aliases in FIELD_ALIASES.values()
    )


def _resolve_fields(headers: dict[str, int]) -> dict[str, int]:
    """Map required field names to CSV column positions."""
    result = {}
    for field, aliases in FIELD_ALIASES.items():
        match = next(
            (headers[alias] for alias in aliases if alias in headers),
            None,
        )
        if match is None:
            raise ExportError(
                "CSV headers must include Billed From, Billed To, "
                "and Consumption M3"
            )
        result[field] = match
    return result


def _resolve_values(values: dict[str, str]) -> dict[str, str]:
    """Map XML child tags to the required bill fields."""
    result = {}
    for field, aliases in FIELD_ALIASES.items():
        match = next(
            (values[alias] for alias in aliases if alias in values),
            None,
        )
        if match is None:
            raise ExportError(
                "An XML billing record is missing a required field"
            )
        result[field] = match
    return result


def _period_from_values(values: dict[str, str]) -> BillingPeriod:
    """Validate a parsed row and convert it to a billing period."""
    start = _parse_date(values["start"])
    end = _parse_date(values["end"])
    consumption = _parse_consumption(values["consumption"])
    if end < start:
        raise ExportError("A billing period ends before it starts")
    return BillingPeriod(start, end, consumption)


def _parse_date(value: str) -> date:
    """Parse Enbridge's month/day/year dates and ISO dates."""
    value = value.strip()
    try:
        return date.fromisoformat(value)
    except ValueError:
        try:
            return datetime.strptime(value, "%m/%d/%Y").date()
        except ValueError as err:
            raise ExportError(f"Invalid billing date: {value}") from err


def _parse_consumption(value: str) -> Decimal:
    """Parse a nonnegative gas volume in cubic metres."""
    cleaned = value.casefold().replace("m³", "").replace("m3", "")
    cleaned = cleaned.replace(",", "").strip()
    try:
        consumption = Decimal(cleaned)
    except InvalidOperation as err:
        raise ExportError(
            "A billing row has an invalid Consumption M3 value"
        ) from err
    if not consumption.is_finite() or consumption < 0:
        raise ExportError(
            "Consumption M3 values must be finite and nonnegative"
        )
    return consumption


def _validate_periods(periods: list[BillingPeriod]) -> list[BillingPeriod]:
    """Sort periods and reject empty, excessive, or overlapping exports."""
    if not periods:
        raise ExportError("No billing periods were found in the selected file")
    if len(periods) > MAX_PERIODS:
        raise ExportError(
            f"Exports may contain at most {MAX_PERIODS} billing periods"
        )

    periods.sort(key=lambda period: (period.start, period.end))
    for previous, current in zip(periods, periods[1:]):
        if current.start <= previous.end:
            raise ExportError(
                "Billing periods overlap or contain duplicate dates"
            )
    return periods


def build_hourly_statistics(
    periods: list[BillingPeriod], local_timezone: tzinfo
) -> list[HourlyStatistic]:
    """Spread each total evenly across local dates and each date's hours."""
    statistics: list[HourlyStatistic] = []
    cumulative = Decimal(0)

    for period in periods:
        day_count = (period.end - period.start).days + 1
        daily_consumption = period.consumption_m3 / day_count

        for day_offset in range(day_count):
            local_start = datetime.combine(
                period.start + timedelta(days=day_offset),
                time.min,
                local_timezone,
            )
            local_end = datetime.combine(
                period.start + timedelta(days=day_offset + 1),
                time.min,
                local_timezone,
            )
            start_utc = local_start.astimezone(timezone.utc)
            end_utc = local_end.astimezone(timezone.utc)
            hours = int((end_utc - start_utc).total_seconds() // 3600)
            if len(statistics) + hours > MAX_STATISTIC_HOURS:
                raise ExportError(
                    "This export spans too many hours to import in one upload"
                )

            hourly_consumption = daily_consumption / hours
            for hour in range(hours):
                cumulative += hourly_consumption
                statistics.append(
                    {
                        "start": start_utc + timedelta(hours=hour),
                        "sum": float(cumulative),
                    }
                )

    return statistics
