# Proposal: unknown-profile-errors

## Why

A profile name that selects no profile is reported, but the command goes on without it (K1 of the PyCharm findings). Checked on 2026-10-25 in the demo project:
- `robotcode -p missing run -i smoke` prints `[ ERROR ] Can't find any configuration profiles matching the pattern 'missing'.`, runs the tests with the configuration outside the profiles, and ends with the tests' exit code, as with `-p dev`.
- `discover`, `analyze code` and `profiles list` do the same and end with 0, and `rebot` goes on as well.
- The same happens when `default-profiles` or `inherits` names a profile that does not exist.

A mistyped profile on a CI server thus shows only in the output, and the run uses another configuration than intended. A `robot.toml` with an invalid value, in contrast, stops `run` before it starts, with exit code 252, and Robot Framework itself stops with 252 when `--include` selects no test.

The language server writes such errors, and the errors of a `robot.toml` it cannot load, only to its log. In the editors nobody sees them.

## What Changes

- A name or pattern that selects no profile, from `-p`, `ROBOTCODE_PROFILES`, `default-profiles` or `inherits`, is an error of the configuration. Commands stop with it before they run anything, as they do for a `robot.toml` with an invalid value. `run`, `rebot`, `libdoc` and `testdoc` exit with 252.
- `robotcode profiles list` reports the error and lists the profiles anyway. The editors call it with their selection to fill their profile lists, and the list is where a selection gets fixed.
- An `enabled` condition that cannot be evaluated stays a reported error, as today.
- The language server starts anyway. It shows each error of the configuration as an error message in the editor once the editor has connected, and still writes it to its log. This covers profile names that select no profile, a `robot.toml` it cannot load or that has invalid values, and conditions or option expressions that cannot be evaluated. With a name that selects no profile, it works with the configuration without that profile.
- The `robot.toml` guide says that the command stops and that the editors show the error.

## Capabilities

### New Capabilities

- `robot-toml-profile-selection`: How commands select the profiles of `robot.toml` by name or pattern, and what they do when a name selects no profile.
- `language-server-configuration`: How the language server deals with errors in the configuration it loads at its start.

### Modified Capabilities

_None._

## Impact

- `packages/robot/src/robotcode/robot/config/model.py`: profile selection raises for a name that selects no profile, unless the caller asks to skip it.
- `src/robotcode/cli/commands/profiles.py` (`profiles list` skips), `packages/analyze/src/robotcode/analyze/dump_model.py` (reports configuration errors like `analyze code`).
- `packages/language_server/src/robotcode/language_server/`: the start collects the configuration errors, and the server shows them after `initialized`.
- Tests in `tests/robotcode/robot/config/`, `tests/robotcode/runner/cli/`, `tests/robotcode/language_server/`.
- Docs: `guides/robot-toml/troubleshooting.md`, `guides/robot-toml/profiles.md`.
- Users: a mistyped or removed profile name now stops runs, discovery and analysis, in pipelines and in the editors, until the name is fixed. In the editors, the profile lists drop selected profiles that no longer exist when they open.
