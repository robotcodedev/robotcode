# Tasks

## 1. Tool tables win and each tool takes its own settings from outside

- [x] 1.1 `rebot.py`: add the constant of settings that Robot Framework does not pass to `rebot` (citing `RobotSettings.get_rebot_settings`), build the options from the outside settings minus the constant and then add `[rebot]`; drop the save-and-restore of `console`/`quiet`. In `tests/robotcode/runner/cli/test_robot_toml_options.py`, with the `dry_rebot` fixture, cover the scenarios of the requirements "A tool table wins over the settings outside of it" (rebot) and "rebot takes the settings that Robot Framework passes to rebot". Change `test_top_level_console_is_not_passed_to_rebot` to prove with `report-title` instead of `name` that the configuration arrives. Verify: `pytest tests/robotcode/runner/cli/test_robot_toml_options.py` passes, and the new tests fail on the old code.
- [x] 1.2 `libdoc.py`: start from `python-path` only and add `[libdoc]`. Add dry-run tests for `robotcode --dry libdoc`: `name` and `quiet` outside of the table do not reach `libdoc`, `python-path` does, and `[libdoc] python-path` wins. Verify: the tests pass and fail on the old code.
- [x] 1.3 `testdoc.py`: take the shared outside settings and add `[testdoc]` on top. Add dry-run tests: `[testdoc] name` wins over the top-level `name`, and the top-level `name` and `includes` reach `testdoc` without a table. Verify: the tests pass, and the first fails on the old code.
- [x] 1.4 Describe in `model.py` what each tool takes from outside its table and that the table wins (fields `rebot`, `libdoc`, `testdoc`). Regenerate with `hatch run create-config-docs` and `hatch run create-json-schema`, then rewrite "Settings of other commands" in `docs/src/content/docs/guides/robot-toml/settings.md` to match. Verify: the generated diff touches only these descriptions, and `npm run docs:build` passes.

## 2. extend- tables for rebot, libdoc and testdoc

- [x] 2.1 `model.py`:
  - add `extend_rebot`, `extend_libdoc` and `extend_testdoc` to `RobotExtendBaseProfile`, with aliases and descriptions;
  - give `combine_profiles_ex` a branch for nested tables that changes a copy;
  - in `tests/robotcode/robot/config/test_profile.py`, cover `extend-rebot` in a profile (keeps `merge`, the configuration's own table stays unchanged after combining), in a later file, and in `extend-profiles`, and that a plain `[rebot]` in a later file replaces the table.

  Verify: `pytest tests/robotcode/robot/config/` passes, and the new profile and `extend-profiles` tests fail on the old code.
- [x] 2.2 Add CLI dry-run tests for the scenarios "extend-rebot in a later file" (`.robot.toml`), "extend-rebot in a profile" (`-p ci`) and "extend-libdoc and extend-testdoc in a later file" in `test_robot_toml_options.py`. Verify: they pass.
- [x] 2.3 Regenerate the reference and the schema. Mention the `extend-` tables in the guide: the table of RobotCode's own settings in `settings.md`, "Between the files" in `combining.md`, and "Changing profiles in a later file" in `profiles.md`, each with an example. Verify: `extend-rebot`, `extend-libdoc` and `extend-testdoc` appear in `docs/src/content/docs/reference/config.md` and `docs/public/schemas/robot.toml.json`, the guide examples behave as described with `robotcode --dry`, and `npm run docs:build` passes.
- [x] 2.4 Review fix: an `extend-` setting inside `[extend-rebot]`, `[extend-libdoc]` or `[extend-testdoc]` stays an `extend-` setting when the table before it does not set the setting, between files, in profiles and in `extend-profiles` (the analysis tables keep turning it into the setting). Dry-run tests for a later file, a profile, `extend-profiles` and two `extend-` settings adding up; the isolation of `test_top_level_console_is_not_passed_to_rebot` via the `dry_rebot` fixture. Verify: the new tests fail on the code before the fix and pass after it.
- [x] 2.5 Review fix (maintainer's decision 2026-10-18): `rebot` takes `tasks` from outside, because Robot Framework copies TaskNames in every supported version, and gets `run-empty-suite` as `process-empty-suite`, as Robot Framework does; `[rebot] process-empty-suite` wins. Dry-run tests for both, and the field description, the guide, the spec, the proposal and the design updated. Verify: the tests fail before the change of `rebot.py` and pass after it.

## 3. Verification

- [x] 3.1 Run the full matrix and the lint checks. Verify: `hatch run test:test`, `ruff check`/`ruff format --check` and `hatch run lint:typing` on the changed files pass.

## Workflow follow-up

- Mark K2 as done in `playground/pycharm-befunde.md`, with the commit.
- Decide the open question on BREAKING before committing.
