# Proposal: rebot-console-options

## Why

Robot Framework 7.5 gives `rebot` the `--console verbose|quiet|none|<custom console>` and `--quiet` options (#5674, #5618). `robot.toml` cannot express them: `RebotOptions` has no `console`/`quiet` field, so `[rebot] console = "quiet"` is silently ignored today (unknown keys are dropped by the loader) and users must pass the options on the command line. The compatibility change `support-rf75` deliberately keeps `console`/`quiet` as `robot`-only options; this change adds the `rebot` counterparts on top of it.

## What Changes

- `[rebot]` gains `console` (built-in names `verbose`, `quiet`, `none`, or any other string as a custom console class/module such as `path/to/Console.py:arg`) and `quiet`, generated from Robot Framework's own `rebot` help like every other option, with TOML examples.
- `robotcode rebot` passes them to `rebot` like every other option, on every Robot Framework version. `rebot` of Robot Framework < 7.5 rejects them itself (`option --console not a unique prefix`), which is check enough (maintainer decision; a first implementation dropped them with a verbose note on older versions).
- The profile's top-level `console` and `quiet` are **not** copied into the `rebot` profile, mirroring Robot Framework, which excludes `ConsoleType`/`ConsoleTypeQuiet` when deriving rebot settings from robot settings. This keeps `support-rf75`'s guarantee that a top-level `console = "dotted"` never reaches `rebot`.
- The generator `scripts/generate_rf_options.py` learns tool-specific type and example overrides so `rebot`'s `console` type (no `dotted`) differs from `robot`'s.
- Model, JSON schema and `docs/03_reference/config.md` are regenerated with the sequence `support-rf75` documents.
- The `--dry` message of `robotcode rebot` says "Would execute rebot" instead of "libdoc".

Depends on `support-rf75` (repaired generator, `rf75` environment, regeneration procedure); must be applied after it.

## Capabilities

### New Capabilities

- `robot-toml-option-coverage`: adds the requirement "Rebot console options" to the capability introduced by `support-rf75` (not yet archived): `[rebot] console`/`quiet` are accepted, forwarded to `rebot`, and independent of the top-level `console`/`quiet`.

### Modified Capabilities

<!-- none — the capability exists only as a delta of support-rf75 -->

## Impact

- `scripts/generate_rf_options.py`: tool-aware `type_templates`/`TOML_EXAMPLES` lookup, `RebotOptions` built from `RebotSettings._extra_cli_opts` plus `ConsoleType`/`ConsoleTypeQuiet`.
- `packages/robot/src/robotcode/robot/config/model.py`: regenerated region (`RebotOptions.console`, `RebotOptions.quiet`), nothing else.
- `packages/runner/src/robotcode/runner/cli/rebot.py`: exclusion of top-level `console`/`quiet`, dry-run message.
- `docs/public/schemas/robot.toml.json`, `docs/03_reference/config.md`: regenerated.
- Tests: `tests/robotcode/robot/config/test_model.py`, `test_profile.py`, the rebot dry-run test module from `support-rf75` under `tests/robotcode/runner/cli/` (extended; `test_rebot.py` if none exists), `tests/robotcode/runner/cli/rf_markers.py` (`needs_rf_75`, shared with `rf75-test-metadata`).
- No change to the VS Code extension (schema is fetched from robotcode.io) or the IntelliJ plugin.
