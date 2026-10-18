# Design

## Context

- `robotcode rebot`, `libdoc` and `testdoc` (`packages/runner/src/robotcode/runner/cli/rebot.py`, `libdoc.py`, `testdoc.py`) combine the profiles, then start from the command's table (`profile.rebot` and so on) and call `add_options(profile)`. That copies every non-empty setting outside of the table that the tool also knows over the table's values. `rebot.py` saves and restores `console` and `quiet` around the call. The `extend-` settings of the table stay unresolved and never reach the command line.
- `BaseOptions.add_options` (`packages/robot/src/robotcode/robot/config/model.py`) merges configuration files and `extend-profiles` entries. Since 45eaa5be it applies a setting before its `extend-` form. Its `extend-` branch already handles a nested table: `elif isinstance(old, BaseOptions): old.add_options(new)`.
- `combine_profiles_ex` applies the selected profiles to a copy of the settings outside of profiles. Its `extend-` branch merges lists and dicts but has no branch for a nested table, and `result` initially shares its table objects with the configuration.
- The option fields from `generate_rf_options.py` live between `# start generated code` and `# end generated code`. `RobotExtendBaseProfile` and the fields `rebot`, `libdoc` and `testdoc` are hand-written below it.
- `RobotSettings.get_rebot_settings` in Robot Framework (`robot/conf/settings.py`, the same in 5.0 to 7.5) does not copy these options from `robot` to `rebot`: Include, Exclude, TestNames, SuiteNames, ParseInclude, Name, Doc, Metadata, SetTag, Output, LogLevel, TimestampOutputs, ConsoleType and ConsoleTypeQuiet. `--task` is the separate option TaskNames, which it does copy, and it sets ProcessEmptySuite from RunEmptySuite. It keeps the list in a local variable.
- `evaluated()` does not descend into nested tables. Expressions in a tool table are computed when the command line is built (`StringExpression.__str__`).
- The main spec `robot-toml-option-coverage` requires that the top-level `console` and `quiet` do not reach `rebot`.
- The behavior in the specs was checked with `robotcode --dry` against a draft of this design.

## Goals / Non-Goals

**Goals:**

- One rule for every tool table: the settings it takes from outside, then the table on top.
- `[extend-rebot]`, `[extend-libdoc]` and `[extend-testdoc]` work the same way between files, in profiles and in `extend-profiles` as other `extend-` settings do.

**Non-Goals:**

- Merging two plain `[rebot]` tables setting by setting. A plain table keeps replacing the one before it, like every other setting.
- Changes to the options of `robot` itself, to `[tool.robotcode-analyze]`, or to how expressions are evaluated.

## Decisions

### Build the options from outside in

Each command creates an empty options object of its tool, adds the allowed settings from outside the table, and then adds the table with `add_options`. The table wins because it comes last, and its `extend-` settings add to the values from outside, with the order from 45eaa5be.

The alternative was to keep starting from the table and skip the fields the table sets. It was rejected because `extend-` settings in the table would still not work.

### Which settings each tool takes from outside

- **`rebot`** takes everything it shares with `robot` except a constant tuple in `rebot.py`, written as model field names: `includes`, `excludes`, `tests`, `suites`, `parse_include`, `name`, `doc`, `metadata`, `set_tag`, `output`, `log_level`, `timestamp_outputs`, `console`, `quiet`. These are the options of Robot Framework's list; ConsoleType and ConsoleTypeQuiet are `console` and `quiet`, and `tasks` stays because Robot Framework copies TaskNames. They are cleared after the outside settings are added and before the table, and `run-empty-suite` is set as `process_empty_suite`, as Robot Framework does. The constant replaces the save-and-restore of `console` and `quiet`. Reading Robot Framework's list at runtime is not possible, because it is a local variable.
- **`libdoc`** starts from `python-path` only, because `name` and `quiet` outside of the table are `robot` options with another meaning for `libdoc`.
- **`testdoc`** takes everything it shares with `robot` (`name`, `doc`, `metadata`, `set-tag`, `tests`, `suites`, `includes`, `excludes`). There the settings mean the same: `testdoc` documents the suite as `robot` would run it.

These choices are the maintainer's decisions of 2026-10-18.

### extend- tables

- **Fields:** `extend_rebot`, `extend_libdoc` and `extend_testdoc` go into the hand-written `RobotExtendBaseProfile`, with the aliases `extend-rebot`, `extend-libdoc` and `extend-testdoc`. `generate_rf_options.py` does not touch them there, and `RobotConfig` and `RobotProfile` inherit them.
- **Between files and in `extend-profiles`:** the existing `BaseOptions` branch of `add_options` merges them; with `combine_extends`, an `extend-rebot` goes into the profile's `rebot` if the profile has one.
- **In profiles:** `combine_profiles_ex` gets a `BaseOptions` branch that merges into a copy (`dataclasses.replace`). Without the copy, applying a profile would change the configuration's own table, and `combine_profiles` runs more than once on the same configuration, for example in `profiles list` and in the language server.
- **Rejected alternative:** merging plain tables automatically. It would make `[rebot]` behave unlike every other setting, and the maintainer chose the `extend-` form.

### Spec placement

The new capability `robot-toml-tool-options` owns the rules for the tool tables. The `console`/`quiet` requirements of `robot-toml-option-coverage` remain true and are not changed.

## Risks / Trade-offs

- **[Risk]** Users who relied on top-level `includes`, `name`, `output` or `log-level` reaching `robotcode rebot`, or on the top-level `name` reaching `robotcode libdoc`, see different results. → **Mitigation:** the robot.toml guide and the field descriptions name the settings that reach each tool. The same settings in the tool's table still reach it.
- **[Risk]** A later Robot Framework version changes its list of options not copied to `rebot`. → **Mitigation:** the constant cites `RobotSettings.get_rebot_settings`. Check it when a new Robot Framework version is supported.
- **[Trade-off]** `add_options` changes nested tables in place when it merges files. That is fine, because the configuration objects are created fresh on every load. The copy is only needed in `combine_profiles_ex`.

## Migration Plan

Nothing to migrate. Whoever wants a filter, `name` or `log-level` for `rebot` puts it into `[rebot]`, and a library name for `libdoc` into `[libdoc]`.

## Open Questions

- Is the changed set of settings that reach `rebot` and `libdoc` a breaking change (commit footer, changelog)? The maintainer decides; it does not change the specs or the tasks.
