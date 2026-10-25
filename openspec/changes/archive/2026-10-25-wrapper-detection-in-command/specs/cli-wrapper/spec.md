## Purpose

Defines which `wrapper` a robotcode command that runs Robot Framework runs under, where robotcode takes it from, and when the command starts again under it.

## ADDED Requirements

### Requirement: The wrapper comes from the configuration of the command

A command that runs Robot Framework (`robot`, `debug`, `repl`, `robot-debug`, `repl-server`) SHALL take the `wrapper` from the selected profiles of its own configuration: the configuration that robotcode finds from the command's paths, or from the current folder when the command gets no paths, as for every other setting.

#### Scenario: Tests in a project below the current folder

- **WHEN** the current folder is the root of a repository with a `.git` folder and no `robot.toml`, `projects/shop/robot.toml` sets `default-profiles = ["gui"]` and the profile `gui` sets `wrapper = ["xvfb-run", "-a"]`, and `robotcode run projects/shop/tests` runs
- **THEN** the run runs under `xvfb-run -a`

#### Scenario: Tests of another project

- **WHEN** the default profile of project A sets a `wrapper`, the configuration of project B sets none, and `robotcode run ../projB/tests` runs in project A
- **THEN** the run uses the configuration of project B and runs without a `wrapper`

### Requirement: --wrapper and --no-wrapper take precedence over the profile

`--wrapper` SHALL replace the `wrapper` of the selected profiles, and `--no-wrapper` SHALL turn off every `wrapper`, also one given with `--wrapper`.

#### Scenario: Wrapper on the command line

- **WHEN** the selected profile sets a `wrapper` and `robotcode --wrapper "<script>" run` runs
- **THEN** the run runs under `<script>` and not under the profile's `wrapper`

#### Scenario: Wrapper turned off

- **WHEN** the selected profile sets a `wrapper` and `robotcode --no-wrapper run` runs
- **THEN** the run runs without a `wrapper`

### Requirement: The configuration is loaded once

A command that runs Robot Framework SHALL load its configuration once in each process. With `-v`, its output SHALL name the project root, the configuration files and each file that it loads once, also when the command starts again under a `wrapper`.

#### Scenario: Run without a wrapper

- **WHEN** `robotcode -v run` runs in a project whose configuration sets no `wrapper`
- **THEN** the output names the project root once and every loaded configuration file once

#### Scenario: Run under a wrapper

- **WHEN** `robotcode -v run` runs in a project whose selected profile sets a `wrapper`
- **THEN** the output names the project root once and every loaded configuration file once, from robotcode under the `wrapper`

#### Scenario: Debug session without a wrapper

- **WHEN** `robotcode -v debug --no-wait-for-client` runs in a project whose configuration sets no `wrapper`
- **THEN** the output names every loaded configuration file once

### Requirement: The command starts under the wrapper before anything else

A command that runs Robot Framework SHALL start again under the `wrapper` after it has loaded its configuration and set the `env` of the selected profiles, and before it starts a debug server, a REPL server, an interpreter, a debugger or Robot Framework. Robotcode under the `wrapper` SHALL NOT start it again.

#### Scenario: Environment of the profile

- **WHEN** the selected profile sets a `wrapper` and `SESSION_KIND = "xephyr"` in its `env`, and `robotcode run` runs
- **THEN** the `wrapper` runs once, with `SESSION_KIND=xephyr` in its environment

#### Scenario: Debug session

- **WHEN** the selected profile sets a `wrapper` and `robotcode debug` runs
- **THEN** only robotcode under the `wrapper` starts the debug server

#### Scenario: REPL server

- **WHEN** the selected profile sets a `wrapper` and `robotcode repl-server` runs
- **THEN** only robotcode under the `wrapper` starts the REPL server

### Requirement: A configuration that cannot be loaded starts no wrapper

When the configuration of a command that runs Robot Framework cannot be loaded, the command SHALL NOT start a `wrapper`, neither the one of a profile nor one given with `--wrapper`, and SHALL report the error as it does without a `wrapper`.

#### Scenario: Invalid value and a wrapper on the command line

- **WHEN** `robot.toml` sets `output-dir = 5` and `robotcode --wrapper "<script>" run` runs
- **THEN** `<script>` does not run, robotcode reports the error about `output-dir` once and exits with 252

#### Scenario: Profile that does not exist next to one with a wrapper

- **WHEN** the profile `x11` sets a `wrapper`, the project defines no profile `typo`, and `robotcode -p x11 -p typo run` runs
- **THEN** the `wrapper` of `x11` does not run, robotcode reports "No profile matches 'typo'." and exits with 252

### Requirement: Debug and REPL servers report an error of the configuration after they start

When the configuration of `debug` or `repl-server` cannot be loaded, the command SHALL start its server as it does without the error and SHALL report the error once: `debug` in its debug session, before the session ends, and `repl-server` after its server has started.

#### Scenario: Debug session with a profile that does not exist

- **WHEN** `robotcode -p typo debug --no-wait-for-client` runs in a project that defines no profile `typo`
- **THEN** robotcode starts the debug server, shows `Error: No profile matches 'typo'.` once before the session ends, and exits with 252

#### Scenario: REPL server with a profile that does not exist

- **WHEN** `robotcode -p typo repl-server` runs in a project that defines no profile `typo`
- **THEN** robotcode starts the REPL server, shows `Error: No profile matches 'typo'.` once and exits with 252

### Requirement: A dry run names the wrapper

With `--dry`, a command that runs Robot Framework SHALL name the `wrapper` that it would run under instead of starting it, and SHALL then go on with its dry run.

#### Scenario: Dry run with the wrapper of a profile

- **WHEN** the selected profile sets a `wrapper` and `robotcode --dry run` runs
- **THEN** robotcode names the `wrapper`, does not start it, and prints the command line of the dry run
