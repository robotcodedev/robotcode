# Interactive development & exploration — `robotcode repl`

`robotcode repl` is an interactive Robot Framework shell that runs inside the project's configuration — the same `robot.toml`, profiles, Python environment, and imports a real run uses. You type keyword calls one line at a time and they execute immediately, and the session's state — variables, imports, library instances, open browsers and connections — persists for as long as it stays open. That makes it the tool for **interactive, step-by-step work**: *exploring* (drive a system under test, try a keyword or library, debug a misbehaving keyword as you call it, stabilize a locator or wait) and *developing* (build up a test case or reusable keyword one line at a time, confirm each step, then save it).

If the user wants to **watch** ("so I can see it", "live", "non-headless"), open the browser non-headless and keep the REPL open (`New Browser    headless=False` with Browser/Playwright; a normal `Open Browser` is already visible in SeleniumLibrary): a test run would close it the moment it finishes.

## Contents

- **Start or reuse a REPL** — how to run it, startup flags, imports
- **What you can run** — keywords, persistent assignments, control structures
- **Dot commands** — `.vars`, `.imports`, `.kw`, `.doc`, `.save`, …
- **Exit code** — what makes a session fail, `.exit CODE`
- **Debugging from the REPL** — interactive breakpoints and the `(rdb)` debugger
- **Relative imports** — bare paths need RF 7.4+
- **Explore the system under test** — the get-state → act → re-check pattern
- **Move experiments into tests** — `.save` and promotion *(optional)*

## Start or reuse a REPL

If a REPL session of this project is already open (`robotcode session list`), reuse it — do not close and reopen it between experiments.

**Can your shell tool keep a command running and write to its input?** Tools such as `write_stdin` or `send_to_terminal` do that; a background process that you feed through a file or a FIFO doesn't count.

- **Yes:** start `robotcode repl` there and work at its prompt: write one input, wait until the output ends with the prompt `>>> `, read the answer, then choose the next input from what you saw. `.exit` ends it.
- **No:** run the REPL as a **session**. It runs in the background and keeps its state — variables, imports, open browsers and connections — between your commands, and each command returns with the answer to one input: send one input, read the answer, then choose the next input from what you saw.

```bash
robotcode session start repl                    # prints "Started session repl-1a2b3c4d." — use this ID below
robotcode session send repl-1a2b3c4d 'Import Resource    ${CURDIR}/resources/accounts.resource'
robotcode session send repl-1a2b3c4d '${user}=    Create User    alice    role=admin'
robotcode session send repl-1a2b3c4d '.vars --user'
robotcode session stop repl-1a2b3c4d
```

- `start` takes the options and files of `robotcode repl` (`-v`, `-P`, `--source`, script files with `--inspect`, `--break …`); options of `robotcode` itself go before `session` (`robotcode -p dev session start repl`). The session runs in the folder you start it in.
- **One `send` is one whole input:** a statement, a whole `FOR` / `IF` / `TRY` block with its `END` as one argument of several lines, or one dot command. Don't send a block line by line: each `send` is complete. A dot command can't share a `send` with anything else.
- Quote the input in **single quotes**, so the shell leaves `${…}` alone; line breaks go inside the quotes. In PowerShell, use a here-string (`@'` … `'@`) for several lines.
- **The exit code of `send` tells you how the input went:** `0` it passed, `1` it failed (the output says why), `124` it still runs after `--timeout` (default 60 s; then `robotcode session wait <ID>` prints the rest), `252` an error of robotcode itself such as an unknown ID. `robotcode session status <ID>` prints `runs`, `waits` or `ended` without taking any output.
- `robotcode session interrupt <ID>` stops a statement that hangs, as `Ctrl-C` does.
- **End it** with `robotcode session stop <ID>` when the task is done; `robotcode session stop --project` ends all sessions of the project. `.exit` only ends the REPL: the session stays open, says `The REPL has ended with exit code N.`, `robotcode session result <ID>` prints that code, and `robotcode session restart <ID>` starts a fresh REPL under the same ID. A session that has waited 15 minutes without a request ends by itself (`--idle-timeout MINUTES` at the start).

**If a `robotcode session` command fails in a sandbox** — `Can't create the files of the session`, `Can't open the channel of the session`, `doesn't answer`, or the next command finds `No session '…' is open` — your agent runs each command in a sandbox of its own, and a session can't outlive that command or be reached from it. Don't try to leave the sandbox. Without a tool as described above, work out another way yourself. Sessions work as usual when the whole agent runs in one sandbox, such as a container or a virtual machine.

