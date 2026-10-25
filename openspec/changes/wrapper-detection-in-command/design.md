# Design: wrapper-detection-in-command

## Context

See proposal.md - Why. The current state in the code:

- **Root CLI** (`robotcode` in `src/robotcode/cli/__init__.py`): stores the global options in `app.config` and calls `_maybe_reexec_under_wrapper`. Only after that does it set up logging and start its own debugpy session (`--debugpy`, a hidden option for debugging robotcode itself).
- **`_maybe_reexec_under_wrapper`:**
  - Returns for `--no-wrapper`, when `ROBOTCODE_WRAPPER_APPLIED` is set, and for a command without the `@wrappable` marker.
  - Otherwise calls `get_config_files` without paths, so the project root is looked for from the current folder, then `load_robot_config_from_path`, `combine_profiles` and `evaluated_with_env`. It passes `app.verbose`, so `-v` prints the loading, and error callbacks that drop reported errors. On an exception it writes only "Skipping profile wrapper detection: …" to `-v`.
  - `--wrapper` takes precedence over the profile's `wrapper`, and `--dry` names the `wrapper`.
  - Otherwise it sets `ROBOTCODE_WRAPPER_APPLIED` and replaces the process with `[*wrapper, sys.executable, <launcher script or -m robotcode.cli>, *sys.argv[1:]]` (`os.execvp`). On Windows it runs that command and exits with its code.
- **`handle_robot_options`** (`packages/runner/src/robotcode/runner/cli/robot.py`): all five `@wrappable` commands load their configuration here.
  - `robot` calls it directly; `debug` through `run_debugger` → `_run_robot` → the `robot` command; `robot-debug` through `_invoke_runner` → the `robot` command; `repl` and `repl-server` through `run_repl`.
  - It parses the arguments with Robot Framework's parser and passes the positional ones to `get_config_files`, which looks for the project root from them. It then loads, combines and evaluates the configuration with `app.verbose` and `app.error`, and turns a `TypeError` or `ValueError` into a `click.ClickException`.
  - `discover` and `robotcode doc` call it too; they are not `@wrappable`.
- **What the commands start before they load:**
  - `debug` starts the debug adapter server and, with the default `--wait-for-client`, waits for a client, its `initialize` and its `configurationDone` (`packages/debugger/src/robotcode/debugger/run.py:226-273`).
  - `repl-server` starts its JSON-RPC server (`packages/repl_server/src/robotcode/repl_server/cli.py:222`).
  - `repl` and `robot-debug` create their console interpreter, and `robot-debug` attaches its debugger.
- **Where errors appear:**
  - An error of the configuration in `debug` reaches the run's output because it is raised inside the session: `run_debugger` shows it before `robotExited` and `terminated` (unknown-profile-errors, D7).
  - With `internalConsole`, the debug launcher forwards the output of the process from its start. It waits up to 10 s for the debug server, though, and fails with "Unable to connect to RobotCode debugger." if the server never comes up (`packages/debugger/src/robotcode/debugger/launcher/server.py:333-344`).
  - `repl-server` closes its server in a `finally` and lets an error of the session reach Click.
- **Other facts:**
  - There is one `Application` per invocation (`make_pass_decorator(Application, ensure=True)`), shared by nested commands such as `robot` inside `debug`.
  - Click 8.5 takes the arguments of the subcommand out of the context before it calls the callback of the root group (`Group.invoke`), so the root callback cannot see the paths that the command will get.
  - A load of the demo project's configuration takes about 5 ms.

## Goals / Non-Goals

**Goals:**

- One place per command that loads the configuration and decides about the `wrapper`, before the command starts anything.
- Errors and `-v` messages of the configuration appear once, where they appear today.

**Non-Goals:**

- Passing the loaded configuration from robotcode before the `wrapper` to robotcode under it; the second process loads it again.
- Changes to the debug launcher, the editors, `--wrapper`'s precedence or the messages of the `wrapper`.
- K5 (`detached` and `env`) and K7 (`python-path` in the language server).

## Decisions

### D1: The command loads the configuration and starts the wrapper; the root CLI only takes the options

