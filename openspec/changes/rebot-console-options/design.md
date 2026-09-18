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
- `[rebot] console`/`quiet` configurable like every other option, generated from RF's help, safe on RF < 7.5.
- Keep `support-rf75`'s guarantee and RF's own semantics: top-level console settings are robot-only.

**Non-Goals:**
- Any change to how other shared options flow between top level and tool sections.
- A `dotted` console for rebot (RF does not list it; as any string it still validates and RF 7.5 accepts it).
- Warning-level notices on RF < 7.5 (verbose only, consistent with the existing console-links guard).

## Decisions

### D1: Top-level `console`/`quiet` are excluded from the rebot profile

`BaseOptions.add_options` gets an opt-in `exclude: Container[str] = ()` parameter; `rebot.py` calls `rebot_options.add_options(profile, exclude=("console", "quiet"))` with a comment pointing at RF's `get_rebot_settings`. Alternatives: let them flow like `libdoc`'s `quiet` (breaks the `support-rf75` guarantee, forwards robot-only `dotted` or custom robot consoles to rebot, and would print the drop note for every RF < 7.5 user with a top-level console), or a local save/restore in `rebot.py` (works, but the generic parameter is three lines and testable in isolation). The default `()` keeps `libdoc`, `testdoc` and profile merging unchanged.

### D2: Tool-aware generator overrides

`type_templates` and `TOML_EXAMPLES` accept tool-prefixed keys (`"rebot:console"`, `"rebot:--console"`) looked up before the plain key; `get_type` and `apply_toml_examples` receive the `tool` that `generate()` already knows. `RebotOptions` is built from `RebotSettings._extra_cli_opts` plus `ConsoleType`/`ConsoleTypeQuiet` taken from `RebotSettings._cli_opts` when present (so the generator still runs under RF 7.4 for `support-rf75`'s diff check). The rebot `console` type becomes `Union[str, Literal["verbose", "quiet", "none"]]`; `quiet` is a flag like robot's. Nested per-tool dicts were considered and rejected as more code for the same effect.

### D3: RF < 7.5 guard clears the fields

Before `build_command_line`, on `RF_VERSION < (7, 5)` and any of the two fields set, `rebot.py` reports them via `app.verbose` and sets both to `None`. Clearing fields (rather than filtering the built argument list) also covers `quiet = false` (`--noquiet`, equally rejected by RF < 7.5) and keeps the verbose "Executing rebot with the following options" line accurate.

### D4: Regeneration and dry-run message

Model, schema and `config.md` are regenerated with the sequence `support-rf75` documents (generator under an RF 7.5 interpreter → `lint:fix` → `create-json-schema` → `robotcode config info desc`); expected structural diff: two new `RebotOptions` fields (`console` first, `quiet` after `process_empty_suite`), nothing else. The `--dry` message typo is fixed in the same change because the new tests assert on that output.

## Risks / Trade-offs

- [Runs the generator; `support-rf75` must be applied first] → stated dependency; the generator refuses nothing by itself, so the task list starts with a check that `support-rf75` tasks 3.1–3.2 are done.
- [`[rebot] console` on RF < 7.5 is only reported in verbose output] → consistent with the existing guard; the schema documents the RF version.
- [Schema advertises the options on every RF version] → same as all version-specific options.
- [`exclude` is a new keyword on a widely used method] → default keeps behaviour; a unit test asserts exclusion is opt-in.
- [Field order in `RebotOptions` changes (`console` first)] → affects `as_dict()`/`save()` key order only.

## Migration Plan

Additive; no migration. Users who passed `--console quiet` on the `robotcode rebot` command line can move it to `[rebot]`.
