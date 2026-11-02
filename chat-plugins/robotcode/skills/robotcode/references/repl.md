# Interactive development & exploration — `robotcode repl`

`robotcode repl` is an interactive Robot Framework shell that runs inside the project's configuration — the same `robot.toml`, profiles, Python environment, and imports a real run uses. You type keyword calls one line at a time and they execute immediately, and the session's state — variables, imports, library instances, open browsers and connections — persists for as long as it stays open. That makes it the tool for **interactive, step-by-step work**: *exploring* (drive a system under test, try a keyword or library, debug a misbehaving keyword as you call it, stabilize a locator or wait) and *developing* (build up a test case or reusable keyword one line at a time, confirm each step, then save it).

The REPL serves **two distinct purposes** — use whichever fits the request:

- **Pure exploration / one-off task**: open a browser, call an API, query a database, gather information, report back. No test file is produced. Right when the user says "go to the site and check …", "look up …", "fetch …", "do X for me". If they want to **watch** ("so I can see it", "live", "non-headless"), open the browser non-headless and keep the session open (`New Browser    headless=False` with Browser/Playwright; a normal `Open Browser` is already visible in SeleniumLibrary) — a test run would close it the moment it finishes.
- **Test development**: try a keyword sequence, confirm it works, then optionally promote it into a `.robot` test or reusable keyword (see *Move experiments into tests*).

Do **not** default to writing a test file when the intent is purely exploratory. Start in the REPL, complete the task, report the result — and only write a test afterwards if the user then asks for one.

Before guessing keyword arguments, inspect them with `robotcode doc keywords <Library>` and `robotcode doc keyword <Library> "<Keyword>"` (see the `doc` section in [SKILL.md](../SKILL.md)). Honor the existing `robot.toml` / `tests/*.robot` conventions.

## Contents

- **Start or reuse a REPL** — launch, agent backend, startup flags, imports
- **What you can run** — keywords, persistent assignments, control structures, inline Python
- **Dot commands** — `.vars`, `.imports`, `.kw`, `.doc`, `.save`, …
- **Exit code** — when a session's exit code reports failures, `--statusrc`, `.exit CODE`
- **Debugging from the REPL** — interactive breakpoints and the `(rdb)` debugger
- **Gotchas** — no section headers, RF 7.4+ relative imports, clean shutdown
- **Explore the system under test** — the get-state → act → re-check pattern
- **Move experiments into tests** — `.save` and promotion *(optional)*
- **Validate changes** — `analyze code` + targeted run

## Start or reuse a REPL

If a REPL session of this project is already open (`robotcode session list`), reuse it — do not close and reopen it between experiments.

### Driving the REPL from an agent

Run the REPL as a **session**. It runs in the background and keeps its state — variables, imports, open browsers and connections — between your commands, and each command returns with the answer to one input. That gives you the same back-and-forth a person has at the prompt: send one input, read the answer, then choose the next input from what you saw.

```bash
robotcode session start repl                    # prints "Started session repl-1a2b3c4d." — use this ID below
robotcode session send repl-1a2b3c4d 'Import Resource    ${CURDIR}/resources/accounts.resource'
robotcode session send repl-1a2b3c4d '${user}=    Create User    alice    role=admin'
robotcode session send repl-1a2b3c4d '.vars --user'
robotcode session stop repl-1a2b3c4d
```

