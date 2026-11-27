# Agent instructions

## Project

This repository contains a Home Assistant custom integration for importing
Enbridge Gas billing history into the `enbridge_gas:gas_usage` Energy
dashboard statistic. Integration code is in `custom_components/enbridge_gas/`;
tests are in `tests/`.

## Working guidelines

- Read the relevant integration code and tests before making changes.
- Keep changes focused and follow existing Home Assistant conventions.
- Treat invoice data as sensitive. Do not log, persist, or commit account
  numbers, customer names, service addresses, or raw exports. Use synthetic
  test data only.
- Validate unsupported or malformed input explicitly. Preserve billing totals
  and clearly describe estimated daily/hourly usage derived from
  billing-period totals.
- Do not describe XML support as verified without a representative Enbridge
  XML sample and a corresponding test.
- Update the README when import behavior or supported formats change.

## Validation

Run the relevant checks before finishing:

```sh
python3 -m unittest discover -s tests -v
node --check custom_components/enbridge_gas/www/enbridge-gas-panel.js
```

See [Copilot instructions](.github/copilot-instructions.md),
[integration instructions](.github/instructions/enbridge-gas.instructions.md),
and [the import skill](.github/skills/enbridge-gas-import/SKILL.md) for
additional project guidance.
