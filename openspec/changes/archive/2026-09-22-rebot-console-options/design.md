# Design: rebot-console-options

## Context

See proposal.md. Facts that shape the approach (verified in the repository and the unpacked RF 7.4.2/7.5 sources):

- RF 7.5 moved `ConsoleType`/`ConsoleTypeQuiet` into `_BaseSettings._cli_opts` (`robot/conf/settings.py`), so `RebotSettings` has them; `rebot`'s help defines `--console console` (the built-in names `verbose`, `quiet`, `none` appear only in the description, no `dotted`) and `--quiet`. Because the parameter token is `console` and not a `|`-separated list, the generator cannot derive a `Literal` from it — hence the type override in D2. RF's own `RobotSettings.get_rebot_settings` lists `ConsoleType`/`ConsoleTypeQuiet` in `not_copied`, i.e. RF never carries robot's console type into rebot settings. RF 7.5 `ConsoleOutput` maps the built-in names case-insensitively and hands any other string to `ListenerFacade.create(kind="console logger")`; RF 7.4.2 rejects `--console` (`option --console not a unique prefix`) and `--quiet`/`--noquiet` (`option … not recognized`) for `rebot`, rc 252, also when RobotCode passes them through.
- `scripts/generate_rf_options.py` builds `RebotOptions` from `RebotSettings._extra_cli_opts` (which never contains the two options), so they are parsed from the USAGE text and dropped. `type_templates` and `TOML_EXAMPLES` are keyed by field/option name only, so `console` shares one type with `RobotOptions.console`. `support-rf75` (D4) already repairs the generator and builds the option dicts explicitly; this change must run after it.
- `BaseOptions.add_options` (`model.py` ≈296-353) copies every same-named, non-`None` field of the top-level profile into the tool profile, top-level winning; `rebot.py` calls it before `build_command_line`. Today `[rebot] console`/`quiet` are silently ignored by the loader (unknown keys), and no test covers `RebotProfile` or `robotcode rebot`.
- `rebot.py` already has an `RF_VERSION >= (7, 1)` guard for `--consolelinks` and uses `ignore_unknown_options` pass-through; its `--dry` message says "Would execute libdoc" (copy-paste).
- `support-rf75`'s spec requires that the top-level `console`/`quiet` never reach `rebot`, and its task 3.3 tests exactly that with `robotcode --dry rebot`.

## Goals / Non-Goals

**Goals:**
- `[rebot] console`/`quiet` configurable like every other option, generated from RF's help.
- Keep `support-rf75`'s guarantee and RF's own semantics: top-level console settings are robot-only.

**Non-Goals:**
- Any change to how other shared options flow between top level and tool sections.
- A `dotted` console for rebot (RF does not list it; as any string it still validates and RF 7.5 accepts it).
- Any RobotCode-side version check for the two options: `rebot` of Robot Framework < 7.5 rejects them itself with a clear error, exactly like a mistyped option (maintainer decision; a guard that dropped them with a verbose note was implemented first and removed again).

## Decisions

### D1: Top-level `console`/`quiet` are kept out of the rebot profile locally

`rebot.py` remembers the `[rebot]` values of `console` and `quiet` before `add_options(profile)` and puts them back afterwards (three lines, with a comment pointing at RF's `get_rebot_settings`). Without that, a top-level `console = "dotted"` — the first example in the configuration reference — would flow into `rebot` like every other shared option and make `robotcode rebot` fail on RF ≤ 7.4 (`option --console not a unique prefix`) for a setting the user never made for `rebot`; `support-rf75`'s scenario "Top-level console does not reach rebot" guards exactly that. A generic `exclude` parameter on `BaseOptions.add_options` was implemented first and removed by maintainer decision: no change to the shared model for a `rebot`-only concern.

### D2: Tool-aware generator overrides

`type_templates` and `TOML_EXAMPLES` accept tool-prefixed keys (`"rebot:console"`, `"rebot:--console"`) looked up before the plain key; `get_type` and `apply_toml_examples` receive the `tool` that `generate()` already knows. `RebotOptions` is built from `RebotSettings._extra_cli_opts` plus `ConsoleType`/`ConsoleTypeQuiet` taken from `RebotSettings._cli_opts` when present (so the generator still runs under RF 7.4 for `support-rf75`'s diff check). The rebot `console` type becomes `Union[str, Literal["verbose", "quiet", "none"]]`; `quiet` is a flag like robot's. Nested per-tool dicts were considered and rejected as more code for the same effect.

### D3: No version guard

`[rebot] console`/`quiet` are built into the command line on every Robot Framework version; `rebot` of Robot Framework < 7.5 rejects them with its own error (`option --console not a unique prefix`, `option --quiet not recognized`) and exit code 252, as it does for any option it does not know (before 7.1, where `--consolelinks` does not exist, `rebot` reads `--console` as the unique prefix of `--consolecolors` and rejects the value instead: `Invalid console color value 'quiet'`; the run fails either way). A guard that dropped the two fields with a verbose note on RF < 7.5 was implemented first and removed by maintainer decision: the setting is a deliberate one in the `[rebot]` section, and the error names it.

### D4: Regeneration and dry-run message

Model, schema and `config.md` are regenerated with the sequence `support-rf75` documents (generator under an RF 7.5 interpreter → `lint:fix` → `create-json-schema` → `robotcode config info desc`); expected structural diff: two new `RebotOptions` fields (`console` first, `quiet` after `process_empty_suite`), nothing else. The `--dry` message typo is fixed in the same change because the new tests assert on that output.

## Risks / Trade-offs

- [Runs the generator; `support-rf75` must be applied first] → stated dependency; the generator refuses nothing by itself, so the task list starts with a check that `support-rf75` tasks 3.1–3.2 are done.
- [`[rebot] console` on RF < 7.5 fails the run] → `rebot`'s own error names the option; the configuration reference shows the options only for the newest supported Robot Framework anyway.
- [Schema advertises the options on every RF version] → same as all version-specific options.
- [Field order in `RebotOptions` changes (`console` first)] → affects `as_dict()`/`save()` key order only.

## Migration Plan

Additive; no migration. Users who passed `--console quiet` on the `robotcode rebot` command line can move it to `[rebot]`.
