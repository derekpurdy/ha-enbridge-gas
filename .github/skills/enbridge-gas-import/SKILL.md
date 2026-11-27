---
name: enbridge-gas-import
description: >-
  Implement or update support for Enbridge Gas billing export formats and
  Home Assistant gas statistics in this repository.
---

# Enbridge Gas import skill

Use this skill when changing CSV/XML statement parsing, upload validation,
historical statistic generation, or the corresponding import documentation.

## Workflow

1. Inspect the current parser, upload WebSocket handler, tests, and README
   before changing behavior.
2. Confirm any proposed field names and date/number formats against a
   sanitized representative export. If no sample exists, clearly state the
   unverified assumptions; do not imply the format is confirmed.
3. Keep the import local. Never log, persist, or add raw invoice data or
   customer identifiers to fixtures.
4. Validate headers/fields, dates, finite nonnegative consumption, file size,
   period ordering, and duplicate or overlapping periods. Return actionable
   errors for invalid input.
5. Ensure period totals remain unchanged in cumulative external statistics.
   Treat billing end dates as inclusive, distribute usage evenly by local
   calendar date, and use Home Assistant's configured time zone when expanding
   dates into hours.
6. Update the README when supported formats, installation, errors, or
   estimation behavior changes.
7. Add focused synthetic tests and run:

   ```sh
   python3 -m unittest discover -s tests -v
   node --check custom_components/enbridge_gas/www/enbridge-gas-panel.js
   ```

## Current format notes

- The verified CSV fields are `Billed From`, `Billed To`, and
  `Consumption M3`; matching normalizes case, spaces, and punctuation.
- XML support is provisional and expects equivalent direct child fields. A
  real Enbridge XML sample has not yet verified this assumption.
- `.xlsx` is not supported.
- Enbridge provides billing-period totals, not hourly readings. Hourly values
  are estimated from even daily allocations and must be described as
  estimates.