- **Root CLI:** stores `--wrapper` and `--no-wrapper` in `app.config` (new fields of `CommonConfig`). It keeps the two warnings that need no configuration: `--wrapper` together with `--no-wrapper`, and `--wrapper` for a command that is not `@wrappable`. It loads no configuration.
- **Moved code:** the code that builds the command line and starts robotcode under the `wrapper` (launcher script, `ROBOTCODE_WRAPPER_APPLIED`, `execvp`, the Windows branch, the `--dry` message and the error when the `wrapper` cannot be started) moves unchanged to `robotcode.plugin.click_helper.wrappable`, next to the marker. The runner, the debugger and the REPL packages depend on `robotcode.plugin` but cannot import the root CLI.
- **Which `wrapper`:** none with `--no-wrapper` or when `ROBOTCODE_WRAPPER_APPLIED` is set; otherwise the split `--wrapper`, otherwise the evaluated `wrapper` of the profile.
- **Whether to wrap:** the command that the root CLI invoked (`ctx.find_root().invoked_subcommand`) must carry the `@wrappable` marker, as today. `robot` inside `debug` or `robot-debug` thus belongs to the outer command. `discover` and `robotcode doc`, which call `handle_robot_options` too, never start a `wrapper`.
- **Alternative:** the root group reads the subcommand's arguments and finds the paths itself. That needs Click's private `_protected_args` before `Group.invoke` clears it, and a mapping from each command's parameters to its paths; rejected.
- **Alternative:** the root CLI passes the configuration it loaded on to the command. That configuration is the wrong one when the paths lie elsewhere; rejected.

### D2: Load once per command and keep the outcome with its messages

- **New step:** next to `handle_robot_options`, the runner gets a step that parses the paths as `handle_robot_options` does and loads, combines and evaluates the configuration. Instead of printing what the callbacks report, it records it in order: `-v` messages and errors.
  - It keeps the outcome on the `Application`, keyed by the positional arguments made absolute: either the root folder and the profile, or the error.
  - It then decides about the `wrapper` (D1). When robotcode starts again under the `wrapper`, the recorded messages are dropped, because robotcode under the `wrapper` loads and prints them itself. When the `wrapper` cannot be started, they are printed before that error.
- **`handle_robot_options`** takes the kept outcome for the same paths, or runs the step itself. It prints the recorded messages and either raises the recorded error or goes on as today: `build_command_line`, the `-v` line with the options, `app.root_folder`.
- **Result:**
  - One load per process.
  - The messages and errors appear where `handle_robot_options` prints them today: in `debug` inside its session, in `repl-server` after its server has started (spec: "Debug and REPL servers report an error of the configuration after they start").
  - A load that fails yields no profile and so starts no `wrapper`. `--wrapper` is not started either: the command stops with the error anyway, and starting a `wrapper` for it would only set up its environment for nothing.
- **Alternative:** print the messages at once. A failing load would then end `debug` before its server starts, and the debug launcher would wait 10 s and fail with "Unable to connect to RobotCode debugger."; rejected.
- **Alternative:** a silent early load in `debug` and `repl-server`, and the real one later. Simpler, but it keeps the second load in these commands; rejected.
- **Alternative:** start `--wrapper` also when the load fails, as today; one more case for no gain, rejected.

### D3: Commands that start something load first

- **Which commands:** `debug`, `repl-server`, `repl` and `robot-debug` run the step from D2 as the first thing in their callbacks, before `debug` calls `run_debugger`, before `repl-server` starts its server, and before `repl` and `robot-debug` create their interpreter. `robot` loads first anyway. As today, the `--dry` message about the `wrapper` therefore comes before the command's own output.
- **Same paths:** the step must get the paths that `handle_robot_options` will get later, so that the kept outcome is found.
  - `debug` and `robot-debug` pass their `robot_options_and_args`. The listener options that `_run_robot` adds change no positional argument, and `_invoke_runner` passes the `--by-longname` filters as options of `robot`.
  - `repl` and `repl-server` pass their `files` made absolute, which `run_repl` adds as the positional arguments.
- **Mismatch:** should the paths still differ, `handle_robot_options` loads again; that is correct, but twice. A `-v` test per command guards against it.
- **Alternative:** a generic hook in the `@wrappable` marker. It would need to know each command's path parameters and to call into the runner, which `robotcode.plugin` cannot import; rejected.

## Risks / Trade-offs

- [The root's own debugpy session (`--debugpy`) starts before the command loads] → When the command then starts again under a `wrapper`, the session ends with the process, and robotcode under the `wrapper` starts its own. With `--debugpy-wait-for-client`, a client has to connect twice. Accepted: the option is hidden and meant for debugging robotcode, and the session under the `wrapper` is the one that runs Robot Framework.
- [The kept outcome is found by its paths] → A command that passes other paths to the step than later to `handle_robot_options` loads twice, see D3.
- [`repl` and `robot-debug` used to start again under the `wrapper` before they parsed their own options] → They still start again before they create anything; parsing options has no effects outside the process.
- [On Windows, robotcode before the `wrapper` waits for robotcode under it] → Unchanged. It now waits inside the command instead of the root callback. `sys.exit` with the code of the run passes through the root group, which converts only Click errors.