- `start` takes the options and files of `robotcode repl` (`-v`, `-P`, `--source`, script files with `--inspect`, `--break …`); options of `robotcode` itself go before `session` (`robotcode -p dev session start repl`). The session runs in the folder you start it in.
- **One `send` is one whole input:** a statement, a whole `FOR` / `IF` / `TRY` block with its `END` as one argument of several lines, or one dot command. Don't send a block line by line: each `send` is complete, so a block it leaves unfinished fails (`FOR loop must have closing END.`). A dot command can't share a `send` with anything else.
- Quote the input in **single quotes**, so the shell leaves `${…}` alone; line breaks go inside the quotes. In PowerShell, use a here-string (`@'` … `'@`) for several lines.
- **The exit code of `send` tells you how the input went:** `0` it passed, `1` it failed (the output says why), `124` it still runs after `--timeout` (default 60 s; then `robotcode session wait <ID>` prints the rest), `252` an error of robotcode itself such as an unknown ID. `robotcode session status <ID>` prints `runs`, `waits` or `ended` without taking any output.
- `robotcode session interrupt <ID>` stops a statement that hangs, as `Ctrl-C` does.
- **End it** with `robotcode session stop <ID>` when the task is done; `robotcode session stop --project` ends all sessions of the project. `.exit` only ends the REPL: the session stays open, says `The REPL has ended with exit code N.`, `robotcode session result <ID>` prints that code, and `robotcode session restart <ID>` starts a fresh REPL under the same ID. A session that has waited 15 minutes without a request ends by itself (`--idle-timeout MINUTES` at the start).

**If a `robotcode session` command fails in a sandbox** — `Can't create the files of the session`, `Can't open the channel of the session`, `doesn't answer`, or the next command finds `No session '…' is open` — your agent runs each command in a sandbox of its own, and a session can't outlive that command or be reached from it. Don't try to leave the sandbox. If your shell tool can keep a process running and write to its input, start `robotcode repl` in it directly: write one input, wait until the output ends with the prompt `>>> `, read the answer, then write the next. Otherwise work out another way yourself. Sessions work as usual when the whole agent runs in one sandbox, such as a container or a virtual machine.

Never start a bare `robotcode repl` with a command that waits for it to exit — it waits at its prompt forever.

**No agent-specific flags are needed.** RobotCode detects an AI agent (env vars like `CLAUDECODE`, `CURSOR_AGENT`, `COPILOT_AGENT`, `AI_AGENT`, …) and uses the plain input backend: no completion popups, highlighting or ANSI escapes in the captured output, and no history. `--plain` / `--backend prompt-toolkit` force a backend; `ROBOTCODE_NO_AI_AGENT=1` turns the detection off.

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

There is **no `*** Settings ***` section** — section headers fail with `No keyword with name '*** Settings ***' found`. Import via the BuiltIn keywords — and the Settings-style names work too, as **REPL-only aliases**, so `Library    Browser` and `Import Library    Browser` are equivalent at the prompt:

- `Import Library    <Name>    [args]    [AS    <alias>]` — or just `Library    <Name>    …`. (`WITH NAME` still works; `AS` is the current syntax.)
- `Import Resource    path/to/resource.robot` — or `Resource    …`.
- `Import Variables    path/to/vars.py` — or `Variables    …`.

Library search paths come from `robot.toml` (`python-path`). Pass import arguments as usual, e.g. `Import Library    DatabaseLibrary    db_api_module_name=sqlite3`.

## What you can run

The REPL is line-oriented but is **not limited to single keyword calls** — it understands the full Robot Framework test-body syntax:

- **Single keyword per line** — the common case; executes as soon as the line parses.
- **Variable assignment that persists** across the whole session: `${id}=    Set Variable    42`, then `Log    ${id}` on a later line. State (variables, imports, library instances, open browsers/connections) lives for the lifetime of the session.
- **The last keyword's return value** is always available as `${_}` — e.g. `Get Text    h1` then `Should Be Equal    ${_}    Welcome`.
- **Multi-line control structures** — `FOR`/`WHILE`/`IF`/`TRY`/`VAR` blocks work. In a session, send the whole block with its `END` in **one** `send`; it runs as a unit, and a block the input leaves unfinished fails with Robot Framework's error (`FOR loop must have closing END.`). Invalid complete input fails the same way (e.g. `ELSE branch cannot be empty.`). (At a terminal, the REPL keeps reading continuation lines at the `...` prompt until the block's `END`.)
  ```robotframework
  FOR    ${row}    IN    @{rows}
      Log    ${row}
  END
  ```
