# Command Line Interface (CLI)

The `robotcode` CLI tool enables seamless interaction with Robot Framework through the command line, offering a comprehensive set of features for project analysis, debugging, and configuration management.

The CLI tool is designed to be straightforward and user-friendly, with a broad range of commands to support various use cases, including test execution, documentation generation, and code analysis. It also supports configuration profiles, allowing users to define and quickly switch between different project setups as needed.

In most cases, not all CLI components are required within a single project. For example, in a CI (Continuous Integration) environment, only the `runner` package is typically necessary to execute tests, while the `language-server` package is generally not needed. The `analyze` package is mainly useful in a development environment to detect syntax errors and validate code, but it may be unnecessary in production or deployment environments. Similarly, the `debugger` package is essential for local development when troubleshooting test cases but isn’t usually required in production or CI pipelines.

To accommodate these varied needs, `robotcode` is organized into separate packages that each focus on specific functions. The core package, `robotcode`, provides foundational support for working with `robot.toml` configuration files and profile management. Here’s a more detailed breakdown of each package and its capabilities:

- **`runner` Package**:
  This package is essential for users who need to run and manage tests within Robot Framework projects. It includes commands for executing tests, generating documentation, and discovering test elements. This package is especially important in CI/CD pipelines, where automation of test execution is a primary focus.
  - **Commands**:
    - `robot`, `rebot`, `libdoc`: Enhanced versions of the standard Robot Framework tools, with support for `robot.toml` configuration files and profiles, allowing customized setups for different environments or testing requirements.
    - `discover`: Searches the project for tests, suites, tags, tasks, and other elements, providing a quick overview of available test cases and project structure.

- **`analyze` Package**:
  This package provides tools for detailed inspection and validation of Robot Framework code, helping users identify errors and improve code quality. The `analyze` package is typically more useful in development environments where code quality checks and error detection are needed before moving tests to a CI or production environment.
  - **Commands**:
    - `analyze`: Analyzes Robot Framework scripts for syntax errors, undefined keywords, and other potential issues, allowing early detection of problems and ensuring adherence to best practices.

- **`debugger` Package**:
  The debugger package enables powerful debugging capabilities for Robot Framework tests by providing a Debug Adapter Protocol (DAP)-compatible debugger. This package is most beneficial in development or local testing environments where developers need to diagnose and troubleshoot test issues. A DAP client, such as Visual Studio Code, can be connected to initiate and control debug sessions, enabling features like setting breakpoints, stepping through code, and inspecting variables.
  - **Commands**:
    - `debug`: Starts a DAP-compatible debug session for Robot Framework tests. This tool requires a DAP client to connect to the debug session, such as Visual Studio Code, which can then interface with the debugger and provide interactive debugging tools to analyze code behavior and troubleshoot issues effectively.

