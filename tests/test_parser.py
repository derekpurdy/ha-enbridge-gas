"""Tests for parsing Enbridge billing exports and generating statistics."""

from datetime import date, timezone
from decimal import Decimal
import importlib.util
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

PARSER_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "enbridge_gas"
    / "parser.py"
)
PARSER_SPEC = importlib.util.spec_from_file_location(
    "enbridge_gas_parser", PARSER_PATH
)
if PARSER_SPEC is None or PARSER_SPEC.loader is None:
    raise RuntimeError("Unable to load the Enbridge parser for tests")
PARSER_MODULE = importlib.util.module_from_spec(PARSER_SPEC)
sys.modules[PARSER_SPEC.name] = PARSER_MODULE
PARSER_SPEC.loader.exec_module(PARSER_MODULE)
ExportError = PARSER_MODULE.ExportError
build_hourly_statistics = PARSER_MODULE.build_hourly_statistics
parse_export = PARSER_MODULE.parse_export


class ParseExportTests(unittest.TestCase):
    """Verify Enbridge CSV/XML parsing and historical statistics."""

    def test_parses_enbridge_csv_and_sorts_periods(self):
        """CSV billing rows are parsed regardless of their input order."""
        contents = (
            "Billed From,Billed To,Consumption M3,Name\n"
            "02/01/2026,02/02/2026,48,Private Customer\n"
            "01/01/2026,01/31/2026,62,Private Customer\n"
        )

        periods = parse_export("invoice.csv", contents)

        self.assertEqual(
            [
                (period.start, period.end, period.consumption_m3)
                for period in periods
            ],
            [
                (date(2026, 1, 1), date(2026, 1, 31), Decimal("62")),
                (date(2026, 2, 1), date(2026, 2, 2), Decimal("48")),
            ],
        )

    def test_parses_xml_records(self):
        """Flat XML invoice fields are mapped to billing periods."""
        contents = """\
        <Invoices>
          <Invoice>
            <BilledFrom>2026-01-01</BilledFrom>
            <BilledTo>2026-01-02</BilledTo>
            <ConsumptionM3>10.5</ConsumptionM3>
          </Invoice>
        </Invoices>
        """

        periods = parse_export("invoice.xml", contents)

        self.assertEqual(periods[0].consumption_m3, Decimal("10.5"))

    def test_rejects_overlapping_billing_periods(self):
        """Overlapping periods cannot silently double-count gas usage."""
        contents = (
            "Billed From,Billed To,Consumption M3\n"
            "01/01/2026,01/03/2026,10\n"
            "01/03/2026,01/04/2026,5\n"
        )

        with self.assertRaisesRegex(ExportError, "overlap"):
            parse_export("invoice.csv", contents)

    def test_rejects_xml_entity_declarations(self):
        """XML entity expansion is not accepted in uploaded files."""
        contents = (
            '<!DOCTYPE invoice [<!ENTITY usage "10">]>'
            "<Invoice><BilledFrom>2026-01-01</BilledFrom></Invoice>"
        )

        with self.assertRaisesRegex(ExportError, "entity declarations"):
            parse_export("invoice.xml", contents)

    def test_hourly_statistics_preserve_period_total(self):
        """The generated hourly profile accumulates to the billed quantity."""
        periods = parse_export(
            "invoice.csv",
            "Billed From,Billed To,Consumption M3\n"
            "01/01/2026,01/01/2026,24\n",
        )

        statistics = build_hourly_statistics(periods, timezone.utc)

        self.assertEqual(len(statistics), 24)
        self.assertEqual(statistics[-1]["sum"], 24.0)
        self.assertEqual(statistics[0]["sum"], 1.0)

    def test_hourly_statistics_respect_daylight_saving_time(self):
        """Local billing dates have 23 or 25 real hours across DST changes."""
        spring_period = parse_export(
            "invoice.csv",
            "Billed From,Billed To,Consumption M3\n"
            "03/08/2026,03/08/2026,23\n",
        )
        fall_period = parse_export(
            "invoice.csv",
            "Billed From,Billed To,Consumption M3\n"
            "11/01/2026,11/01/2026,25\n",
        )

        spring_stats = build_hourly_statistics(
            spring_period, ZoneInfo("America/Toronto")
        )
        fall_stats = build_hourly_statistics(
            fall_period, ZoneInfo("America/Toronto")
        )

        self.assertEqual(len(spring_stats), 23)
        self.assertEqual(spring_stats[-1]["sum"], 23.0)
        self.assertEqual(len(fall_stats), 25)
        self.assertEqual(fall_stats[-1]["sum"], 25.0)

    def test_daily_totals_are_equal_across_daylight_saving_time(self):
        """DST changes do not change the estimated usage for a calendar day."""
        periods = parse_export(
            "invoice.csv",
            "Billed From,Billed To,Consumption M3\n"
            "03/07/2026,03/09/2026,30\n",
        )
        local_timezone = ZoneInfo("America/Toronto")
        statistics = build_hourly_statistics(periods, local_timezone)

        daily_totals = {}
        previous_sum = 0.0
        for statistic in statistics:
            daily_total = daily_totals.setdefault(
                statistic["start"].astimezone(local_timezone).date(), 0.0
            )
            delta = statistic["sum"] - previous_sum
            daily_totals[
                statistic["start"].astimezone(local_timezone).date()
            ] = daily_total + delta
            previous_sum = statistic["sum"]

        self.assertEqual(list(daily_totals.values()), [10.0, 10.0, 10.0])


if __name__ == "__main__":
    unittest.main()