Startup options worth knowing (all optional):

- `robotcode repl <file> [...]` — **pre-execute** the keyword calls in one or more files (REPL syntax, not full suites), then exit. A file runs like a test body: an invalid statement fails with Robot Framework's message when execution reaches it and skips the rest of that file, and without `--inspect` the exit code is `1` if a statement failed. Add `--inspect` to drop into the interactive prompt afterwards with all the file's imports and variables still in scope.
- `-v name:value` / `-V <varfile.py|.yaml>` — seed variables into the session (same as `robot --variable` / `--variablefile`).
- `-P <path>` — add a library/module search path for this session (`robot --pythonpath`).
- `--show-keywords` — echo each executed keyword as it runs (a lightweight trace, useful when a higher-level keyword does several things).
- `--source <file>` — resolve relative imports against that file's **parent directory** (the REPL uses it as the working directory; the file itself is never read or written, so it need not exist).

Import the library or libraries you want to explore:

```robotframework
Import Library    Browser    timeout=20s
Import Library    RequestsLibrary
Import Library    Collections
```

There is **no `*** Settings ***` section**. Import via the BuiltIn keywords — and the Settings-style names work too, as **REPL-only aliases**, so `Library    Browser` and `Import Library    Browser` are equivalent at the prompt:

- `Import Library    <Name>    [args]    [AS    <alias>]` — or just `Library    <Name>    …`. (`WITH NAME` still works; `AS` is the current syntax.)
- `Import Resource    path/to/resource.robot` — or `Resource    …`.
- `Import Variables    path/to/vars.py` — or `Variables    …`.

Library search paths come from `robot.toml` (`python-path`). Pass import arguments as usual, e.g. `Import Library    DatabaseLibrary    db_api_module_name=sqlite3`.

## What you can run

The REPL is line-oriented but is **not limited to single keyword calls** — it understands the full Robot Framework test-body syntax:

- **Single keyword per line** — the common case; executes as soon as the line parses.
- **Variable assignment that persists** across the whole session: `${id}=    Set Variable    42`, then `Log    ${id}` on a later line. State (variables, imports, library instances, open browsers/connections) lives for the lifetime of the session.
- **The last keyword's return value** is always available as `${_}` — e.g. `Get Text    h1` then `Should Be Equal    ${_}    Welcome`.
- **Multi-line control structures** — `FOR`/`WHILE`/`IF`/`TRY`/`VAR` blocks work. In a session, send the whole block with its `END` in **one** `send`. At a prompt in a terminal, the REPL keeps reading continuation lines at the `...` prompt until the block's `END`.
  ```robotframework
  FOR    ${row}    IN    @{rows}
      Log    ${row}
  END
  ```

## Dot commands

Available at the `>>>` prompt (`.help` lists them, `.help <cmd>` shows details):

- `.vars [--user]` — list variables in scope with current values; `--user` hides Robot built-ins so only what you assigned shows.
- `.imports` — show which libraries and resource files are currently loaded, with keyword counts and source paths.
- `.kw [name-or-text]` — with a keyword name, full keyword documentation (signature, argument types, docstring, tags) without leaving the REPL. Names resolve as in a suite (case/space/underscore-insensitive), including the explicit `Owner.Keyword` form (e.g. `.kw BuiltIn.Log`) to disambiguate when several imports share a keyword name. With **no argument** it lists every loaded keyword grouped by library/resource; with **partial text** that isn't an exact keyword it lists the matching keyword names (`.kw click`).
- `.doc <name>` — full documentation for an imported library or resource. Only what the session has imported is shown, addressed by its namespace name (a library imported with `AS` is found under the alias).
- `.cwd` — print the working directory that relative imports/variable files resolve against.
- `.save [-a] [-t NAME] [--keep-failed] FILENAME` — export the session as a runnable `.robot` file (see *Move experiments into tests*).
- `.exit [CODE]` / `.quit [CODE]` — clean exit (aliases); with `CODE` the process exits with that code (see *Exit code*).

## Exit code

