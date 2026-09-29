# Proposal: test-metadata-selection

## Why

Since Robot Framework 7.5 tests and tasks carry `[Metadata]` (#4409), and RobotCode shows it (`rf75-test-metadata`), but nothing can select by it: Robot's `--include`/`--exclude` take only tags, RF 7.5 adds no metadata filter (PR #5685 says so explicitly) and none is planned, and RobotCode's `--search` matches the text anywhere in a test. Metadata is where projects keep the data about a test — the issue it verifies, who wrote or reviewed it — so the questions "all tests for issue 4409", "everything Hans Müller wrote or reviewed" and "tests without an owner" can today only be answered by duplicating that data into tags (`issue:4409`), where it is normalised and fills the tag statistics.

## What Changes

- **Metadata patterns.** A test's metadata becomes a list of entries `Name:Value`, one per line of each value. A pattern is written like a tag pattern: `*`, `?` and `[…]` wildcards, combined with `AND`, `OR` and `NOT`. Names compare as Robot Framework compares metadata names and values like tags (case, spaces and underscores ignored). Unlike tag patterns in RF 7.5, an operator only counts as a word of its own, with whitespace on both sides — the rule RF 8.0 introduces for tags (RF #5656) — so `Issue:CORE-123` or `Author:NORBERT` stay literal. Examples: `Issue:4409 AND Author:Hans*`, `Author:Hans* NOT Reviewer:*`, `*:4409`.
- **Selection options.** `-btm/--by-test-metadata PATTERN` and `-ebtm/--exclude-by-test-metadata PATTERN`, both repeatable, on `robot`, `robot-debug` and every `discover` command, and on `results summary`, `show`, `log`, `stats` and `diff`, next to `-bl/--by-longname`. Several `--by-test-metadata` patterns select tests matching any of them; `--exclude-by-test-metadata` removes every test matching one; both narrow every other selection.
- **Pre-run modifiers.** `robotcode.modifiers.ByTestMetadata` and `ExcludedByTestMetadata` implement the selection and work on their own: `robot --prerunmodifier "robotcode.modifiers.ByTestMetadata;Issue:4409"` or `pre-run-modifiers` in `robot.toml`.
- **`robotcode discover metadata`.** An index of the metadata in use, like `discover tags`, in two sections: the test and task metadata, and the suite metadata (including `--metadata` given to Robot). The names by default, `--values` adds the values, `--tests`/`--tasks`/`--suites` the items; JSON maps name → value → items under `metadata` and `suiteMetadata`. The test section lists exactly the entries the patterns match, so every value it shows can be selected with `--by-test-metadata Name:Value`; suite metadata is shown, not selectable.
- **Older Robot Framework.** With RF < 7.5 installed the new options and `discover metadata` are not listed in `--help`, as `--show-metadata` is not; they are still accepted, no test has metadata there, and `discover metadata` shows only the suite metadata.
- **Option order.** The options shared by `robot`, `robot-debug` and the `discover` commands appear as `--by-longname`, `--exclude-by-longname`, `--by-test-metadata`, `--exclude-by-test-metadata`, `--version`.
- **Robot Framework 7.5 note.** The version an option or command needs is declared once; from it follows that `--help` hides it on older versions and that the generated CLI reference marks it "(Robot Framework 7.5+)". `--help` itself carries no note. `--show-metadata` uses the same declaration, so all test-metadata flags are marked alike.
- Documentation (`discovering-tests.md`, `analyzing-results.md`, regenerated `cli.md`), every place marked "(Robot Framework 7.5+)", and the robotcode skill.

Left out: selecting by suite metadata (Robot Framework keeps a suite's own `Metadata` apart from test metadata, and RF #5769 plans `Test Metadata` for metadata shared by the tests of a suite; the option names say `test` so that a later `--by-suite-metadata` stays possible), statistics by metadata, a display in the editor clients, a dedicated `robot.toml` key. If Robot Framework adds its own metadata selection later, these options are removed again (maintainer decision); the maintainer proposes the feature to Robot Framework separately, with the same pattern rules.

## Capabilities

### New Capabilities

- `test-metadata-selection`: How tests and tasks are selected by their metadata in RobotCode — the entries and the pattern syntax, the selection options of `robot`, `robot-debug`, `discover` and `results`, the stand-alone pre-run modifiers, the `discover metadata` index of test and suite metadata, and the behaviour with Robot Framework older than 7.5.

### Modified Capabilities

- `cli-reference-generation`: the fixed order of the options shared by `robot`, `robot-debug` and the `discover` commands includes `--by-test-metadata` and `--exclude-by-test-metadata`; commands and options that need a newer Robot Framework version are marked with it in the generated reference.

## Impact

- `packages/modifiers/src/robotcode/modifiers/`: new module with the entries, the pattern parser and `ByTestMetadata`/`ExcludedByTestMetadata`; exported from the package.
- `packages/runner/src/robotcode/runner/cli/robot.py`: the options in `ROBOT_OPTIONS`, `RobotFrameworkEx` and the `robot` command.
- `packages/runner/src/robotcode/runner/cli/discover/`: every command and `handle_options` take the options; new `metadata` command with collector index, model and renderer.
- `packages/runner/src/robotcode/runner/cli/results/results.py`: `RESULT_FILTER_OPTIONS`, `_apply_tree_filters`, `_filters_dict` and the five commands.
- `packages/runner/src/robotcode/runner/cli/`: click classes for options and commands that need a Robot Framework version, also used by `--show-metadata`; `scripts/create_cmdline_doc.py` marks them.
- `packages/repl/src/robotcode/repl/cli.py`: `robot-debug` accepts and forwards the options.
- Tests: pattern and entry unit tests (new `tests/robotcode/modifiers/`), discover, results, REPL forwarding and option-order tests.
- Docs: `docs/03_reference/discovering-tests.md`, `docs/03_reference/analyzing-results.md`, `docs/03_reference/cli.md`.
- Skill: `robotframework-agent-plugins` (`SKILL.md`, references), then `scripts/sync_chat_plugin.py` for the vendored copy.
- No change to the language server, the editor clients or the `robot.toml` schema.
