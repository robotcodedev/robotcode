# Proposal

## Why

The tables `[rebot]`, `[libdoc]` and `[testdoc]` of `robot.toml` hold the options of `robotcode rebot`, `robotcode libdoc` and `robotcode testdoc`, but today the settings outside of them win: `[rebot] output-dir = "merged"` has no effect when the top level sets `output-dir`, which the automatically created user configuration always does. Their `extend-` settings have no effect at all. Which top-level settings reach the tools also does not fit: `robotcode libdoc` names every library after the suite `name` meant for `robot`, and `robotcode rebot` applies filters, `name` or `output` that Robot Framework itself does not pass from `robot` to `rebot`. Finally, a `[rebot]` in `.robot.toml` or in a profile replaces the whole `[rebot]` of `robot.toml`, and no `extend-` form exists to add to it. The new robot.toml guide documents how settings combine; these tables are the part that does not follow the rules (finding K2).

## What Changes

- The table of a command wins over the settings outside of it, and the `extend-` settings in the table add to them.
- Of the settings outside of the tables:
  - `robotcode rebot` takes those that Robot Framework passes from `robot` to `rebot` after a run, so no longer `includes`, `excludes`, `tests`, `suites`, `parse-include`, `name`, `doc`, `metadata`, `set-tag`, `output`, `log-level` and `timestamp-outputs` (`console` and `quiet` were already left out), and, as Robot Framework does, `run-empty-suite` reaches it as `process-empty-suite`;
  - `robotcode libdoc` takes only `python-path`, no longer `name` and `quiet`;
  - `robotcode testdoc` keeps taking the settings it shares with `robot`.
- New settings `[extend-rebot]`, `[extend-libdoc]` and `[extend-testdoc]`: in a later configuration file, in a profile and in `[extend-profiles.<name>]`, they change the table that comes before them; a setting in them replaces the one of the table, and an `extend-` setting adds to it. `[rebot]` itself keeps replacing the whole table.
- Whether the changed set of settings that reach `rebot` and `libdoc` is a breaking change is left to the maintainer (design, Open Questions).

## Capabilities

### New Capabilities

- `robot-toml-tool-options`: how the options of `robotcode rebot`, `robotcode libdoc` and `robotcode testdoc` come together from their tables in `robot.toml`, the settings outside of them, profiles and later configuration files.

### Modified Capabilities

None. The requirements of `robot-toml-option-coverage` on `console` and `quiet` stay true; `robot-toml-tool-options` covers them as part of the settings that do not reach `rebot`.

## Impact

- `packages/robot/src/robotcode/robot/config/model.py`: the fields `extend_rebot`, `extend_libdoc` and `extend_testdoc`, combining a table and its `extend-` form in profiles, the descriptions of `rebot`, `libdoc` and `testdoc`.
- `packages/runner/src/robotcode/runner/cli/rebot.py`, `libdoc.py` and `testdoc.py`: building the options.
- Tests in `tests/robotcode/runner/cli/test_robot_toml_options.py` and `tests/robotcode/robot/config/test_profile.py`.
- Generated: `docs/src/content/docs/reference/config.md` and `docs/public/schemas/robot.toml.json`.
- Docs: the robot.toml guide (`docs/src/content/docs/guides/robot-toml/`, mainly `settings.md`).