The session is one test, and it fails as soon as a statement fails without being handled. A failure caught by `TRY`/`EXCEPT`, `Run Keyword And Expect Error`, or `Run Keyword And Ignore Error` doesn't count, nor do `Skip` and `Pass Execution`. `robotcode session result <ID>` then prints `1`, and a script file without `--inspect` exits with it. `.exit CODE` ends the REPL with that code; `--nostatusrc`, or `no-status-rc = true` in `robot.toml`, keeps it at `0`.

## Debugging from the REPL

The same debugger is available for the **whole REPL session**, but it starts **detached** — attach it with `.debug on` (or start with `--debugger-attached`, or just pass `--break …`). Once attached you can debug a keyword *as you build it*: arm a breakpoint, run the keyword, and when it's hit, execution pauses at a `(rdb)` prompt with the live stack and variables. `.debug off` detaches again without losing your breakpoints.

This is for debugging a keyword **you call yourself at the prompt** while building or exploring it. To debug an existing test, [`robotcode robot-debug`](debugging.md) runs the real one in place ([why](../SKILL.md#a-real-test-case-the-debugger-not-the-repl)).

Breakpoints can be armed three ways — the interactive one is unique to the REPL:

- **Interactively, at the `>>>` prompt** (no restart): `.debug on` attaches the debugger (`.debug off` detaches, bare `.debug` shows the state); `.break <Keyword>`, `.break file.robot:42`, or conditional `.break Login, ${retries} > 3` — then run a keyword and it stops on the next hit (when that keyword runs, or when execution reaches that line). `.tbreak` is one-shot, `.breakpoints` lists them, `.delete` / `.disable` remove or pause them, and `.catch uncaught|all|test|suite` pauses on failures instead of locations.
- **From the start, via flags**: `robotcode repl --break "<Keyword>"` / `--break file.robot:42`, plus the `--break-on-*` exception flags, arm breakpoints before the first prompt — and passing any of them (or `--debugger-attached`) attaches the debugger from the start.
- **From the file**: an embedded `Breakpoint` keyword (after `Library    robotcode.repl.Repl`) pauses whenever the debugger is attached (in the REPL, once you've attached with `.debug on`) — a no-op in a normal `robot` run.

At a `(rdb)` stop you get the full debug command set — `.where`, `.vars`, `.print ${x}`, `.step` / `.next` / `.continue`, and the rest. It is the *same* debugger as [`robotcode robot-debug`](debugging.md), and **[debugging.md](debugging.md) is the full reference** for breakpoints, debug commands and stepping.

## Relative imports

Bare relative paths in the BuiltIn import keywords need RF 7.4+: `Import Resource    foo/my.resource` (and the `Import Library` / `Import Variables` path forms) only resolve against the importing file's directory starting in RF 7.4. On RF ≤ 7.3 such calls fail with `Resource file '...' does not exist.` — fall back to `${CURDIR}/foo/my.resource` or put the directory on the module search path.

## Explore the system under test

General pattern, independent of library:

1. Call a "get state" keyword to learn what is currently visible/available (page snapshot, API response, table contents).
2. Pick a stable identifier from that state.
3. Run the action keyword against that identifier.
4. Re-check the state to confirm the effect.

For non-UI libraries, run the action and inspect the returned value:

```robotframework
${response}=    GET    https://example.com/api/items
Log    ${response.json()}
```

Prefer stable IDs from the domain (primary keys, slugs, ISO codes) over volatile values (timestamps, generated UUIDs, list indices). For UI libraries (Browser, SeleniumLibrary, AppiumLibrary, …) the locator strategy and discovery helpers are library-specific — use the matching library skill if one is available in this plugin's `skills/` directory.

## Move experiments into tests *(optional — only when the goal is test creation)*

Skip this entirely if the task was pure exploration or a one-off automation job. When the goal *is* a polished, repeatable test or reusable keyword, this section gets you a runnable file; for the full authoring loop (reuse → conventions → `analyze code` → targeted run → refactor) hand off to [authoring.md](authoring.md).

When a keyword sequence works and should become a repeatable test, save it directly:

```
.save -t "My Scenario" scratch.robot
```

`.save` hoists `Import Library` / `Import Resource` calls into a `*** Settings ***` section and puts everything else into a `*** Test Cases ***` block. Inputs with parse errors are never exported, and inputs whose run failed or was skipped are left out too, so the file runs the way the session did; `--keep-failed` keeps the failed ones (an input ending in `Pass Execution` counts as passed). Use `-a` / `--append` to add to an existing file instead of overwriting; `-t` / `--test-name` overrides the generated test-case name.
