# Proposal: wrapper-detection-in-command

## Why

A command that runs Robot Framework can run under the `wrapper` of the selected profile, but robotcode looks for that `wrapper` in another configuration than the one the command uses (K9 of the PyCharm findings). Checked on 2026-10-25 with `--dry`:
- From the root of a monorepo, with a `.git` folder and no `robot.toml`, `robotcode run projects/shop/tests` uses `projects/shop/robot.toml` with its default profile `gui`, but names no `wrapper`, although `gui` sets `wrapper = ["xvfb-run", "-a"]`. Started in `projects/shop`, it names it.
- From project A, whose default profile has a `wrapper`, `robotcode run ../projB/tests` uses the configuration of project B, which has none, but names A's `wrapper` as the one it would run under.
- With `-v`, these commands name the project root, the configuration files and every file they load twice.

Before the command runs, the root CLI loads the configuration to find the `wrapper`. It does not know the paths that the command gets, so it looks for the project root from the current folder, while the command looks for it from its paths. The command then loads the configuration a second time. A load takes about 5 ms in the demo project; the problem is the wrong configuration and the repeated output.

## What Changes

- The `wrapper` comes from the configuration that the command uses, found from the command's paths like every other setting. The root CLI no longer loads the configuration.
- `robot`, `debug`, `repl`, `robot-debug` and `repl-server` load the configuration once, as their first step, before they start a server, an interpreter or a debugger, and start again under the `wrapper` right after that. As before:
  - the profile's `env` applies before the `wrapper` runs;
  - `--dry` names the `wrapper` instead of running it;
  - `--wrapper` takes precedence over the profile;
  - `--no-wrapper` turns it off;
  - robotcode under the `wrapper` does not start it again.
- With `-v`, the loading appears once, also with a `wrapper`: then robotcode under the `wrapper` prints it.
- `debug` and `repl-server` report an error of the configuration where they report it today: in the debug session and after their server has started. VS Code's Debug Console thus keeps showing an error before the run.
- A configuration that cannot be loaded starts no `wrapper`, also not one given with `--wrapper`, and the command stops with the error, as before. Today robotcode starts a `wrapper` given with `--wrapper`, and robotcode under it stops with the error.
- The `-v` message "Skipping profile wrapper detection: …" goes away.

## Capabilities

### New Capabilities

- `cli-wrapper`: Which `wrapper` a robotcode command that runs Robot Framework runs under, and when the command starts under it.

### Modified Capabilities

(none)

## Impact

- `src/robotcode/cli/__init__.py`: the root CLI keeps `--wrapper` and `--no-wrapper` and their warnings for commands that do not run Robot Framework, passes the options on to the command and no longer loads the configuration. The code that starts robotcode under the `wrapper` moves to `packages/plugin/src/robotcode/plugin/click_helper/wrappable.py`.
- `packages/plugin/src/robotcode/plugin/__init__.py`: `CommonConfig` holds the `wrapper` options.
- `packages/runner/src/robotcode/runner/cli/robot.py`: `handle_robot_options` loads the configuration once per command, starts robotcode under the `wrapper`, and uses a configuration that the command loaded before.
- `packages/debugger/src/robotcode/debugger/cli.py`, `packages/repl/src/robotcode/repl/cli.py` (`repl`, `robot-debug`) and `packages/repl_server/src/robotcode/repl_server/cli.py`: load the configuration first.
- Tests: `tests/robotcode/cli/test_wrapper.py` and new tests for paths in another project, for the single load and for the order of loading, `wrapper` and server.
- Docs: none. `guides/wrapper.md` stays correct: the `env` before the `wrapper`, `--dry`, and a relative `wrapper` path that counts from the folder robotcode is started in.
- Users: the `wrapper` of the project that a run uses applies, also when its paths lie below the current folder or in another project; `-v` shows the loading once; a configuration that cannot be loaded starts no `wrapper`.
