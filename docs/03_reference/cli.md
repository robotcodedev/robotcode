# Command Line Interface

The robotcode CLI tool allows users to interact with Robot Framework directly from the command line. It supports various tasks such as project analysis, debugging, and configuration management.

The following sections outline the available commands, their usage, and the corresponding options.

<!-- START -->
## robotcode

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

   TODO: Analyzes a Robot Framework project.

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

- [`robot`](#robot)

   Runs `robot` with the selected configuration, profiles, options and arguments.

- [`testdoc`](#testdoc)

   Runs `testdoc` with the selected configuration, profiles, options and arguments.


**Aliases:**

- [`run`](#robot)

   Runs `robot` with the selected configuration, profiles, options and arguments.


### analyze

TODO: Analyzes a Robot Framework project.


**Usage:**
```text
robotcode analyze [OPTIONS] [PATHS]...
```


**Options:**
- `--version`

   Show the version and exit.


- `--help`

   Show this message and exit.


### clean

TODO: Cleans a Robot Framework project.

TODO: This is not implemented yet.


**Usage:**
```text
robotcode clean [OPTIONS]
```


**Options:**
- `--help`

   Show this message and exit.


### config

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


#### files

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


#### info

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


##### desc

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


##### list

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




#### root

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


#### show

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




### debug

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

   Waits until a debug client is connected.  [default: wait-for-client]


- `--wait-for-client-timeout FLOAT`

   Timeout in seconds for waiting for a connection with a debug client.  [default: 10]


- `--configuration-done-timeout FLOAT`

   Timeout to wait for a configuration from client.  [default: 10]


- `--debugpy / --no-debugpy`

   Enable/disable python debugging.  [default: no-debugpy]


- `--debugpy-wait-for-client / --no-debugpy-wait-for-client`

   Waits for a debugpy client to connect.


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

   Run in `tcp` server mode and listen at the given port. (Equivalent to `--mode tcp --port <port>`) *NOTE:* This option is mutually exclusive with options: pipe-name, mode, port, pipe-server.


- `--pipe-server NAME`

   Run in `pipe-server` mode and listen at the given pipe name. (Equivalent to `--mode pipe-server --pipe-name <name>`) *NOTE:* This option is mutually exclusive with options: tcp, bind, pipe-name, port, mode.


- `--mode [tcp|pipe-server]`

   The mode to use for the debug launch server. *NOTE:* This option is mutually exclusive with options: tcp, pipe-server.  [env var: ROBOTCODE_MODE; default: tcp]


- `--port PORT`

   The port to listen on or connect to. (Only valid for `tcp` and `socket mode`) *NOTE:* This option is mutually exclusive with options: pipe-name, pipe-server.  [env var: ROBOTCODE_PORT; default: 6612; 1<=x<=65535]


- `--bind ADDRESS`

   Specify alternate bind address. If no address is specified `localhost` is used. (Only valid for tcp and socket mode) *NOTE:* This option is mutually exclusive with options: pipe-name, pipe-server.  [env var: ROBOTCODE_BIND; default: 127.0.0.1]


- `--pipe-name NAME`

   The pipe to listen on or connect to. (Only valid in `pipe` and `pipe-server` mode) *NOTE:* This option is mutually exclusive with options: tcp, bind, port, pipe-server.  [env var: ROBOTCODE_PIPE_NAME]


- `--version`

   Show the version and exit.


- `--help`

   Show this message and exit.


### debug-launch

Launches a robotcode debug session.


**Usage:**
```text
robotcode debug-launch [OPTIONS]
```


**Options:**
- `--stdio`

   Run in `stdio` mode. (Equivalent to `--mode stdio`) *NOTE:* This option is mutually exclusive with options: pipe, tcp, socket, bind, pipe-server, pipe-name, port, mode.  [env var: ROBOTCODE_STDIO]


- `--tcp [<ADDRESS>:]<PORT>`

   Run in `tcp` server mode and listen at the given port. (Equivalent to `--mode tcp --port <port>`) *NOTE:* This option is mutually exclusive with options: pipe, stdio, socket, pipe-server, pipe-name, port, mode.


- `--socket [<ADDRESS>:]<PORT>`

   Run in `socket` mode and connect to the given port. (Equivalent to `--mode socket --port <port>`) *NOTE:* This option is mutually exclusive with options: pipe, stdio, tcp, pipe-server, pipe-name, port, mode.


- `--pipe NAME`

   Run in `pipe` mode and connect to the given pipe name. (Equivalent to `--mode pipe --pipe-name <name>`) *NOTE:* This option is mutually exclusive with options: stdio, socket, bind, pipe-server, tcp, pipe-name, port, mode.


- `--pipe-server NAME`

   Run in `pipe-server` mode and listen at the given pipe name. (Equivalent to `--mode pipe-server --pipe-name <name>`) *NOTE:* This option is mutually exclusive with options: pipe, stdio, socket, bind, tcp, pipe-name, port, mode.


- `--mode [stdio|tcp|socket|pipe|pipe-server]`

   The mode to use for the debug launch server. *NOTE:* This option is mutually exclusive with options: pipe, stdio, tcp, pipe-server, socket.  [env var: ROBOTCODE_MODE; default: stdio]


- `--port PORT`

   The port to listen on or connect to. (Only valid for `tcp` and `socket mode`) *NOTE:* This option is mutually exclusive with options: pipe, pipe-name, pipe-server.  [env var: ROBOTCODE_PORT; default: 6611; 1<=x<=65535]


- `--bind ADDRESS`

   Specify alternate bind address. If no address is specified `localhost` is used. (Only valid for tcp and socket mode) *NOTE:* This option is mutually exclusive with options: pipe, pipe-name, pipe-server.  [env var: ROBOTCODE_BIND; default: 127.0.0.1]


- `--pipe-name NAME`

   The pipe to listen on or connect to. (Only valid in `pipe` and `pipe-server` mode) *NOTE:* This option is mutually exclusive with options: pipe, stdio, tcp, bind, pipe-server, port, socket.  [env var: ROBOTCODE_PIPE_NAME]


- `--version`

   Show the version and exit.


- `--help`

   Show this message and exit.


### discover

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

- [`tests`](#tests)

   Discover tests with the selected configuration, profiles, options and arguments.


#### all

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

   Show the tags that are present.  [default: no-tags]


- `--exclude-by-longname TEXT`

   Excludes tests/tasks or suites by longname.


- `--version`

   Show the version and exit.


- `--by-longname TEXT`

   Select tests/tasks or suites by longname.


- `--full-paths / --no-full-paths`

   Show full paths instead of releative.  [default: no-full-paths]


- `--help`

   Show this message and exit.



Use `-- --help` to see `robot` help.


#### files

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


#### info

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


#### suites

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
- `--exclude-by-longname TEXT`

   Excludes tests/tasks or suites by longname.


- `--version`

   Show the version and exit.


- `--by-longname TEXT`

   Select tests/tasks or suites by longname.


- `--full-paths / --no-full-paths`

   Show full paths instead of releative.  [default: no-full-paths]


- `--help`

   Show this message and exit.



Use `-- --help` to see `robot` help.


#### tags

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


- `--full-paths / --no-full-paths`

   Show full paths instead of releative.  [default: no-full-paths]


- `--exclude-by-longname TEXT`

   Excludes tests/tasks or suites by longname.


- `--version`

   Show the version and exit.


- `--by-longname TEXT`

   Select tests/tasks or suites by longname.


- `--help`

   Show this message and exit.



Use `-- --help` to see `robot` help.


#### tests

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


- `--exclude-by-longname TEXT`

   Excludes tests/tasks or suites by longname.


- `--version`

   Show the version and exit.


- `--by-longname TEXT`

   Select tests/tasks or suites by longname.


- `--help`

   Show this message and exit.



Use `-- --help` to see `robot` help.




### language-server

Run Robot Framework Language Server.


**Usage:**
```text
robotcode language-server [OPTIONS] [PATHS]...
```


**Options:**
- `--stdio`

   Run in `stdio` mode. (Equivalent to `--mode stdio`) *NOTE:* This option is mutually exclusive with options: pipe, tcp, socket, bind, pipe-name, port, mode.  [env var: ROBOTCODE_STDIO]


- `--tcp [<ADDRESS>:]<PORT>`

   Run in `tcp` server mode and listen at the given port. (Equivalent to `--mode tcp --port <port>`) *NOTE:* This option is mutually exclusive with options: pipe, stdio, pipe-name, port, mode, socket.


- `--socket [<ADDRESS>:]<PORT>`

   Run in `socket` mode and connect to the given port. (Equivalent to `--mode socket --port <port>`) *NOTE:* This option is mutually exclusive with options: pipe, stdio, tcp, pipe-name, port, mode.


- `--pipe NAME`

   Run in `pipe` mode and connect to the given pipe name. (Equivalent to `--mode pipe --pipe-name <name>`) *NOTE:* This option is mutually exclusive with options: stdio, socket, bind, tcp, pipe-name, port, mode.


- `--mode [pipe|tcp|socket|stdio]`

   The mode to use for the debug launch server. *NOTE:* This option is mutually exclusive with options: pipe, stdio, socket, tcp.  [env var: ROBOTCODE_MODE; default: stdio]


- `--port PORT`

   The port to listen on or connect to. (Only valid for `tcp` and `socket mode`) *NOTE:* This option is mutually exclusive with options: pipe, pipe-name.  [env var: ROBOTCODE_PORT; default: 6610; 1<=x<=65535]


- `--bind ADDRESS`

   Specify alternate bind address. If no address is specified `localhost` is used. (Only valid for tcp and socket mode) *NOTE:* This option is mutually exclusive with options: pipe, pipe-name.  [env var: ROBOTCODE_BIND; default: 127.0.0.1]


- `--pipe-name NAME`

   The pipe to listen on or connect to. (Only valid in `pipe` and `pipe-server` mode) *NOTE:* This option is mutually exclusive with options: pipe, stdio, tcp, bind, port, socket.  [env var: ROBOTCODE_PIPE_NAME]


- `--version`

   Show the version and exit.


- `--help`

   Show this message and exit.


### libdoc

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


### new

TODO: Create a new Robot Framework project.

TODO: This is not implemented yet.


**Usage:**
```text
robotcode new [OPTIONS]
```


**Options:**
- `--help`

   Show this message and exit.


### profiles

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


#### list

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


#### show

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




### rebot

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


### robot

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
- `--exclude-by-longname TEXT`

   Excludes tests/tasks or suites by longname.


- `--version`

   Show the version and exit.


- `--by-longname TEXT`

   Select tests/tasks or suites by longname.


- `--help`

   Show this message and exit.



Use `-- --help` to see `robot` help.


### testdoc

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