- **Inline Python** via `Evaluate`, e.g. `${n}=    Evaluate    len(@{items})`.

Useful inspection helpers while exploring:

- `Log    ${var}    formatter=repr` — print a value with its Python `repr`, so types and quoting are visible.
- `Log Many    @{list}` / `Log Many    &{dict}` — dump each item of a list or dict on its own line.
- `Log To Console    ${var}` — write directly to the terminal.

## Dot commands

Available at the `>>>` prompt (work in the plain agent backend too; `.help` lists them, `.help <cmd>` shows details):

- `.vars [--user]` — list variables in scope with current values; `--user` hides Robot built-ins so only what you assigned shows.
- `.imports` — show which libraries and resource files are currently loaded, with keyword counts and source paths.
- `.kw [name-or-text]` — with a keyword name, full keyword documentation (signature, argument types, docstring, tags) without leaving the REPL. Names resolve as in a suite (case/space/underscore-insensitive), including the explicit `Owner.Keyword` form (e.g. `.kw BuiltIn.Log`) to disambiguate when several imports share a keyword name. With **no argument** it lists every loaded keyword grouped by library/resource; with **partial text** that isn't an exact keyword it lists the matching keyword names (`.kw click`).
- `.doc <name>` — full documentation for an imported library or resource. Only what the session has imported is shown, addressed by its namespace name (a library imported with `AS` is found under the alias); a name that isn't loaded reports that instead of showing an empty page.
- `.cwd` — print the working directory that relative imports/variable files resolve against.
- `.clear` — clear the screen.
- `.save [-a] [-t NAME] [--keep-failed] FILENAME` — export the session as a runnable `.robot` file (see *Move experiments into tests*).
- `.exit [CODE]` / `.quit [CODE]` — clean exit (aliases); with `CODE` the process exits with that code (see *Exit code*).

## Exit code

The session is one test, and it fails as soon as a statement fails without being handled. A failure caught by `TRY`/`EXCEPT`, `Run Keyword And Expect Error`, or `Run Keyword And Ignore Error` doesn't count, nor do `Skip` and `Pass Execution`. How that reaches the exit code depends on how the session runs:

- **Non-interactive** — piped or redirected input, or script files without `--inspect`: exit code `1` if a statement failed, otherwise `0`.
- **Interactive** — stdin is a terminal: exit code `0` regardless of failures. This depends on stdin being a terminal, not on agent detection, so a session driven through a pseudo-terminal counts as interactive too.
- `--statusrc` makes the exit code report failures in any session; `--nostatusrc` — or `no-status-rc = true` in `robot.toml` — keeps it at `0`.
- `.exit CODE` ends the session with that code in any session. Dot commands work at the prompt and in piped input, not inside a script file.

With `-o output.xml`, the session test in the output files shows the same failures — also for an interactive session.

## Debugging from the REPL

The same debugger is available for the **whole REPL session**, but it starts **detached** — attach it with `.debug on` (or start with `--debugger-attached`, or just pass `--break …`). Once attached you can debug a keyword *as you build it*: arm a breakpoint, run the keyword, and when it's hit, execution pauses at a `(rdb)` prompt with the live stack and variables. `.debug off` detaches again without losing your breakpoints.

This is for debugging a keyword **you call yourself at the prompt** while building or exploring it. To debug an **existing failing test**, don't paste or rebuild it in here — run the real one in place with [`robotcode robot-debug`](debugging.md), scoped to that one test by name (`-bl "<longname>"` / `-t "<name>"`, not the whole file), which keeps the suite's setup/teardown, variables, and imports intact.

Breakpoints can be armed three ways — the interactive one is unique to the REPL:

