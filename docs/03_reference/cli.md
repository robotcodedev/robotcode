# Command Line Interface (CLI)

The `robotcode` CLI tool enables seamless interaction with Robot Framework through the command line, offering a comprehensive set of features for project analysis, debugging, and configuration management.

The CLI tool is designed to be straightforward and user-friendly, with a broad range of commands to support various use cases, including test execution, documentation generation, and code analysis. It also supports configuration profiles, allowing users to define and quickly switch between different project setups as needed.

In most cases, not all CLI components are required within a single project. For example, in a CI (Continuous Integration) environment, only the `runner` package is typically necessary to execute tests, while the `language-server` package is generally not needed. The `analyze` package is mainly useful in a development environment to detect syntax errors and validate code, but it may be unnecessary in production or deployment environments. Similarly, the `debugger` package is essential for local development when troubleshooting test cases but isn’t usually required in production or CI pipelines.

To accommodate these varied needs, `robotcode` is organized into separate packages that each focus on specific functions. The core package, `robotcode`, provides foundational support for working with `robot.toml` configuration files and profile management. Here’s a more detailed breakdown of each package and its capabilities:

- **`robotcode` Core Package**:
  Always installed, the core package provides the top-level `robotcode` command together with the global options (config files, profiles, output format, paging, …) shared by every other command. It also includes commands to inspect the resolved configuration and the profiles defined for a project.
  - **Commands**:
    - `config`: Shows the merged `robot.toml` configuration and which files contributed to it, making it easy to understand how settings are resolved.
    - `profiles`: Lists the profiles defined for the project and shows their resulting configuration, helping verify which profile applies in a given context.

- **`runner` Package**:
  This package is essential for users who need to run and manage tests within Robot Framework projects. It includes commands for executing tests, generating documentation, and discovering test elements. This package is especially important in CI/CD pipelines, where automation of test execution is a primary focus.
  - **Commands**:
    - `robot`, `rebot`, `libdoc`, `testdoc`: Enhanced versions of the standard Robot Framework tools, with support for `robot.toml` configuration files and profiles, allowing customized setups for different environments or testing requirements.
    - `discover`: Searches the project for tests, suites, tags, tasks, and other elements, providing a quick overview of available test cases and project structure.
    - `results`: Inspects a finished run's `output.xml`/`output.json` — summaries, failures, the per-test execution log, and diffs between two runs — without re-executing the tests.

- **`analyze` Package**:
  This package provides tools for detailed inspection and validation of Robot Framework code, helping users identify errors and improve code quality. The `analyze` package is typically more useful in development environments where code quality checks and error detection are needed before moving tests to a CI or production environment.
  - **Commands**:
    - `analyze`: Analyzes Robot Framework scripts for syntax errors, undefined keywords, and other potential issues, allowing early detection of problems and ensuring adherence to best practices.

- **`debugger` Package**:
  The debugger package enables powerful debugging capabilities for Robot Framework tests by providing a Debug Adapter Protocol (DAP)-compatible debugger. This package is most beneficial in development or local testing environments where developers need to diagnose and troubleshoot test issues. A DAP client, such as Visual Studio Code, can be connected to initiate and control debug sessions, enabling features like setting breakpoints, stepping through code, and inspecting variables.
  - **Commands**:
    - `debug`: Starts a DAP-compatible debug session for Robot Framework tests. This tool requires a DAP client to connect to the debug session, such as Visual Studio Code, which can then interface with the debugger and provide interactive debugging tools to analyze code behavior and troubleshoot issues effectively.

- **`repl` Package**:
  The REPL (Read-Eval-Print Loop) package provides an interactive, real-time environment for executing Robot Framework commands. It’s ideal for experimenting with keywords, testing ideas, and performing quick debugging without needing to create full test files. It also ships a command-line debugger for Robot Framework runs. This package is mainly used in local development or testing environments where users can quickly prototype or troubleshoot commands.
  - **Commands**:
    - `repl`: Launches an interactive Robot Framework shell where users can execute commands line-by-line, ideal for quick testing and experimentation.
    - `robot-debug`: Runs a real `.robot` suite with the command-line debugger attached, pausing at breakpoints to step through execution, inspect the call stack and variables, and run keywords in the paused context.

- **`language-server` Package**:
  This package provides language server capabilities, supporting IDE integration for Robot Framework with real-time code insights. Compatible with editors that support the Language Server Protocol (LSP), such as Visual Studio Code, it enables enhanced productivity and convenience. It is most useful in local development environments where interactive IDE support aids in code writing and refactoring but is generally not needed in CI or production environments.
  - **Commands**:
    - `language-server`: Starts the RobotCode Language Server, which provides features like syntax highlighting, auto-completion, and code analysis, designed to improve the Robot Framework development experience within IDEs.

## Installation

To install the core `robotcode` CLI tool, use `pip`:

```bash
pip install robotcode
```

This command installs only the main package. For specific functionality, additional packages can be installed as needed:

```bash
pip install robotcode[runner]
pip install robotcode[analyze]
pip install robotcode[debugger]
pip install robotcode[repl]
pip install robotcode[languageserver]
```

To install all packages, including optional dependencies, use:

```bash
pip install robotcode[all]
```

