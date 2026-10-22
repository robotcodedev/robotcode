# Design

## Context

`RunTerminals` (`vscode-client/extension/runTerminals.ts`) creates each run terminal with `shellPath: process.execPath`, `shellArgs: [out/runTerminal.js]` and `ELECTRON_RUN_AS_NODE=1`. It listens on a Unix socket, on Windows a named pipe, and sends the script each run as a JSON line. The script (`vscode-client/runTerminal/index.ts`) does three things:
- it builds the line before a run with `commandLine.ts` and `shellIntegration.ts`;
- it starts the run with `stdio: "inherit"`;
- it waits in raw mode for a key or the next run.

Measured on a Windows 11 VM with VS Code 1.142 and its own node-pty, in Windows' ConPTY and in VS Code's `conpty.dll`:
- **`Code.exe` as the terminal's process:** it gets no console, nothing appears, `\\.\CONIN$` cannot be opened, and no key arrives.
- **`cmd.exe` in front:** `Code.exe` gets a console, but Ctrl+C breaks the terminal.
- **`python.exe` as the terminal's process:**
  - it gets a real console;
  - the run inherits that console, with stdin and stdout as terminals;
  - the shell integration sequences pass ConPTY;
  - each Ctrl+C reaches the run, the second ends a run that a first one is stopping, and the script stays;
  - a line typed at once is dropped, and a key ends the script.
- **Linux harness with the prototype and real runs:**
  - the shortened, quoted line and the robot icon;
  - reuse, and two runs at once;
  - Ctrl+C once and twice, and **Stop**;
  - a breakpoint;
  - **Copy Command** with the full quoted line;
  - closing on a key;
  - no activation in either Python mode.

The extension starts the debug launcher with the folder's interpreter: `robotcode.python`, or else the one selected in VS Code for the folder. A launch configuration can give its run another interpreter in `python`.

## Goals / Non-Goals

**Goals:**
- One script for Windows, Linux and macOS, with the same behavior as the Node.js script.
- Nothing visible changes on Linux and macOS.

**Non-Goals:**
- No change to the debug launcher, `runInRobotCodeTerminal` or the other console values.
- No new setting.
- No change to how the run's environment is merged, also not to the case of the keys on Windows.

## Decisions

### D1: The terminal's process is a Python script run with the folder's interpreter

The script `bundled/tool/utils/run_terminal.py` uses only the standard library and runs on Python 3.10 and newer, the oldest version RobotCode supports. It sits next to `check_robot_version.py`, which the extension also runs with the folder's interpreter, and `bundled/` goes into the package as it is.

The run terminal is created with:
- `shellPath`: the folder's interpreter, as for the debug launcher; a run keeps the interpreter of its launch configuration;
- `shellArgs`: `["-I", <script>]`, so that `PYTHONPATH`, the user's site packages and the working directory do not reach the script; the run still gets the whole environment;
- `env`: the address and the key, without `ELECTRON_RUN_AS_NODE`.

A reused terminal keeps the interpreter it started with; the script only starts each run with the run's own command line.

- **Alternative: the task terminal of VS Code.** It works on Windows, but it can neither show RobotCode's line before a run nor RobotCode's icon, so the maintainer rejected it.
- **Alternative: `cmd.exe` in front of `Code.exe`.** Ctrl+C breaks the terminal, as measured.
- **Alternative: Python only on Windows.** That would keep two scripts with the same behavior.
- **Alternative: the interpreter of the launch configuration (`python`).** It differs only when a configuration sets one. The run uses it anyway, and the debug launcher already needs the folder's interpreter.

### D2: TCP on 127.0.0.1, with connections bound to their terminal

The extension listens with `listen(0, "127.0.0.1")` and passes `127.0.0.1:<port>` to the script in `ROBOTCODE_RUN_TERMINAL_ADDRESS`. Python on Windows cannot read and write a named pipe that is open for synchronous I/O at the same time, because a read in progress holds a write back. Sockets have no such limit, and `socket` and `select` work for them on every platform.

A TCP port is open to every local process, unlike a Unix socket in the user's temporary folder. The extension therefore binds each connection to a terminal: its first message must be `ready` with the key of a terminal that is being created, or the connection is closed. The extension takes `ended` only from the connection of the terminal that has that run.

