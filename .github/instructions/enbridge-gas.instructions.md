---
description: >-
  Project-specific instructions for the Enbridge Gas Home Assistant
  integration.
applyTo: "**/*.py"
---

- Follow Home Assistant integration conventions and existing project patterns.
- Keep imported data local and limit persisted statistics to billing dates and
  gas consumption. Never log or store customer identifiers or invoice data.
- Validate date ranges, consumption values, overlapping periods, file size,
  and supported formats explicitly.
- Preserve the total billed cubic metres when converting billing periods to
  hourly cumulative statistics. Allocate evenly per local date before
  distributing each date's total across its hours, using the configured
  Home Assistant time zone and accounting for daylight-saving transitions.
- Use synthetic fixtures only. Do not commit Enbridge account numbers, names,
  addresses, or real invoice exports.
- Add focused tests for parser behavior changes and run
  `python3 -m unittest discover -s tests -v`.
- For frontend changes, run
  `node --check custom_components/enbridge_gas/www/enbridge-gas-panel.js`.
- Do not claim the XML parser matches Enbridge's actual export until tested
  against a sanitized representative XML file.