- **Interactively, at the `>>>` prompt** (no restart): `.debug on` attaches the debugger (`.debug off` detaches, bare `.debug` shows the state); `.break <Keyword>`, `.break file.robot:42`, or conditional `.break Login, ${retries} > 3` — then run a keyword and it stops on the next hit (when that keyword runs, or when execution reaches that line). `.tbreak` is one-shot, `.breakpoints` lists them, `.delete` / `.disable` remove or pause them, and `.catch uncaught|all|test|suite` pauses on failures instead of locations. (The *stepping/resume* commands — `.continue`, `.step`, … — only act once you're actually stopped; before that they report `not at a breakpoint`.)
- **From the start, via flags**: `robotcode repl --break "<Keyword>"` / `--break file.robot:42`, plus the `--break-on-*` exception flags, arm breakpoints before the first prompt — and passing any of them (or `--debugger-attached`) attaches the debugger from the start.
- **From the file**: an embedded `Breakpoint` keyword (after `Library    robotcode.repl.Repl`) pauses whenever the debugger is attached (in the REPL, once you've attached with `.debug on`) — a no-op in a normal `robot` run.

At a `(rdb)` stop you get the full debug command set — `.where`, `.vars`, `.print ${x}`, `.step` / `.next` / `.continue`, and the rest. It is the *same* debugger as [`robotcode robot-debug`](debugging.md), and **[debugging.md](debugging.md) is the full reference** for breakpoints, debug commands and stepping.

One trap: at the `(rdb)` prompt `Ctrl-D` **resumes** the run (unlike the `>>>` prompt, where `Ctrl-D` exits) — leave a stop with `.continue` / `.detach` / `.abort`.

## Gotchas

- **No section headers in the REPL**: `*** Settings ***` / `*** Keywords ***` / `*** Test Cases ***` fail with `No keyword with name '...' found` — import with the `Import Library` / `Import Resource` / `Import Variables` keywords instead (see *Start or reuse a REPL* for the Settings-style aliases).
- **Bare relative paths in the BuiltIn import keywords need RF 7.4+**: `Import Resource    foo/my.resource` (and the `Import Library` / `Import Variables` path forms) only resolve against the importing file's directory starting in RF 7.4. On RF ≤ 7.3 such calls fail with `Resource file '...' does not exist.` — fall back to `${CURDIR}/foo/my.resource` or put the directory on the module search path.

### Close the REPL when done

Shut the REPL down so spawned subprocesses (browser, DB connection, server, …) don't linger — `.exit` is the clean exit:

- A session: `robotcode session stop <ID>` — it also stops a statement that still runs.
- A REPL you run in a terminal yourself: type `.exit` (or `.quit`) at the `>>>` prompt. If a statement still runs, send SIGTERM (`kill <pid>`): it stops the statement and ends the REPL with exit code `253`; a second SIGTERM forces the end.

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

Then extract the generated keyword calls into a reusable keyword when it will be used more than once:

```robotframework
Item Should Exist
    [Arguments]    ${item_id}
    ${response}=    GET    ${BASE_URL}/items/${item_id}
    Status Should Be    200    ${response}
    Should Be Equal    ${response.json()}[id]    ${item_id}
```

Keep tests focused on complete user/system flows rather than isolated keyword calls, and assert the observable outcome after each meaningful step.

## Validate changes

Run static analysis, then the project's headless/CI profile if one is defined:

```bash
robotcode analyze code tests
robotcode --profile ci robot
```

If tests fail, inspect with the `results` subcommands instead of opening raw `output.xml` — see [references/results.md](results.md):

```bash
robotcode results summary --failed
robotcode results log -bl "<full longname>"
```

If a test fails, debug it in place with [`robotcode robot-debug -bl "<longname>"`](debugging.md) — not by rebuilding it in the REPL (a REPL copy runs in a different context, without the suite's setup/teardown, variables, and imports). Use the REPL only to refine an *isolated* building block — a locator, a wait, a keyword sequence — before editing the test.