- **Alternative: keep the Unix socket on Linux and macOS, TCP only on Windows.** That gives two ways to say the same thing.
- **Alternative: asyncio's named pipes on Windows.** That puts more code into the script.

### D3: The text before a run comes from the extension

A `run` message carries `header`, the text the terminal shows before the run:
- `PROMPT_START`, the mark and `Executing: `;
- `COMMAND_START` and the shortened command line from `shownArgs`;
- a line break, then `COMMAND_EXECUTED` and the `E` sequence with the full command line.

The script writes it unchanged. The command line's quoting (`commandLine.ts`) and the escaping for VS Code (`shellIntegration.ts`) thus stay in TypeScript with their tests, and move into `vscode-client/extension/`. The script writes only its own text:
- `HasRichCommandDetection` at its start;
- the `D` sequence with the exit code after a run;
- the two lines of its wait, with the same mark.

### D4: The script

The script ports `index.ts`:
- **Start:** it connects and sends `ready` with its key.
- **A run:**
  - it writes the header;
  - it starts the run with `subprocess.Popen`, with the terminal as its console and the run's `cwd` and environment over the script's;
  - after the run it writes `D`, waits, and sends `ended` with the exit code;
  - an end by a signal on Linux and macOS counts as no exit code.
- **Busy:** a run that arrives while one is in progress gets `ended` with the error `busy`, as now.
- **Ctrl+C:** the script installs a SIGINT handler that does nothing. `SIG_IGN` would be inherited by the run on Linux and macOS, and Robot Framework would then not stop. On Windows the console sends each Ctrl+C to the run itself.
- **The wait:**
  - on Linux and macOS: raw mode with `termios`, and `select` on the terminal;
  - on Windows: `msvcrt.kbhit` and `getwch` every 20 ms;
  - in both, input that arrives within 50 ms as more than one key is dropped: **Rerun Command**, **Run Recent Command**, a paste. A single key or an escape sequence closes the terminal, and on Windows also a special key, which `getwch` gives as two characters.
- **A lost connection:** a thread reads the connection. When it closes, the script ends while it waits for its first run, shows "Press any key to close the terminal." while it waits after a run, or shows that line instead of the reuse line after a run in progress.
- **Output:** UTF-8 bytes through `sys.stdout.buffer`, which on Windows goes through the console's Unicode interface. On Windows the script also switches on the console's virtual terminal processing, which the measured Windows 11 already had on.

The module has no effect when imported; `main()` runs only as a script, so that tests can load it.

### D5: Tests

- **Python unit tests** in `tests/bundled/test_run_terminal.py`, which load the script from its file as `tests/scripts/` does:
  - which input counts as a single key: a character, an escape sequence, a Windows special key, a line;
  - the `D` sequence with and without an exit code.
- **Extension tests** in `runTerminals.test.ts`: the terminals run with a Python interpreter, from `ROBOTCODE_TEST_PYTHON` or else `python3` or `python` on the path. The runs use the same interpreter with `-c`, so whether the run's output is a terminal is checked on Windows too. The existing tests stay. A new one checks that a connection without a valid key gets no run and is closed.
- **CI:** the job `test-vscode` sets up Python before `npm test`. `CONTRIBUTING.md` says that `npm test` needs a Python interpreter.

### D6: What goes

- `vscode-client/runTerminal/index.ts` and its `tsconfig.json`;
- the project of `out/runTerminal.js` in `esbuild.mjs`.

`commandLine.ts` and `shellIntegration.ts` move to `vscode-client/extension/`, and their tests follow the new paths.

## Risks / Trade-offs

- [The script starts slower than Node.js on a slow machine: on the Windows VM, `ready` came after about 3 s.] → `READY_TIMEOUT` of 20 s stays.
- [An interpreter that cannot run the script, such as one older than 3.10, ends the terminal at once.] → The existing path for a terminal that closed at once shows an error and ends the session.
- [The script cannot be built or type-checked with the extension.] → ruff and mypy cover `bundled/tool/`, and the unit and extension tests run it.
- [A local process could connect to the port.] → It gets no run and cannot end one, see D2.