This includes additional tools, such as [`robocop`](https://robocop.readthedocs.io) for linting and formatting, which further enhance the development experience with Robot Framework.


## Commands

The following sections outline all available commands, their usage, and the corresponding options.
Options with and asterisk (*) can be specified multiple times.


<!-- START -->
### robotcode

A CLI tool for Robot Framework.


**Usage:**
```text
robotcode [OPTIONS] COMMAND [ARGS]...
```


**Options:**
- `-c, --config PATH *`

   Config file to use. If not specified, the default config file is used.           [env var: ROBOTCODE_CONFIG_FILES]


- `-p, --profile TEXT *`

   The Execution Profile to use. If not specified, the default profile is used.           [env var: ROBOTCODE_PROFILES]


- `-r, --root DIRECTORY`

   Specifies the root path to be used for the project. It will be automatically detected if not provided.  [env var: ROBOTCODE_ROOT]


- `--no-vcs`

   Ignore version control system directories (e.g., .git, .hg) when detecting the project root.  [env var: ROBOTCODE_NO_VCS]


- `-f, --format [toml|json|json_indent|text]`

   Set the output format.


- `-d, --dry`

   Dry run, do not execute any commands.  [env var: ROBOTCODE_DRY]


- `--color / --no-color`

   Force or disable colored output. Default (no flag): auto-detect — colors only when stdout is a TTY, disabled if `NO_COLOR` is set, forced if `FORCE_COLOR` is set.  [env var: ROBOTCODE_COLOR]


- `--pager / --no-pager`

   Force or disable the pager. Default (no flag): auto-page when the rendered output exceeds the terminal height.  [env var: ROBOTCODE_PAGER]


- `-v, --verbose`

   Enables verbose mode.  [env var: ROBOTCODE_VERBOSE]


- `--log`

   Enables logging.  [env var: ROBOTCODE_LOG]


- `--log-level [TRACE|DEBUG|INFO|WARNING|ERROR|CRITICAL]`

   Sets the log level.  [env var: ROBOTCODE_LOG_LEVEL; default: CRITICAL]


- `--log-format TEXT`

   Sets the log format. See python logging documentation for more information.  [env var: ROBOTCODE_LOG_FORMAT; default: %(levelname)s:%(name)s:%(message)s]


- `--log-style [%|{|$]`

   Sets the log style. See python logging documentation for more information.  [env var: ROBOTCODE_LOG_STYLE; default: %]


- `--log-filename FILE`

   Write log output to a file instead to console.  [env var: ROBOTCODE_LOG_FILENAME]


- `--log-calls`

   Enables logging of method/function calls.  [env var: ROBOTCODE_LOG_CALLS]


- `--log-config FILE`

   Path to a logging configuration file. This must be a valid Python logging configuration file in JSON format. If this option is set, the other logging options are ignored.  [env var: ROBOTCODE_LOG_CONFIG]


- `--version`

   Show the version and exit.


- `--help`

   Show this message and exit.


**Commands:**

- [`analyze`](#analyze)

   The analyze command provides various subcommands for analyzing Robot Framework code.

- [`config`](#config)

   Shows information about the configuration.

- [`debug`](#debug)

   Starts a Robot Framework debug session and waits for incomming connections.

- [`debug-launch`](#debug-launch)

   Launches a robotcode debug session.

- [`discover`](#discover)

   Commands to discover informations about the current project.

- [`language-server`](#language-server)

   Run Robot Framework Language Server.

- [`libdoc`](#libdoc)

   Runs `libdoc` with the selected configuration, profiles, options and arguments.

- [`profiles`](#profiles)

   Shows information on defined profiles.

- [`rebot`](#rebot)

   Runs `rebot` with the selected configuration, profiles, options and arguments.

- [`repl`](#repl)

   Run Robot Framework interactively (alias `shell`).

- [`repl-server`](#repl-server)

   Start a REPL server, client can connect to the server and run the REPL scripts.

- [`results`](#results)

   Inspect a finished run's `output.xml` / `output.json` — counts, failures, and per-test execution tree, without re-running.

- [`robot`](#robot)

   Runs `robot` with the selected configuration, profiles, options and arguments.

- [`robot-debug`](#robot-debug)

   Run a real Robot Framework suite with the debugger attached (alias `run-debug`).

- [`testdoc`](#testdoc)

   Runs `testdoc` with the selected configuration, profiles, options and arguments.


**Aliases:**

- [`shell`](#repl)

   Run Robot Framework interactively (alias `shell`).

- [`run`](#robot)

   Runs `robot` with the selected configuration, profiles, options and arguments.

- [`run-debug`](#robot-debug)

   Run a real Robot Framework suite with the debugger attached (alias `run-debug`).


#### analyze

The analyze command provides various subcommands for analyzing Robot
Framework code. These subcommands support specialized tasks, such as code
analysis, style checking or dependency graphs.


**Usage:**
```text
robotcode analyze [OPTIONS] COMMAND [ARGS]...
```


**Options:**
- `--version`

   Show the version and exit.


- `--help`

   Show this message and exit.


**Commands:**

- [`cache`](#cache)

   Manage the RobotCode analysis cache.

- [`code`](#code)

   Performs static code analysis to identify potential issues in the specified *PATHS*.


##### cache

Manage the RobotCode analysis cache.

Provides subcommands to inspect, list, and clear cached data (library docs,
variables, resources, namespaces).


**Usage:**
```text
robotcode analyze cache [OPTIONS] COMMAND [ARGS]...
```


**Options:**
- `--help`

   Show this message and exit.


**Commands:**

- [`clear`](#clear)

   Clear the analysis cache.

- [`info`](#info)

   Show cache statistics.

- [`list`](#list)

   List cached entries.

- [`path`](#path)

   Print the cache directory path.

- [`prune`](#prune)

   Remove the entire cache directory.


###### clear

Clear the analysis cache.

Removes cached entries from the database. By default clears all sections.
Use --section to clear specific sections only.


**Usage:**
```text
robotcode analyze cache clear [OPTIONS] [PATHS]...
```


**Options:**
- `-s, --section SECTION *`

   Clear only specific sections (library, variables, resource, namespace). Can be specified multiple times.


- `--help`

   Show this message and exit.


###### info

Show cache statistics.

Displays the cache directory, database size, app version, and per-section
entry counts with timestamps.


**Usage:**
```text
robotcode analyze cache info [OPTIONS] [PATHS]...
```


**Options:**
- `--help`

   Show this message and exit.


###### list

List cached entries.

Shows all entries in the cache with their timestamps and sizes. Use
--section to filter by specific cache sections. Use --pattern to filter
entries by glob pattern.


**Usage:**
```text
robotcode analyze cache list [OPTIONS] [PATHS]...
```


**Options:**
- `-s, --section SECTION *`

   Filter by section (library, variables, resource, namespace). Can be specified multiple times.


- `-p, --pattern PATTERN *`

   Filter entries by glob pattern (e.g. 'robot.*', '*BuiltIn*'). Can be specified multiple times.


- `--help`

   Show this message and exit.


###### path

Print the cache directory path.

Outputs the resolved cache directory for the current project and
Python/Robot Framework version combination.


**Usage:**
```text
robotcode analyze cache path [OPTIONS] [PATHS]...
```


**Options:**
- `--help`

   Show this message and exit.


###### prune

Remove the entire cache directory.

Deletes the .robotcode_cache directory and all its contents, including
caches for all Python and Robot Framework versions.


**Usage:**
```text
robotcode analyze cache prune [OPTIONS] [PATHS]...
```


**Options:**
- `--force`

   Force prune even if cache is in use by another process.


- `--help`

   Show this message and exit.




##### code

Performs static code analysis to identify potential issues in the specified
*PATHS*. The analysis detects syntax errors, missing keywords or variables,
missing arguments, and other problems.

- **PATHS**: Can be individual files or directories. If no *PATHS* are
provided, the current directory is   analyzed by default.

The return code is a bitwise combination of the following values:

- `0`: **SUCCESS** - No issues detected. - `1`: **ERRORS** - Critical issues
found. - `2`: **WARNINGS** - Non-critical issues detected. - `4`:
**INFORMATIONS** - General information messages. - `8`: **HINTS** -
Suggestions or improvements.

*Examples*:
```
robotcode analyze code
robotcode analyze code --filter **/*.robot
robotcode analyze code tests/acceptance/first.robot
robotcode analyze code -mi DuplicateKeyword tests/acceptance/first.robot
robotcode --format json analyze code
```


**Usage:**
```text
robotcode analyze code [OPTIONS] [PATHS]...
```


**Options:**
- `--version`

   Show the version and exit.


- `-f, --filter PATTERN *`

   Glob pattern to filter files to analyze. Can be specified multiple times.         


- `-v, --variable name:value *`

   Set variables in the test data. see `robot --variable` option.


- `-V, --variablefile PATH *`

   Python or YAML file file to read variables from. see `robot --variablefile` option.


- `-P, --pythonpath PATH *`

   Additional locations where to search test libraries and other extensions when they are imported. see `robot --pythonpath` option.


- `-mi, --modifiers-ignore CODE *`

   Specifies the diagnostics codes to ignore.


- `-me, --modifiers-error CODE *`

   Specifies the diagnostics codes to treat as errors.


- `-mw, --modifiers-warning CODE *`

   Specifies the diagnostics codes to treat as warning.


- `-mI, --modifiers-information CODE *`

   Specifies the diagnostics codes to treat as information.


- `-mh, --modifiers-hint CODE *`

   Specifies the diagnostics codes to treat as hint.


- `-xm, --exit-code-mask [error|warn|info|hint|all] *`

   Specifies which diagnostic severities should not affect the exit code. For example, with 'warn' in the mask, warnings won't cause a non-zero exit code.


- `-xe, --extend-exit-code-mask [error|warn|info|hint|all] *`

   Extend the exit code mask with the specified values. This appends to the default mask, defined in the config file.


- `--severity [error|warn|warning|info|information|hint] *`

   Only report diagnostics of these severities. Repeatable and comma-separated. Filtered-out severities are ignored entirely — they don't appear in the output, the summary or the exit code. When omitted, all severities are reported.


- `--code CODE *`

   Only report diagnostics with these codes (e.g. `KeywordNotFound`). Repeatable and comma-separated; matching is case-insensitive. Unlike the modifiers, this filters without changing severity. Combined with --severity, both must match. When omitted, all codes are reported.


- `--load-library-timeout SECONDS`

   Timeout (in seconds) for loading libraries and variable files during analysis. Must be > 0. Overrides config file and environment variable when set.  [env var: ROBOTCODE_LOAD_LIBRARY_TIMEOUT]


- `--collect-unused / --no-collect-unused`

   Enable or disable collection of unused keyword and unused variable diagnostics. Overrides the config file setting when specified.


- `--cache-namespaces / --no-cache-namespaces`

   Enable or disable caching of fully analyzed namespace data to disk. Can speed up startup for large projects by skipping re-analysis of unchanged files.


- `--show-tracebacks / --no-show-tracebacks`

   Include the full diagnostic message in the text output, including Python tracebacks and PYTHONPATH listings that Robot Framework appends to import errors. Off by default to keep output concise. Has no effect on JSON output, which always carries the full message.


- `--full-paths / --no-full-paths`

   Show full paths instead of paths relative to the project root. Applies to both text and JSON output.  [default: no-full-paths]


- `--output-format [concise|json|json-indent|sarif|github|gitlab]`

   Output format for the analysis result. Overrides the global `--format` for this command. `concise` (default) is the human-readable text output; `sarif` emits a SARIF 2.1.0 log; `github` emits GitHub Actions workflow annotations; `gitlab` emits a GitLab Code Quality report.


- `--output-file FILE`

   Write the report to FILE instead of stdout. Useful with `--output-format sarif`/`gitlab` to produce an artifact for CI upload.


- `--help`

   Show this message and exit.




#### config

Shows information about the configuration.


**Usage:**
```text
robotcode config [OPTIONS] COMMAND [ARGS]...
```


**Options:**
- `--help`

   Show this message and exit.


**Commands:**

- [`files`](#files)

   Search for configuration files and list them.

- [`info`](#info)

   Shows informations about possible configuration settings.

- [`root`](#root)

   Searches for the root folder of the project and prints them.

- [`show`](#show)

   Shows the current configuration.


##### files

Search for configuration files and list them.

Takes a list of PATHS or if no PATHS are given, takes the current working
directory, to search for configuration files and prints them.

Examples:
```
robotcode config files
robotcode config files tests/acceptance/first.robot
```


**Usage:**
```text
robotcode config files [OPTIONS] [PATHS]... [USER]
```


**Options:**
- `--help`

   Show this message and exit.


##### info

Shows informations about possible configuration settings.


**Usage:**
```text
robotcode config info [OPTIONS] COMMAND [ARGS]...
```


**Options:**
- `--help`

   Show this message and exit.


**Commands:**

- [`desc`](#desc)

   Shows the description of the specified configuration settings.

- [`list`](#list)

   Lists all possible configuration settings.


###### desc

Shows the description of the specified configuration settings.

If no NAME is given shows the description of all possible configuration
settings. Wildcards are supported.

Examples:
```
robotcode config info desc
robotcode config info desc python-path
robotcode config info desc rebot.*
robotcode config info desc *tag*
```


**Usage:**
```text
robotcode config info desc [OPTIONS] [NAME]...
```


**Options:**
- `--help`

   Show this message and exit.


###### list

Lists all possible configuration settings.

If NAME is given searches for given name. Wildcards are supported.

Examples:
```
robotcode config info list
robotcode config info list rebot.*
robotcode config info list *tag*
```


**Usage:**
```text
robotcode config info list [OPTIONS] [NAME]...
```


**Options:**
- `--help`

   Show this message and exit.




##### root

Searches for the root folder of the project and prints them.

Takes a list of PATHS or if no PATHS are given, takes the current working
directory, to search for the root of the project and prints this.

Examples:
```
robotcode config root
robotcode config root tests/acceptance/first.robot
```


**Usage:**
```text
robotcode config root [OPTIONS] [PATHS]...
```


**Options:**
- `--help`

   Show this message and exit.


##### show

Shows the current configuration.

Takes a list of PATHS or if no PATHS are given, takes the current working
directory, to search for configuration files and prints the current
configuration.

Examples:
```
robotcode config show
robotcode config show tests/acceptance/first.robot
robotcode --format json config show
```


**Usage:**
```text
robotcode config show [OPTIONS] [PATHS]...
```


**Options:**
- `-s, --single`

   Shows single files, not the combined config.


- `--help`

   Show this message and exit.




#### debug

Starts a Robot Framework debug session and waits for incomming connections.


**Usage:**
```text
robotcode debug [OPTIONS] [ROBOT_OPTIONS_AND_ARGS]...
```


**Options:**
- `--debug / --no-debug`

   Enable/disable debug mode  [default: debug]


- `--stop-on-entry / --no-stop-on-entry`

   Breaks into debugger when a robot framework run starts.  [default: no-stop-on-entry]


- `--wait-for-client / --no-wait-for-client`

   Waits until a debug client is connected.  [env var: ROBOTCODE_WAIT_FOR_CLIENT; default: wait-for-client]


- `--wait-for-client-timeout FLOAT`

   Timeout in seconds for waiting for a connection with a debug client.  [env var: ROBOTCODE_WAIT_FOR_CLIENT_TIMEOUT; default: 15]


- `--configuration-done-timeout FLOAT`

   Timeout to wait for a configuration from client.  [env var: ROBOTCODE_CONFIGURATION_DONE_TIMEOUT; default: 15]


- `--debugpy / --no-debugpy`

   Enable/disable python debugging.  [env var: ROBOTCODE_DEBUGPY; default: no-debugpy]


- `--debugpy-wait-for-client / --no-debugpy-wait-for-client`

   Waits for a debugpy client to connect.  [env var: ROBOTCODE_DEBUGPY_WAIT_FOR_CLIENT]


- `--debugpy-port INTEGER`

   The port for the debugpy session.  [default: 5678]


- `--output-messages / --no-output-messages`

   Send output messages from robot framework to client.  [default: no-output-messages]


- `--output-log / --no-output-log`

   Send log messages from robotframework to client.  [default: output-log]


- `--output-timestamps / --no-output-timestamps`

   Include timestamps in log and output messages.  [default: no-output-timestamps]


- `--group-output / --no-group-output`

   Fold/group messages or log messages.  [default: no-group-output]


- `--tcp [<ADDRESS>:]<PORT>`

   Run in `tcp` server mode and listen at the given port. (Equivalent to `--mode tcp --port <port>`) *NOTE:* This option is mutually exclusive with options: mode, pipe-name, pipe-server, port.


- `--pipe-server NAME`

   Run in `pipe-server` mode and listen at the given pipe name. (Equivalent to `--mode pipe-server --pipe-name <name>`) *NOTE:* This option is mutually exclusive with options: bind, mode, pipe-name, port, tcp.


- `--mode [tcp|pipe_server]`

   The mode to use for the debug launch server. *NOTE:* This option is mutually exclusive with options: pipe-server, tcp.  [env var: ROBOTCODE_MODE; default: TCP]


- `--port PORT`

   The port to listen on or connect to. (Only valid for `tcp` and `socket mode`) *NOTE:* This option is mutually exclusive with options: pipe-name, pipe-server.  [env var: ROBOTCODE_PORT; default: 6612; 1<=x<=65535]


- `--bind ADDRESS *`

   Specify alternate bind address. If no address is specified `localhost` is used. (Only valid for tcp and socket mode) *NOTE:* This option is mutually exclusive with options: pipe-name, pipe-server.  [env var: ROBOTCODE_BIND; default: 127.0.0.1]


- `--pipe-name NAME`

   The pipe to listen on or connect to. (Only valid in `pipe` and `pipe-server` mode) *NOTE:* This option is mutually exclusive with options: bind, pipe-server, port, tcp.  [env var: ROBOTCODE_PIPE_NAME]


- `--version`

   Show the version and exit.


- `--help`

   Show this message and exit.


#### debug-launch

Launches a robotcode debug session.


**Usage:**
```text
robotcode debug-launch [OPTIONS]
```


**Options:**
- `--stdio`

   Run in `stdio` mode. (Equivalent to `--mode stdio`) *NOTE:* This option is mutually exclusive with options: bind, mode, pipe, pipe-name, pipe-server, port, socket, tcp.  [env var: ROBOTCODE_STDIO]


- `--tcp [<ADDRESS>:]<PORT>`

   Run in `tcp` server mode and listen at the given port. (Equivalent to `--mode tcp --port <port>`) *NOTE:* This option is mutually exclusive with options: mode, pipe, pipe-name, pipe-server, port, socket, stdio.


- `--socket [<ADDRESS>:]<PORT>`

   Run in `socket` mode and connect to the given port. (Equivalent to `--mode socket --port <port>`) *NOTE:* This option is mutually exclusive with options: mode, pipe, pipe-name, pipe-server, port, stdio, tcp.


- `--pipe NAME`

   Run in `pipe` mode and connect to the given pipe name. (Equivalent to `--mode pipe --pipe-name <name>`) *NOTE:* This option is mutually exclusive with options: bind, mode, pipe-name, pipe-server, port, socket, stdio, tcp.


- `--pipe-server NAME`

   Run in `pipe-server` mode and listen at the given pipe name. (Equivalent to `--mode pipe-server --pipe-name <name>`) *NOTE:* This option is mutually exclusive with options: bind, mode, pipe, pipe-name, port, socket, stdio, tcp.


- `--mode [stdio|tcp|socket|pipe|pipe_server]`

   The mode to use for the debug launch server. *NOTE:* This option is mutually exclusive with options: pipe, pipe-server, socket, stdio, tcp.  [env var: ROBOTCODE_MODE; default: STDIO]


- `--port PORT`

   The port to listen on or connect to. (Only valid for `tcp` and `socket mode`) *NOTE:* This option is mutually exclusive with options: pipe, pipe-name, pipe-server.  [env var: ROBOTCODE_PORT; default: 6611; 1<=x<=65535]


- `--bind ADDRESS *`

   Specify alternate bind address. If no address is specified `localhost` is used. (Only valid for tcp and socket mode) *NOTE:* This option is mutually exclusive with options: pipe, pipe-name, pipe-server.  [env var: ROBOTCODE_BIND; default: 127.0.0.1]


- `--pipe-name NAME`

   The pipe to listen on or connect to. (Only valid in `pipe` and `pipe-server` mode) *NOTE:* This option is mutually exclusive with options: bind, pipe, pipe-server, port, socket, stdio, tcp.  [env var: ROBOTCODE_PIPE_NAME]


- `--version`

   Show the version and exit.


- `--help`

   Show this message and exit.


#### discover

Commands to discover informations about the current project.

Examples:
```
robotcode discover tests
robotcode --profile regression discover tests
```


**Usage:**
```text
robotcode discover [OPTIONS] COMMAND [ARGS]...
```


**Options:**
- `--diagnostics / --no-diagnostics`

   Display `robot` parsing errors and warning that occur during discovering.  [default: diagnostics]


- `--version`

   Show the version and exit.


- `--help`

   Show this message and exit.


**Commands:**

- [`all`](#all)

   Discover suites, tests, tasks with the selected configuration, profiles, options and arguments.

- [`files`](#files)

   Shows all files that are used to discover the tests.

- [`info`](#info)

   Shows some informations about the current *robot* environment.

- [`suites`](#suites)

   Discover suites with the selected configuration, profiles, options and arguments.

- [`tags`](#tags)

   Discover tags with the selected configuration, profiles, options and arguments.

- [`tasks`](#tasks)

   Discover tasks with the selected configuration, profiles, options and arguments.

- [`tests`](#tests)

   Discover tests with the selected configuration, profiles, options and arguments.


##### all

Discover suites, tests, tasks with the selected configuration, profiles,
options and arguments.

You can use all known `robot` arguments to filter for example by tags or to
use pre-run-modifier.

Examples:
```
robotcode discover all
robotcode --profile regression discover all
robotcode --profile regression discover all --include regression --exclude wipANDnotready
```


**Usage:**
```text
robotcode discover all [OPTIONS] [ROBOT_OPTIONS_AND_ARGS]...
```


**Options:**
- `--tags / --no-tags`

   Show the tags that are present.  [default: tags]


- `-ebl, --exclude-by-longname TEXT *`

   Excludes tests/tasks or suites by longname.


- `-bl, --by-longname TEXT *`

   Select tests/tasks or suites by longname.


- `--version`

   Show the version and exit.


- `--search TEXT`

   Only include items where TEXT case-insensitively matches the name, full name, source path, documentation, template name, timeout, any tag (normalisation-aware), the parent suite's Documentation / Metadata, or anything inside the test body — keyword names, keyword arguments, assigned variables, FOR/WHILE/IF conditions, VAR/RETURN values, EXCEPT patterns, GROUP names. Mutually exclusive with `--search-regex`.


- `--search-regex PATTERN`

   Only include items where PATTERN (Python regex, case-sensitive — prefix with `(?i)` for case-insensitive) matches any of the same targets as `--search`. Mutually exclusive with `--search`.


- `--full-paths / --no-full-paths`

   Show full paths instead of relative.  [default: no-full-paths]


- `--help`

   Show this message and exit.



Use `-- --help` to see `robot` help.


##### files

Shows all files that are used to discover the tests.

Note: At the moment only `.robot` and `.resource` files are shown. 
Examples: ``` robotcode discover files . ```


**Usage:**
```text
robotcode discover files [OPTIONS] [PATHS]...
```


**Options:**
- `--full-paths / --no-full-paths`

   Show full paths instead of relative.  [default: no-full-paths]


- `--search TEXT`

   Only include items where TEXT case-insensitively matches the name, full name, source path, documentation, template name, timeout, any tag (normalisation-aware), the parent suite's Documentation / Metadata, or anything inside the test body — keyword names, keyword arguments, assigned variables, FOR/WHILE/IF conditions, VAR/RETURN values, EXCEPT patterns, GROUP names. Mutually exclusive with `--search-regex`.


- `--search-regex PATTERN`

   Only include items where PATTERN (Python regex, case-sensitive — prefix with `(?i)` for case-insensitive) matches any of the same targets as `--search`. Mutually exclusive with `--search`.


- `--help`

   Show this message and exit.


##### info

Shows some informations about the current *robot* environment.

Examples:
```
robotcode discover info
```


**Usage:**
```text
robotcode discover info [OPTIONS]
```


**Options:**
- `--help`

   Show this message and exit.


##### suites

Discover suites with the selected configuration, profiles, options and
arguments.

You can use all known `robot` arguments to filter for example by tags or to
use pre-run-modifier.

Examples:
```
robotcode discover suites
robotcode --profile regression discover suites
robotcode --profile regression discover suites --include regression --exclude wipANDnotready
```


**Usage:**
```text
robotcode discover suites [OPTIONS] [ROBOT_OPTIONS_AND_ARGS]...
```


**Options:**
- `-ebl, --exclude-by-longname TEXT *`

   Excludes tests/tasks or suites by longname.


- `-bl, --by-longname TEXT *`

   Select tests/tasks or suites by longname.


- `--version`

   Show the version and exit.


- `--search TEXT`

   Only include items where TEXT case-insensitively matches the name, full name, source path, documentation, template name, timeout, any tag (normalisation-aware), the parent suite's Documentation / Metadata, or anything inside the test body — keyword names, keyword arguments, assigned variables, FOR/WHILE/IF conditions, VAR/RETURN values, EXCEPT patterns, GROUP names. Mutually exclusive with `--search-regex`.


- `--search-regex PATTERN`

   Only include items where PATTERN (Python regex, case-sensitive — prefix with `(?i)` for case-insensitive) matches any of the same targets as `--search`. Mutually exclusive with `--search`.


- `--full-paths / --no-full-paths`

   Show full paths instead of relative.  [default: no-full-paths]


- `--help`

   Show this message and exit.



Use `-- --help` to see `robot` help.


##### tags

Discover tags with the selected configuration, profiles, options and
arguments.

You can use all known `robot` arguments to filter for example by tags or to
use pre-run-modifier.

Examples:
```
robotcode discover tags
robotcode --profile regression discover tags

robotcode --profile regression discover tags --tests -i wip ```


**Usage:**
```text
robotcode discover tags [OPTIONS] [ROBOT_OPTIONS_AND_ARGS]...
```


**Options:**
- `--normalized / --not-normalized`

   Whether or not normalized tags are shown.  [default: normalized]


- `--tests / --no-tests`

   Show tests where the tag is present.  [default: no-tests]


- `--tasks / --no-tasks`

   Show tasks where the tag is present.  [default: no-tasks]


- `--full-paths / --no-full-paths`

   Show full paths instead of relative.  [default: no-full-paths]


- `-ebl, --exclude-by-longname TEXT *`

   Excludes tests/tasks or suites by longname.


- `-bl, --by-longname TEXT *`

   Select tests/tasks or suites by longname.


- `--version`

   Show the version and exit.


- `--search TEXT`

   Only include items where TEXT case-insensitively matches the name, full name, source path, documentation, template name, timeout, any tag (normalisation-aware), the parent suite's Documentation / Metadata, or anything inside the test body — keyword names, keyword arguments, assigned variables, FOR/WHILE/IF conditions, VAR/RETURN values, EXCEPT patterns, GROUP names. Mutually exclusive with `--search-regex`.


- `--search-regex PATTERN`

   Only include items where PATTERN (Python regex, case-sensitive — prefix with `(?i)` for case-insensitive) matches any of the same targets as `--search`. Mutually exclusive with `--search`.


- `--help`

   Show this message and exit.



Use `-- --help` to see `robot` help.


##### tasks

Discover tasks with the selected configuration, profiles, options and
arguments.

You can use all known `robot` arguments to filter for example by tags or to
use pre-run-modifier.

Examples:
```
robotcode discover tasks
robotcode --profile regression discover tasks
robotcode --profile regression discover tasks --include regression --exclude wipANDnotready
```


**Usage:**
```text
robotcode discover tasks [OPTIONS] [ROBOT_OPTIONS_AND_ARGS]...
```


**Options:**
- `--tags / --no-tags`

   Show the tags that are present.  [default: no-tags]


- `--full-paths / --no-full-paths`

   Show full paths instead of relative.  [default: no-full-paths]


- `-ebl, --exclude-by-longname TEXT *`

   Excludes tests/tasks or suites by longname.


- `-bl, --by-longname TEXT *`

   Select tests/tasks or suites by longname.


- `--version`

   Show the version and exit.


- `--search TEXT`

   Only include items where TEXT case-insensitively matches the name, full name, source path, documentation, template name, timeout, any tag (normalisation-aware), the parent suite's Documentation / Metadata, or anything inside the test body — keyword names, keyword arguments, assigned variables, FOR/WHILE/IF conditions, VAR/RETURN values, EXCEPT patterns, GROUP names. Mutually exclusive with `--search-regex`.


- `--search-regex PATTERN`

   Only include items where PATTERN (Python regex, case-sensitive — prefix with `(?i)` for case-insensitive) matches any of the same targets as `--search`. Mutually exclusive with `--search`.


- `--help`

   Show this message and exit.



Use `-- --help` to see `robot` help.


##### tests

Discover tests with the selected configuration, profiles, options and
arguments.

You can use all known `robot` arguments to filter for example by tags or to
use pre-run-modifier.

Examples:
```
robotcode discover tests
robotcode --profile regression discover tests
robotcode --profile regression discover tests --include regression --exclude wipANDnotready
```


**Usage:**
```text
robotcode discover tests [OPTIONS] [ROBOT_OPTIONS_AND_ARGS]...
```


**Options:**
- `--tags / --no-tags`

   Show the tags that are present.  [default: no-tags]


- `--full-paths / --no-full-paths`

   Show full paths instead of relative.  [default: no-full-paths]


- `-ebl, --exclude-by-longname TEXT *`

   Excludes tests/tasks or suites by longname.


- `-bl, --by-longname TEXT *`

   Select tests/tasks or suites by longname.


- `--version`

   Show the version and exit.


- `--search TEXT`

   Only include items where TEXT case-insensitively matches the name, full name, source path, documentation, template name, timeout, any tag (normalisation-aware), the parent suite's Documentation / Metadata, or anything inside the test body — keyword names, keyword arguments, assigned variables, FOR/WHILE/IF conditions, VAR/RETURN values, EXCEPT patterns, GROUP names. Mutually exclusive with `--search-regex`.


- `--search-regex PATTERN`

   Only include items where PATTERN (Python regex, case-sensitive — prefix with `(?i)` for case-insensitive) matches any of the same targets as `--search`. Mutually exclusive with `--search`.


- `--help`

   Show this message and exit.



Use `-- --help` to see `robot` help.




#### language-server

Run Robot Framework Language Server.


**Usage:**
```text
robotcode language-server [OPTIONS] [PATHS]...
```


**Options:**
- `--stdio`

   Run in `stdio` mode. (Equivalent to `--mode stdio`) *NOTE:* This option is mutually exclusive with options: bind, mode, pipe, pipe-name, port, socket, tcp.  [env var: ROBOTCODE_STDIO]


- `--tcp [<ADDRESS>:]<PORT>`

   Run in `tcp` server mode and listen at the given port. (Equivalent to `--mode tcp --port <port>`) *NOTE:* This option is mutually exclusive with options: mode, pipe, pipe-name, port, socket, stdio.


- `--socket [<ADDRESS>:]<PORT>`

   Run in `socket` mode and connect to the given port. (Equivalent to `--mode socket --port <port>`) *NOTE:* This option is mutually exclusive with options: mode, pipe, pipe-name, port, stdio, tcp.


- `--pipe NAME`

   Run in `pipe` mode and connect to the given pipe name. (Equivalent to `--mode pipe --pipe-name <name>`) *NOTE:* This option is mutually exclusive with options: bind, mode, pipe-name, port, socket, stdio, tcp.


- `--mode [stdio|tcp|socket|pipe]`

   The mode to use for the debug launch server. *NOTE:* This option is mutually exclusive with options: pipe, socket, stdio, tcp.  [env var: ROBOTCODE_MODE; default: STDIO]


- `--port PORT`

   The port to listen on or connect to. (Only valid for `tcp` and `socket mode`) *NOTE:* This option is mutually exclusive with options: pipe, pipe-name.  [env var: ROBOTCODE_PORT; default: 6610; 1<=x<=65535]


- `--bind ADDRESS *`

   Specify alternate bind address. If no address is specified `localhost` is used. (Only valid for tcp and socket mode) *NOTE:* This option is mutually exclusive with options: pipe, pipe-name.  [env var: ROBOTCODE_BIND; default: 127.0.0.1]


- `--pipe-name NAME`

   The pipe to listen on or connect to. (Only valid in `pipe` and `pipe-server` mode) *NOTE:* This option is mutually exclusive with options: bind, pipe, port, socket, stdio, tcp.  [env var: ROBOTCODE_PIPE_NAME]


- `--version`

   Show the version and exit.


- `--help`

   Show this message and exit.


#### libdoc

Runs `libdoc` with the selected configuration, profiles, options and
arguments.

The options and arguments are passed to `libdoc` as is.


**Usage:**
```text
robotcode libdoc [OPTIONS] [ROBOT_OPTIONS_AND_ARGS]...
```


**Options:**
- `--version`

   Show the version and exit.


- `--help`

   Show this message and exit.



Use `-- --help` to see the `libdoc` help.


#### profiles

Shows information on defined profiles.


**Usage:**
```text
robotcode profiles [OPTIONS] COMMAND [ARGS]...
```


**Options:**
- `--help`

   Show this message and exit.


**Commands:**

- [`list`](#list)

   Lists the defined profiles in the current configuration.

- [`show`](#show)

   Shows the given profile configuration.


##### list

Lists the defined profiles in the current configuration.


**Usage:**
```text
robotcode profiles list [OPTIONS] [PATHS]...
```


**Options:**
- `-h, --show-hidden`

   Show hidden profiles.


- `-sp, --sort-by-precedence`

   Sort by precedence.


- `--help`

   Show this message and exit.


##### show

Shows the given profile configuration.


**Usage:**
```text
robotcode profiles show [OPTIONS] [PATHS]...
```


**Options:**
- `-n, --no-evaluate`

   Don't evaluate expressions in the profile.


- `--help`

   Show this message and exit.




#### rebot

Runs `rebot` with the selected configuration, profiles, options and
arguments.

The options and arguments are passed to `rebot` as is.


**Usage:**
```text
robotcode rebot [OPTIONS] [ROBOT_OPTIONS_AND_ARGS]...
```


**Options:**
- `--version`

   Show the version and exit.


- `--help`

   Show this message and exit.



Use `-- --help` to see `rebot` help.


#### repl

Run Robot Framework interactively (alias `shell`).

Starts an interactive session where you enter Robot Framework keywords and
run them immediately. Pass FILES to execute them in the session.


**Usage:**
```text
robotcode repl [OPTIONS] [FILES]...
```


**Options:**
- `--no-history`

   Don't load or save the persistent history file. In-session arrow-up recall still works, but nothing crosses session boundaries. Useful for AI-agent invocations or quick spike sessions you don't want polluting your shell's REPL history.


- `--backend [auto|prompt-toolkit|plain]`

   Force a specific input backend instead of auto-picking. `auto` and `prompt-toolkit` both pick the prompt-toolkit-driven interpreter (completion, syntax highlighting, history, doc viewer). `plain` drops to a bare `input()` prompt — useful when ANSI escapes or popups would interfere with the surrounding capture.  [default: auto]


- `--plain`

   Shorthand for `--backend=plain`. Disables all prompt enhancements — completion, syntax highlighting, candidate popup, auto-suggest, history file. The prompt becomes a bare `input()` call. Recommended for AI-agent invocations, automation pipelines, and any context where ANSI escapes or completion popups would interfere with stdin/stdout capture. Conflicts with `--backend=<other>`.


- `-v, --variable name:value *`

   Set variables in the test data. See `robot --variable` option.


- `-V, --variablefile PATH *`

   Python or YAML file to read variables from. See `robot --variablefile` option.


- `-P, --pythonpath PATH *`

   Additional locations where to search test libraries and other extensions when they are imported. See `robot --pythonpath` option.


- `-k, --show-keywords`

   Executed keywords will be shown in the output.


- `-i, --inspect`

   Activate inspection mode. This forces a prompt to appear after the REPL script is executed.


- `-d, --outputdir DIR`

   Where to create output files. See `robot --outputdir` option.


- `-o, --output FILE`

   XML output file. See `robot --output` option.


- `-r, --report FILE`

   HTML output file. See `robot --report` option.


- `-l, --log FILE`

   HTML log file. See `robot --log` option.


- `-x, --xunit FILE`

   xUnit output file. See `robot --xunit` option.


- `-s, --source FILE`

   Use the parent directory of FILE as the REPL's working directory. Relative paths inside `Import Resource`, `Import Library`, file-based variables, etc. resolve against that directory. The file itself is never read or written, so the path doesn't need to exist.


- `--debugger-attached / --no-debugger-attached`

   Whether the debugger is active. While detached nothing pauses — a failing keyword just prints its error and you stay at the prompt — but breakpoints and exception filters stay configured. Default: attached for `robot-debug`; for `repl` detached, unless a pause trigger (`--break`, a `--break-on-*` flag) is given. Toggle at runtime with `.debug on` / `.debug off`.


- `--break LOCATION *`

   Break at LOCATION — a `file:line` or a keyword name. Repeatable.


- `--break-on-exception / --no-break-on-exception`

   Break at an uncaught failing keyword (not caught by TRY/EXCEPT or `Run Keyword And …`), before the failure unwinds. Armed by default; it only pauses while the debugger is attached (see `--debugger-attached`).


- `--break-on-all-exceptions / --no-break-on-all-exceptions`

   Break at EVERY failing keyword, even ones caught by TRY/EXCEPT or `Run Keyword And …`.  [default: no-break-on-all-exceptions]


- `--break-on-failed-test / --no-break-on-failed-test`

   Break at the end of a failing test.  [default: no-break-on-failed-test]


- `--break-on-failed-suite / --no-break-on-failed-suite`

   Break at the end of a failing suite.  [default: no-break-on-failed-suite]


- `--version`

   Show the version and exit.


- `--help`

   Show this message and exit.


#### repl-server

Start a REPL server, client can connect to the server and run the REPL
scripts.


**Usage:**
```text
robotcode repl-server [OPTIONS] [FILES]...
```


**Options:**
- `--stdio`

   Run in `stdio` mode. (Equivalent to `--mode stdio`) *NOTE:* This option is mutually exclusive with options: bind, mode, pipe, pipe-name, pipe-server, port, socket, tcp.  [env var: ROBOTCODE_STDIO]


- `--tcp [<ADDRESS>:]<PORT>`

   Run in `tcp` server mode and listen at the given port. (Equivalent to `--mode tcp --port <port>`) *NOTE:* This option is mutually exclusive with options: mode, pipe, pipe-name, pipe-server, port, socket, stdio.


- `--socket [<ADDRESS>:]<PORT>`

   Run in `socket` mode and connect to the given port. (Equivalent to `--mode socket --port <port>`) *NOTE:* This option is mutually exclusive with options: mode, pipe, pipe-name, pipe-server, port, stdio, tcp.


- `--pipe NAME`

   Run in `pipe` mode and connect to the given pipe name. (Equivalent to `--mode pipe --pipe-name <name>`) *NOTE:* This option is mutually exclusive with options: bind, mode, pipe-name, pipe-server, port, socket, stdio, tcp.


- `--pipe-server NAME`

   Run in `pipe-server` mode and listen at the given pipe name. (Equivalent to `--mode pipe-server --pipe-name <name>`) *NOTE:* This option is mutually exclusive with options: bind, mode, pipe, pipe-name, port, socket, stdio, tcp.


- `--mode [stdio|tcp|socket|pipe|pipe_server]`

   The mode to use for the debug launch server. *NOTE:* This option is mutually exclusive with options: pipe, pipe-server, socket, stdio, tcp.  [env var: ROBOTCODE_MODE; default: STDIO]


- `--port PORT`

   The port to listen on or connect to. (Only valid for `tcp` and `socket mode`) *NOTE:* This option is mutually exclusive with options: pipe, pipe-name, pipe-server.  [env var: ROBOTCODE_PORT; default: 6601; 1<=x<=65535]


- `--bind ADDRESS *`

   Specify alternate bind address. If no address is specified `localhost` is used. (Only valid for tcp and socket mode) *NOTE:* This option is mutually exclusive with options: pipe, pipe-name, pipe-server.  [env var: ROBOTCODE_BIND; default: 127.0.0.1]


- `--pipe-name NAME`

   The pipe to listen on or connect to. (Only valid in `pipe` and `pipe-server` mode) *NOTE:* This option is mutually exclusive with options: bind, pipe, pipe-server, port, socket, stdio, tcp.  [env var: ROBOTCODE_PIPE_NAME]


- `-v, --variable name:value *`

   Set variables in the test data. see `robot --variable` option.


- `-V, --variablefile PATH *`

   Python or YAML file file to read variables from. see `robot --variablefile` option.


- `-P, --pythonpath PATH *`

   Additional locations where to search test libraries and other extensions when they are imported. see `robot --pythonpath` option.


- `-d, --outputdir DIR`

   Where to create output files. see `robot --outputdir` option.


- `-o, --output FILE`

   XML output file. see `robot --output` option.


- `-r, --report FILE`

   HTML output file. see `robot --report` option.


- `-l, --log FILE`

   HTML log file. see `robot --log` option.


- `-x, --xunit FILE`

   xUnit output file. see `robot --xunit` option.


- `--version`

   Show the version and exit.


- `-s, --source FILE`

   Use the parent directory of FILE as the REPL's working directory. Relative paths inside `Import Resource`, `Import Library`, file-based variables, etc. resolve against that directory. The file itself is never read or written, so the path doesn't need to exist.


- `--help`

   Show this message and exit.


#### results

Inspect a finished run's `output.xml` / `output.json` — counts, failures,
and per-test execution tree, without re-running.

The result file is auto-discovered from the active profile's `output_dir` /
`output` settings; override with `-o/--output PATH`. Use `-f json` (or
`toml`) for a structured payload.

Examples:
```
robotcode results summary
robotcode results summary --failed
robotcode results show --failed
robotcode results log "*Login*"
robotcode --format json results summary
```


**Usage:**
```text
robotcode results [OPTIONS] COMMAND [ARGS]...
```


**Options:**
- `--help`

   Show this message and exit.


**Commands:**

- [`diff`](#diff)

   Compare two output files: status changes plus added/removed tests.

- [`log`](#log)

   Show the execution log of each test: keywords, control flow and messages.

- [`show`](#show)

   List individual tests with status, source and failure message.

- [`stats`](#stats)

   Aggregate results by tag, suite, or status.

- [`summary`](#summary)

   Print headline counts and overall status for a finished run.


##### diff

Compare two output files: status changes plus added/removed tests.

If `CURRENT` is omitted, it is auto-discovered from the active profile so
you can diff a saved baseline against the latest run.

Examples:
```
robotcode results diff baseline.xml
robotcode results diff prev/output.xml curr/output.xml
robotcode results diff baseline.xml --only new-failures
robotcode results diff baseline.xml -i smoke
robotcode results diff baseline.xml --search TimeoutError
robotcode --format json results diff baseline.xml
```


**Usage:**
```text
robotcode results diff [OPTIONS] BASELINE [CURRENT]
```


**Options:**
- `--status [pass|fail|skip|not-run] *`

   Only include tests with one of these statuses.


- `-i, --include TAG_PATTERN *`

   Include tests matching the tag pattern. Supports Robot's tag pattern syntax (AND, OR, NOT, *, ?).


- `-e, --exclude TAG_PATTERN *`

   Exclude tests matching the tag pattern. Same syntax as --include.


- `-s, --suite NAME *`

   Only include tests inside the named suite (glob against full suite name).


- `-t, --test, --task NAME *`

   Only include tests whose name matches (glob against full test name). `--task` is an alias for `--test` (Robot's RPA terminology).


- `-bl, --by-longname NAME *`

   Select tests/tasks or suites by long name (exact match).


- `-ebl, --exclude-by-longname NAME *`

   Exclude tests/tasks or suites by long name (exact match).


- `--search TEXT`

   Only include tests with at least one case-insensitive substring match against TEXT. Searches test name, full name, failure message, documentation, template name, timeout, tags, the parent suite's Documentation / Metadata, every executed keyword's name / arguments / [Documentation] / [Tags] / [Timeout] / failure message, and log messages. Mutually exclusive with `--search-regex`.


- `--search-regex PATTERN`

   Only include tests with at least one match against PATTERN (Python regular expression, case-sensitive — prefix with `(?i)` for case-insensitive). Same target fields as `--search`. Mutually exclusive with `--search`.


- `--full-paths / --no-full-paths`

   Show absolute source paths instead of paths relative to cwd.  [default: no-full-paths]


- `--message-chars INTEGER RANGE`

   Truncate failure messages to N characters (0 = no truncation).  [default: 120; x>=0]


- `--only [new-failures|new-passes|status-changes|added|removed] *`

   Restrict output to these categories. Default: all.


- `--help`

   Show this message and exit.


##### log

Show the execution log of each test: keywords, control flow and messages.

Filter the same way as `show` — by status, tag, suite, or test name. Without
filters, all tests are included. Use `--max-depth` to collapse deeply nested
keyword calls.

Examples:
```
robotcode results log
robotcode results log --failed
robotcode results log -t "*Login*"
robotcode results log --level WARN
robotcode results log --max-depth 2
robotcode results log -i smoke --extract /tmp/artefacts
robotcode results log --search "TimeoutError"
robotcode results log --execution-messages
```


**Usage:**
```text
robotcode results log [OPTIONS]
```


**Options:**
- `--status [pass|fail|skip|not-run] *`

   Only include tests with one of these statuses.


- `-i, --include TAG_PATTERN *`

   Include tests matching the tag pattern. Supports Robot's tag pattern syntax (AND, OR, NOT, *, ?).


- `-e, --exclude TAG_PATTERN *`

   Exclude tests matching the tag pattern. Same syntax as --include.


- `-s, --suite NAME *`

   Only include tests inside the named suite (glob against full suite name).


- `-t, --test, --task NAME *`

   Only include tests whose name matches (glob against full test name). `--task` is an alias for `--test` (Robot's RPA terminology).


- `-bl, --by-longname NAME *`

   Select tests/tasks or suites by long name (exact match).


- `-ebl, --exclude-by-longname NAME *`

   Exclude tests/tasks or suites by long name (exact match).


- `--failed`

   Shortcut for `--status fail`. Additive with `--status` / `--passed` / `--skipped`.


- `--passed`

   Shortcut for `--status pass`. Additive with `--status` / `--failed` / `--skipped`.


- `--skipped`

   Shortcut for `--status skip`. Additive with `--status` / `--failed` / `--passed`.


- `--search TEXT`

   Only include tests with at least one case-insensitive substring match against TEXT. Searches test name, full name, failure message, documentation, template name, timeout, tags, the parent suite's Documentation / Metadata, every executed keyword's name / arguments / [Documentation] / [Tags] / [Timeout] / failure message, and log messages. Mutually exclusive with `--search-regex`.


- `--search-regex PATTERN`

   Only include tests with at least one match against PATTERN (Python regular expression, case-sensitive — prefix with `(?i)` for case-insensitive). Same target fields as `--search`. Mutually exclusive with `--search`.


- `-o, --output PATH`

   Path to output.xml/output.json (Robot's `--output`). If omitted, auto-discovered from the active profile's `output_dir` + `output` settings (with timestamp glob fallback and ./output.xml as last resort). A directory may also be passed — then auto-discovery happens inside it.


- `--level [trace|debug|info|warn|error|fail]`

   Minimum message level to include.  [default: INFO]


- `--max-depth N`

   Limit nested keyword calls to N levels (0 = unlimited). When a keyword sits below the limit, its body is collapsed and the hidden child count is shown instead.  [default: 0; x>=0]


- `--extract DIRECTORY`

   Copy/decode referenced artefacts into this directory. Each test's artefacts go into a per-test subdirectory.


- `--full-paths / --no-full-paths`

   [default: no-full-paths]


- `--timestamps / --no-timestamps`

   Show timestamps next to log messages.  [default: no-timestamps]


- `--timing / --no-timing`

   Show start time per test/keyword and append start / end / elapsed of the run as a footer. Use `--no-timing` to suppress.  [default: timing]


- `--raw-html / --no-raw-html`

   Emit HTML messages as raw markup instead of converting them to plain text. Useful when the HTML is the payload of interest. Embedded base64 images and external file refs are NOT extracted in raw mode.  [default: no-raw-html]


- `--execution-messages / --no-execution-messages`

   Also show parser/discovery messages from output.xml's `<errors>` section (deduplicated).  [default: no-execution-messages]


- `--keyword-info / --no-keyword-info`

   Include each executed keyword's [Documentation], [Tags] and [Timeout] from the keyword definition. Off by default to keep the log compact.  [default: no-keyword-info]


- `--suite-info / --no-suite-info`

   Group tests under suite headers (name, source, Documentation, Metadata, status). In JSON, populates `suites` and a per-test `suite` reference. Off by default to keep the log compact.  [default: no-suite-info]


- `--help`

   Show this message and exit.


##### show

List individual tests with status, source and failure message.

One line per test: status badge, full name, `(path:line)` link, and the
first line of any failure/skip message.

Examples:
```
robotcode results show
robotcode results show --failed
robotcode results show --failed --skipped --tags
robotcode results show -i smoke -e wipANDnotready
robotcode results show -s "MyProject.Login.*"
robotcode results show --top 20
robotcode results show --search "AssertionError"
```


**Usage:**
```text
robotcode results show [OPTIONS]
```


**Options:**
- `--status [pass|fail|skip|not-run] *`

   Only include tests with one of these statuses.


- `-i, --include TAG_PATTERN *`

   Include tests matching the tag pattern. Supports Robot's tag pattern syntax (AND, OR, NOT, *, ?).


- `-e, --exclude TAG_PATTERN *`

   Exclude tests matching the tag pattern. Same syntax as --include.


- `-s, --suite NAME *`

   Only include tests inside the named suite (glob against full suite name).


- `-t, --test, --task NAME *`

   Only include tests whose name matches (glob against full test name). `--task` is an alias for `--test` (Robot's RPA terminology).


- `-bl, --by-longname NAME *`

   Select tests/tasks or suites by long name (exact match).


- `-ebl, --exclude-by-longname NAME *`

   Exclude tests/tasks or suites by long name (exact match).


- `--failed`

   Shortcut for `--status fail`. Additive with `--status` / `--passed` / `--skipped`.


- `--passed`

   Shortcut for `--status pass`. Additive with `--status` / `--failed` / `--skipped`.


- `--skipped`

   Shortcut for `--status skip`. Additive with `--status` / `--failed` / `--passed`.


- `--search TEXT`

   Only include tests with at least one case-insensitive substring match against TEXT. Searches test name, full name, failure message, documentation, template name, timeout, tags, the parent suite's Documentation / Metadata, every executed keyword's name / arguments / [Documentation] / [Tags] / [Timeout] / failure message, and log messages. Mutually exclusive with `--search-regex`.


- `--search-regex PATTERN`

   Only include tests with at least one match against PATTERN (Python regular expression, case-sensitive — prefix with `(?i)` for case-insensitive). Same target fields as `--search`. Mutually exclusive with `--search`.


- `-o, --output PATH`

   Path to output.xml/output.json (Robot's `--output`). If omitted, auto-discovered from the active profile's `output_dir` + `output` settings (with timestamp glob fallback and ./output.xml as last resort). A directory may also be passed — then auto-discovery happens inside it.


- `--top INTEGER RANGE`

   Show at most N tests (0 = no limit, default).  [default: 0; x>=0]


- `--message-chars INTEGER RANGE`

   Truncate each message to N characters (0 = no truncation).  [default: 120; x>=0]


- `--full-paths / --no-full-paths`

   Show absolute source paths instead of paths relative to cwd.  [default: no-full-paths]


- `--tags / --no-tags`

   Append the tag list after each test.  [default: no-tags]


- `--timing / --no-timing`

   Show start time per test and append start / end / elapsed of the run to the statistics block. Use `--no-timing` to suppress.  [default: timing]


- `--sort FIELD`

   Sort tests before display. `name`/`suite` = lexicographic full-name/suite. `status` = FAIL → SKIP → PASS → NOT RUN. `elapsed` = duration (longest first). `start` = start time. Default: execution order from the output file.


- `--reverse / --no-reverse`

   Reverse the sort order (only applies with `--sort`).  [default: no-reverse]


- `--help`

   Show this message and exit.


##### stats

Aggregate results by tag, suite, or status.

Each section is a table with pass/fail/skip counts and total elapsed per
group. Repeat `--by` to render multiple sections in one go.

Examples:
```
robotcode results stats
robotcode results stats --by tag
robotcode results stats --by tag --by suite
robotcode results stats --by tag --sort elapsed --top 20
robotcode results stats --by tag --search Browser
robotcode --format json results stats --by tag
```


**Usage:**
```text
robotcode results stats [OPTIONS]
```


**Options:**
- `--status [pass|fail|skip|not-run] *`

   Only include tests with one of these statuses.


- `-i, --include TAG_PATTERN *`

   Include tests matching the tag pattern. Supports Robot's tag pattern syntax (AND, OR, NOT, *, ?).


- `-e, --exclude TAG_PATTERN *`

   Exclude tests matching the tag pattern. Same syntax as --include.


- `-s, --suite NAME *`

   Only include tests inside the named suite (glob against full suite name).


- `-t, --test, --task NAME *`

   Only include tests whose name matches (glob against full test name). `--task` is an alias for `--test` (Robot's RPA terminology).


- `-bl, --by-longname NAME *`

   Select tests/tasks or suites by long name (exact match).


- `-ebl, --exclude-by-longname NAME *`

   Exclude tests/tasks or suites by long name (exact match).


- `--failed`

   Shortcut for `--status fail`. Additive with `--status` / `--passed` / `--skipped`.


- `--passed`

   Shortcut for `--status pass`. Additive with `--status` / `--failed` / `--skipped`.


- `--skipped`

   Shortcut for `--status skip`. Additive with `--status` / `--failed` / `--passed`.


- `--search TEXT`

   Only include tests with at least one case-insensitive substring match against TEXT. Searches test name, full name, failure message, documentation, template name, timeout, tags, the parent suite's Documentation / Metadata, every executed keyword's name / arguments / [Documentation] / [Tags] / [Timeout] / failure message, and log messages. Mutually exclusive with `--search-regex`.


- `--search-regex PATTERN`

   Only include tests with at least one match against PATTERN (Python regular expression, case-sensitive — prefix with `(?i)` for case-insensitive). Same target fields as `--search`. Mutually exclusive with `--search`.


- `-o, --output PATH`

   Path to output.xml/output.json (Robot's `--output`). If omitted, auto-discovered from the active profile's `output_dir` + `output` settings (with timestamp glob fallback and ./output.xml as last resort). A directory may also be passed — then auto-discovery happens inside it.


- `--by [tag|suite|status] *`

   Group tests by this attribute (one section per value).  [default: status]


- `--sort [name|total|failed|elapsed]`

   Within each section: sort groups by this metric (descending).  [default: failed]


- `--top INTEGER RANGE`

   Show at most N groups per section (0 = all).  [default: 0; x>=0]


- `--help`

   Show this message and exit.


##### summary

Print headline counts and overall status for a finished run.

Pass `--failed` to also list failed tests above the counts. Filter options
narrow what is counted.

Examples:
```
robotcode results summary
robotcode results summary --failed
robotcode results summary -i smoke --status fail
robotcode results summary --search TimeoutError
robotcode --format json results summary
```


**Usage:**
```text
robotcode results summary [OPTIONS]
```


**Options:**
- `--status [pass|fail|skip|not-run] *`

   Only include tests with one of these statuses.


- `-i, --include TAG_PATTERN *`

   Include tests matching the tag pattern. Supports Robot's tag pattern syntax (AND, OR, NOT, *, ?).


- `-e, --exclude TAG_PATTERN *`

   Exclude tests matching the tag pattern. Same syntax as --include.


- `-s, --suite NAME *`

   Only include tests inside the named suite (glob against full suite name).


- `-t, --test, --task NAME *`

   Only include tests whose name matches (glob against full test name). `--task` is an alias for `--test` (Robot's RPA terminology).


- `-bl, --by-longname NAME *`

   Select tests/tasks or suites by long name (exact match).


- `-ebl, --exclude-by-longname NAME *`

   Exclude tests/tasks or suites by long name (exact match).


- `--search TEXT`

   Only include tests with at least one case-insensitive substring match against TEXT. Searches test name, full name, failure message, documentation, template name, timeout, tags, the parent suite's Documentation / Metadata, every executed keyword's name / arguments / [Documentation] / [Tags] / [Timeout] / failure message, and log messages. Mutually exclusive with `--search-regex`.


- `--search-regex PATTERN`

   Only include tests with at least one match against PATTERN (Python regular expression, case-sensitive — prefix with `(?i)` for case-insensitive). Same target fields as `--search`. Mutually exclusive with `--search`.


- `-o, --output PATH`

   Path to output.xml/output.json (Robot's `--output`). If omitted, auto-discovered from the active profile's `output_dir` + `output` settings (with timestamp glob fallback and ./output.xml as last resort). A directory may also be passed — then auto-discovery happens inside it.


- `--failed / --no-failed`

   Include the list of failed tests (with messages) above the counts table.  [default: no-failed]


- `--full-paths / --no-full-paths`

   Show absolute source paths instead of paths relative to cwd.  [default: no-full-paths]


- `--help`

   Show this message and exit.




#### robot

Runs `robot` with the selected configuration, profiles, options and
arguments.

The options and arguments are passed to `robot` as is.

Examples:

```
robotcode robot
robotcode robot tests
robotcode robot -i regression -e wip tests
robotcode --profile ci robot -i regression -e wip tests
```


**Usage:**
```text
robotcode robot [OPTIONS] [ROBOT_OPTIONS_AND_ARGS]...
```


**Options:**
- `-ebl, --exclude-by-longname TEXT *`

   Excludes tests/tasks or suites by longname.


- `-bl, --by-longname TEXT *`

   Select tests/tasks or suites by longname.


- `--version`

   Show the version and exit.


- `--help`

   Show this message and exit.



Use `-- --help` to see `robot` help.


#### robot-debug

Run a real Robot Framework suite with the debugger attached (alias `run-
debug`).

Takes the same arguments as `robotcode robot`, but pauses at breakpoints so
you can inspect and step through the run at a debug prompt.


**Usage:**
```text
robotcode robot-debug [OPTIONS] [ROBOT_OPTIONS_AND_ARGS]...
```


**Options:**
- `--no-history`

   Don't load or save the persistent history file. In-session arrow-up recall still works, but nothing crosses session boundaries. Useful for AI-agent invocations or quick spike sessions you don't want polluting your shell's REPL history.


- `--backend [auto|prompt-toolkit|plain]`

   Force a specific input backend instead of auto-picking. `auto` and `prompt-toolkit` both pick the prompt-toolkit-driven interpreter (completion, syntax highlighting, history, doc viewer). `plain` drops to a bare `input()` prompt — useful when ANSI escapes or popups would interfere with the surrounding capture.  [default: auto]


- `--plain`

   Shorthand for `--backend=plain`. Disables all prompt enhancements — completion, syntax highlighting, candidate popup, auto-suggest, history file. The prompt becomes a bare `input()` call. Recommended for AI-agent invocations, automation pipelines, and any context where ANSI escapes or completion popups would interfere with stdin/stdout capture. Conflicts with `--backend=<other>`.


- `-ebl, --exclude-by-longname TEXT *`

   Excludes tests/tasks or suites by longname.


- `-bl, --by-longname TEXT *`

   Select tests/tasks or suites by longname.


- `--debugger-attached / --no-debugger-attached`

   Whether the debugger is active. While detached nothing pauses — a failing keyword just prints its error and you stay at the prompt — but breakpoints and exception filters stay configured. Default: attached for `robot-debug`; for `repl` detached, unless a pause trigger (`--break`, a `--break-on-*` flag) is given. Toggle at runtime with `.debug on` / `.debug off`.


- `--break LOCATION *`

   Break at LOCATION — a `file:line` or a keyword name. Repeatable.


- `--break-on-exception / --no-break-on-exception`

   Break at an uncaught failing keyword (not caught by TRY/EXCEPT or `Run Keyword And …`), before the failure unwinds. Armed by default; it only pauses while the debugger is attached (see `--debugger-attached`).


- `--break-on-all-exceptions / --no-break-on-all-exceptions`

   Break at EVERY failing keyword, even ones caught by TRY/EXCEPT or `Run Keyword And …`.  [default: no-break-on-all-exceptions]


- `--break-on-failed-test / --no-break-on-failed-test`

   Break at the end of a failing test.  [default: no-break-on-failed-test]


- `--break-on-failed-suite / --no-break-on-failed-suite`

   Break at the end of a failing suite.  [default: no-break-on-failed-suite]


- `--stop-on-entry`

   Break at the very first keyword.


- `--version`

   Show the version and exit.


- `--help`

   Show this message and exit.



Use `-- --help` to see `robot` help.


#### testdoc

Runs `testdoc` with the selected configuration, profiles, options and
arguments.

The options and arguments are passed to `testdoc` as is.


**Usage:**
```text
robotcode testdoc [OPTIONS] [ROBOT_OPTIONS_AND_ARGS]...
```


**Options:**
- `--version`

   Show the version and exit.


- `--help`

   Show this message and exit.



Use `-- --help` to see `testdoc` help.




<!-- END -->

## Getting Help

The command reference above is generated directly from the CLI, so it always matches the installed version. To get the same information on the command line, append `--help` to any command or sub-command, for example `robotcode analyze --help` or `robotcode results summary --help`.

For the commands that wrap a standard Robot Framework tool (`robot`, `rebot`, `libdoc`, `testdoc`), use `-- --help` to see the help of the underlying tool, e.g. `robotcode robot -- --help`.

## See Also

- [Configuration](./config.md) — how `robot.toml` and profiles work, the foundation for the `config` and `profiles` commands.
- [Discovering Tests](./discovering-tests.md) — details on the `discover` command.
- [Analyzing Results](./analyzing-results.md) — working with the `analyze` and `results` commands.
- [REPL](./repl.md) — using the interactive `repl` shell.