- **`repl` Package**:
  The REPL (Read-Eval-Print Loop) package provides an interactive, real-time environment for executing Robot Framework commands. It’s ideal for experimenting with keywords, testing ideas, and performing quick debugging without needing to create full test files. This package is mainly used in local development or testing environments where users can quickly prototype or troubleshoot commands.
  - **Commands**:
    - `repl`: Launches an interactive Robot Framework shell where users can execute commands line-by-line, ideal for quick testing and experimentation.

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
pip install robotcode[language-server]
```

To install all packages, including optional dependencies, use:

```bash
pip install robotcode[all]
```

This includes additional tools, such as [`robocop`](https://robocop.readthedocs.io) for linting and [`robotidy`](https://robotidy.readthedocs.io) for code formatting, which further enhance the development experience with Robot Framework.


## Commands

The following sections outline all available commands, their usage, and the corresponding options.

<!-- START -->
### robotcode

A CLI tool for Robot Framework.


**Usage:**
```text
robotcode [OPTIONS] COMMAND [ARGS]...
```


**Options:**
- `-c, --config PATH`

   Config file to use. Can be specified multiple times. If not specified, the default config file is used.  [env var: ROBOTCODE_CONFIG_FILES]


- `-p, --profile TEXT`

   The Execution Profile to use. Can be specified multiple times. If not specified, the default profile is used.  [env var: ROBOTCODE_PROFILES]


- `-r, --root DIRECTORY`

   Specifies the root path to be used for the project. It will be automatically detected if not provided.  [env var: ROBOTCODE_ROOT]


- `--no-vcs`

   Ignore version control system directories (e.g., .git, .hg) when detecting the project root.  [env var: ROBOTCODE_NO_VCS]


- `-f, --format [toml|json|json-indent|text]`

   Set the output format.


- `-d, --dry`

   Dry run, do not execute any commands.  [env var: ROBOTCODE_DRY]


- `--color / --no-color`

   Whether or not to display colored output (default is auto-detection).  [env var: ROBOTCODE_COLOR]


- `--pager / --no-pager`

   Whether or not use a pager to display long text or data.  [env var: ROBOTCODE_PAGER]


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


- `--version`

   Show the version and exit.


- `--help`

   Show this message and exit.


**Commands:**

- [`analyze`](#analyze)

   The analyze command provides various subcommands for analyzing Robot Framework code.

- [`clean`](#clean)

   TODO: Cleans a Robot Framework project.

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

- [`new`](#new)

   TODO: Create a new Robot Framework project.

- [`profiles`](#profiles)

   Shows information on defined profiles.

- [`rebot`](#rebot)

   Runs `rebot` with the selected configuration, profiles, options and arguments.

- [`repl`](#repl)

   Run Robot Framework interactively.

- [`robot`](#robot)

   Runs `robot` with the selected configuration, profiles, options and arguments.

- [`testdoc`](#testdoc)

   Runs `testdoc` with the selected configuration, profiles, options and arguments.


**Aliases:**

- [`shell`](#repl)

   Run Robot Framework interactively.

- [`run`](#robot)

   Runs `robot` with the selected configuration, profiles, options and arguments.


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

- [`code`](#code)

   Performs static code analysis to detect syntax errors, missing keywords or variables, missing arguments, and more on the given *PATHS*.


##### code

Performs static code analysis to detect syntax errors, missing keywords or
variables, missing arguments, and more on the given *PATHS*. *PATHS* can be
files or directories. If no PATHS are given, the current directory is used.

Examples:
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


- `-f, --filter PATTERN`

   Glob pattern to filter files to analyze. Can be specified multiple times.         


- `-v, --variable name:value`

   Set variables in the test data. see `robot --variable` option.


- `-V, --variablefile PATH`

   Python or YAML file file to read variables from. see `robot --variablefile` option.


- `-P, --pythonpath PATH`

   Additional locations where to search test libraries and other extensions when they are imported. see `robot --pythonpath` option.


- `-mi, --modifiers-ignore CODE`

   Specifies the diagnostics codes to ignore.


- `-me, --modifiers-error CODE`

   Specifies the diagnostics codes to treat as errors.


- `-mw, --modifiers-warning CODE`

   Specifies the diagnostics codes to treat as warning.


- `-mI, --modifiers-information CODE`

   Specifies the diagnostics codes to treat as information.


- `-mh, --modifiers-hint CODE`

   Specifies the diagnostics codes to treat as hint.


- `--help`

   Show this message and exit.




#### clean

TODO: Cleans a Robot Framework project.

TODO: This is not implemented yet.


**Usage:**
```text
robotcode clean [OPTIONS]
```


**Options:**
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

   Run in `tcp` server mode and listen at the given port. (Equivalent to `--mode tcp --port <port>`) *NOTE:* This option is mutually exclusive with options: mode, port, pipe-server, pipe-name.


- `--pipe-server NAME`

   Run in `pipe-server` mode and listen at the given pipe name. (Equivalent to `--mode pipe-server --pipe-name <name>`) *NOTE:* This option is mutually exclusive with options: bind, mode, tcp, port, pipe-name.


- `--mode [tcp|pipe-server]`

   The mode to use for the debug launch server. *NOTE:* This option is mutually exclusive with options: tcp, pipe-server.  [env var: ROBOTCODE_MODE; default: tcp]


- `--port PORT`

   The port to listen on or connect to. (Only valid for `tcp` and `socket mode`) *NOTE:* This option is mutually exclusive with options: pipe-server, pipe-name.  [env var: ROBOTCODE_PORT; default: 6612; 1<=x<=65535]


- `--bind ADDRESS`

   Specify alternate bind address. If no address is specified `localhost` is used. (Only valid for tcp and socket mode) *NOTE:* This option is mutually exclusive with options: pipe-server, pipe-name.  [env var: ROBOTCODE_BIND; default: 127.0.0.1]


- `--pipe-name NAME`

   The pipe to listen on or connect to. (Only valid in `pipe` and `pipe-server` mode) *NOTE:* This option is mutually exclusive with options: bind, tcp, port, pipe-server.  [env var: ROBOTCODE_PIPE_NAME]


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

   Run in `stdio` mode. (Equivalent to `--mode stdio`) *NOTE:* This option is mutually exclusive with options: bind, socket, pipe, mode, tcp, port, pipe-server, pipe-name.  [env var: ROBOTCODE_STDIO]


- `--tcp [<ADDRESS>:]<PORT>`

   Run in `tcp` server mode and listen at the given port. (Equivalent to `--mode tcp --port <port>`) *NOTE:* This option is mutually exclusive with options: socket, pipe, mode, port, pipe-server, pipe-name, stdio.


- `--socket [<ADDRESS>:]<PORT>`

   Run in `socket` mode and connect to the given port. (Equivalent to `--mode socket --port <port>`) *NOTE:* This option is mutually exclusive with options: pipe, mode, tcp, port, pipe-server, pipe-name, stdio.


- `--pipe NAME`

   Run in `pipe` mode and connect to the given pipe name. (Equivalent to `--mode pipe --pipe-name <name>`) *NOTE:* This option is mutually exclusive with options: bind, socket, mode, tcp, port, pipe-server, pipe-name, stdio.


- `--pipe-server NAME`

   Run in `pipe-server` mode and listen at the given pipe name. (Equivalent to `--mode pipe-server --pipe-name <name>`) *NOTE:* This option is mutually exclusive with options: bind, socket, pipe, mode, tcp, port, pipe-name, stdio.


- `--mode [stdio|tcp|socket|pipe|pipe-server]`

   The mode to use for the debug launch server. *NOTE:* This option is mutually exclusive with options: socket, pipe, tcp, pipe-server, stdio.  [env var: ROBOTCODE_MODE; default: stdio]


- `--port PORT`

   The port to listen on or connect to. (Only valid for `tcp` and `socket mode`) *NOTE:* This option is mutually exclusive with options: pipe-name, pipe-server, pipe.  [env var: ROBOTCODE_PORT; default: 6611; 1<=x<=65535]


- `--bind ADDRESS`

   Specify alternate bind address. If no address is specified `localhost` is used. (Only valid for tcp and socket mode) *NOTE:* This option is mutually exclusive with options: pipe-name, pipe-server, pipe.  [env var: ROBOTCODE_BIND; default: 127.0.0.1]


- `--pipe-name NAME`

   The pipe to listen on or connect to. (Only valid in `pipe` and `pipe-server` mode) *NOTE:* This option is mutually exclusive with options: bind, socket, pipe, tcp, port, pipe-server, stdio.  [env var: ROBOTCODE_PIPE_NAME]


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


- `--by-longname TEXT`

   Select tests/tasks or suites by longname.


- `--version`

   Show the version and exit.


- `--exclude-by-longname TEXT`

   Excludes tests/tasks or suites by longname.


- `--full-paths / --no-full-paths`

   Show full paths instead of releative.  [default: no-full-paths]


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

   Show full paths instead of releative.  [default: no-full-paths]


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
- `--by-longname TEXT`

   Select tests/tasks or suites by longname.


- `--version`

   Show the version and exit.


- `--exclude-by-longname TEXT`

   Excludes tests/tasks or suites by longname.


- `--full-paths / --no-full-paths`

   Show full paths instead of releative.  [default: no-full-paths]


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

   Show full paths instead of releative.  [default: no-full-paths]


- `--by-longname TEXT`

   Select tests/tasks or suites by longname.


- `--version`

   Show the version and exit.


- `--exclude-by-longname TEXT`

   Excludes tests/tasks or suites by longname.


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

   Show full paths instead of releative.  [default: no-full-paths]


- `--by-longname TEXT`

   Select tests/tasks or suites by longname.


- `--version`

   Show the version and exit.


- `--exclude-by-longname TEXT`

   Excludes tests/tasks or suites by longname.


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

   Show full paths instead of releative.  [default: no-full-paths]


- `--by-longname TEXT`

   Select tests/tasks or suites by longname.


- `--version`

   Show the version and exit.


- `--exclude-by-longname TEXT`

   Excludes tests/tasks or suites by longname.


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

   Run in `stdio` mode. (Equivalent to `--mode stdio`) *NOTE:* This option is mutually exclusive with options: bind, socket, pipe, mode, tcp, port, pipe-name.  [env var: ROBOTCODE_STDIO]


- `--tcp [<ADDRESS>:]<PORT>`

   Run in `tcp` server mode and listen at the given port. (Equivalent to `--mode tcp --port <port>`) *NOTE:* This option is mutually exclusive with options: socket, pipe, mode, port, pipe-name, stdio.


- `--socket [<ADDRESS>:]<PORT>`

   Run in `socket` mode and connect to the given port. (Equivalent to `--mode socket --port <port>`) *NOTE:* This option is mutually exclusive with options: pipe, mode, tcp, port, pipe-name, stdio.


- `--pipe NAME`

   Run in `pipe` mode and connect to the given pipe name. (Equivalent to `--mode pipe --pipe-name <name>`) *NOTE:* This option is mutually exclusive with options: bind, socket, mode, tcp, port, pipe-name, stdio.


- `--mode [stdio|tcp|socket|pipe]`

   The mode to use for the debug launch server. *NOTE:* This option is mutually exclusive with options: stdio, tcp, socket, pipe.  [env var: ROBOTCODE_MODE; default: stdio]


- `--port PORT`

   The port to listen on or connect to. (Only valid for `tcp` and `socket mode`) *NOTE:* This option is mutually exclusive with options: pipe-name, pipe.  [env var: ROBOTCODE_PORT; default: 6610; 1<=x<=65535]


- `--bind ADDRESS`

   Specify alternate bind address. If no address is specified `localhost` is used. (Only valid for tcp and socket mode) *NOTE:* This option is mutually exclusive with options: pipe-name, pipe.  [env var: ROBOTCODE_BIND; default: 127.0.0.1]


- `--pipe-name NAME`

   The pipe to listen on or connect to. (Only valid in `pipe` and `pipe-server` mode) *NOTE:* This option is mutually exclusive with options: bind, socket, pipe, tcp, port, stdio.  [env var: ROBOTCODE_PIPE_NAME]


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


#### new

TODO: Create a new Robot Framework project.

TODO: This is not implemented yet.


**Usage:**
```text
robotcode new [OPTIONS]
```


**Options:**
- `--help`

   Show this message and exit.


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

Run Robot Framework interactively.


**Usage:**
```text
robotcode repl [OPTIONS] [FILES]...
```


**Options:**
- `-v, --variable name:value`

   Set variables in the test data. see `robot --variable` option.


- `-V, --variablefile PATH`

   Python or YAML file file to read variables from. see `robot --variablefile` option.


- `-P, --pythonpath PATH`

   Additional locations where to search test libraries and other extensions when they are imported. see `robot --pythonpath` option.


- `-k, --show-keywords`

   Executed keywords will be shown in the output.


- `-i, --inspect`

   Activate inspection mode. This forces a prompt to appear after the REPL script is executed.


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
- `--by-longname TEXT`

   Select tests/tasks or suites by longname.


- `--version`

   Show the version and exit.


- `--exclude-by-longname TEXT`

   Excludes tests/tasks or suites by longname.


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
