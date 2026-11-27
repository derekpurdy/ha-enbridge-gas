# Enbridge Gas Usage Import

[![Add to Home Assistant][ha-badge]][ha-config]

[ha-badge]: https://my.home-assistant.io/badges/config_flow_start.svg
[ha-config]:
  https://my.home-assistant.io/redirect/config_flow_start/?domain=enbridge_gas

Import Enbridge Gas invoice history into Home Assistant as an external gas
statistic that can be selected in the Energy dashboard.

## Features

- Upload an Enbridge invoice CSV from the Home Assistant sidebar.
- Parse XML records with equivalent billing-date and consumption fields.
- Import cubic-metre usage as long-term statistics.
- Keep account number, customer name, and service address out of the
  integration and its stored statistics.

CSV support targets the Enbridge invoice export columns `Billed From`,
`Billed To`, and `Consumption M3`. Header matching ignores capitalization,
spaces, and punctuation. XML support expects records with direct child fields
corresponding to those values; no Enbridge XML sample was available to verify
its exact schema. The supplied `.xlsx` example was blank and spreadsheet files
are not supported.

## Installation

1. Add this GitHub repository as a custom integration repository in the
   Home Assistant Marketplace, then install **Enbridge Gas Usage Import**.
2. Select the **Add to Home Assistant** button above to open the integration
   setup flow. The integration must be installed first.
3. Open **Enbridge Gas** in the sidebar and upload the CSV or XML export.
4. In the Energy dashboard settings, add
   `enbridge_gas:gas_usage` as a gas source.

The integration requires the Home Assistant Recorder integration to be
enabled. Uploads are limited to 2 MB. Reimport a corrected export to update
the same statistic.

## Import behavior

- Billing dates are interpreted in the Home Assistant time zone. The end
  date is inclusive.
- Rows are sorted by start date. Empty, invalid, duplicate, or overlapping
  billing periods are rejected instead of silently double-counted.
- The integration imports only dates and gas consumption. Account numbers,
  names, service addresses, and invoice charges are not stored.
- Each import updates the same external statistic. Reimporting the same
  periods replaces their hourly totals; periods omitted from a later import
  are not removed.

## Historical data handling

Enbridge invoice exports provide a total for each billing period, not daily or
hourly readings. The importer divides each period's total evenly across its
inclusive billing dates, then across the actual hours in each date. This keeps
daily estimates consistent across daylight-saving changes and preserves the
billing-period total. Since the export has no daily readings, dates in the
same billing period will have similar estimated usage; actual daily variation
cannot be inferred. The hourly and daily values are estimates, not meter
readings. After updating the integration's allocation logic, upload the same
export again to replace matching historical statistics.

The uploaded file is parsed in memory and is not saved. Home Assistant
Recorder retains the resulting gas statistics.

## Development

The integration source is in `custom_components/enbridge_gas/`. Parser tests
run with Python 3:

```sh
python3 -m unittest discover -s tests -v
node --check custom_components/enbridge_gas/www/enbridge-gas-panel.js
```

Tests use synthetic data only. Do not commit real Enbridge exports; invoice
files can include account identifiers, names, and service addresses.

Project-specific Copilot guidance:

- [Copilot instructions](.github/copilot-instructions.md)
- [Python instructions](.github/instructions/enbridge-gas.instructions.md)
- [Import skill](.github/skills/enbridge-gas-import/SKILL.md)

<!-- marketplace-readme-start -->
This is a community integration. Review and trust its source before installing
it; community integrations run with access to your Home Assistant instance.
<!-- marketplace-readme-end -->
