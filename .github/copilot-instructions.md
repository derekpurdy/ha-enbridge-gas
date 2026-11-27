# Copilot instructions

## Project scope

This repository is a Home Assistant custom integration that imports Enbridge
Gas invoice history into the `enbridge_gas:gas_usage` external statistic for
the Energy dashboard. The implementation is under
`custom_components/enbridge_gas/`; parser tests are under `tests/`.

## Change guidelines

- Keep changes focused on Enbridge file import, Home Assistant integration
  behavior, or directly related documentation and tests.
- Preserve Home Assistant config-flow, WebSocket, statistics, and entity
  conventions. Keep uploads admin-only and local to Home Assistant.
- Treat uploaded statements and fixtures as sensitive. Do not log, persist,
  or commit account numbers, customer names, service addresses, or raw user
  exports. Use synthetic data in tests.
- Validate the file format and billing data explicitly. Reject malformed or
  ambiguous data with a useful error rather than silently skipping rows.
- Preserve the billed volume when generating statistics. The integration
  distributes each period evenly across inclusive local dates and then across
  each date's hours because invoices provide period totals, not interval
  readings. Keep that limitation clear in user-facing documentation.
- Do not claim verified XML compatibility without a representative Enbridge
  XML sample and a test for its schema.
- Avoid new runtime dependencies unless Home Assistant does not already
  provide the needed capability.

## Validation

Run the focused checks after relevant changes:

```sh
python3 -m unittest discover -s tests -v
node --check custom_components/enbridge_gas/www/enbridge-gas-panel.js
```

When changing parser behavior, add synthetic tests for valid data and the
relevant invalid or boundary cases. Do not use real invoice exports as test
fixtures.
