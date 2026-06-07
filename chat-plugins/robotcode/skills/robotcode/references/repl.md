# Interactive development & exploration — `robotcode repl`

`robotcode repl` is an interactive Robot Framework shell that runs inside the project's configuration — the same `robot.toml`, profiles, Python environment, and imports a real run uses. You type keyword calls one line at a time and they execute immediately, and the session's state — variables, imports, library instances, open browsers and connections — persists for as long as it stays open. That makes it the tool for **interactive, step-by-step work**: *exploring* (drive a system under test, try a keyword or library, debug a misbehaving keyword as you call it, stabilize a locator or wait) and *developing* (build up a test case or reusable keyword one line at a time, confirm each step, then save it). Reach for it even when the user never says "REPL" — "try this keyword interactively" or "let's build the test as we go" both point here.

The REPL serves **two distinct purposes** — use whichever fits the request:

- **Pure exploration / one-off task**: open a browser, call an API, query a database, gather information, report back. No test file is produced. Right when the user says "go to the site and check …", "look up …", "fetch …", "do X for me". If they want to **watch** ("so I can see it", "live", "non-headless"), open the browser non-headless and keep the session open — a test run would close it the moment it finishes.
- **Test development**: try a keyword sequence, confirm it works, then optionally promote it into a `.robot` test or reusable keyword (see *Move experiments into tests*).

Do **not** default to writing a test file when the intent is purely exploratory. Start in the REPL, complete the task, report the result — and only write a test afterwards if the user then asks for one. With Browser Library that means `New Browser    headless=False` (Playwright); with SeleniumLibrary a normal `Open Browser` is already visible.

Before guessing keyword arguments, inspect them with `robotcode libdoc <Library> list` and `robotcode libdoc <Library> show "<Keyword>"` (see the `libdoc` section in [SKILL.md](../SKILL.md)). Honor the existing `robot.toml` / `tests/*.robot` conventions.

## Contents

- **Start or reuse a REPL** — launch, agent backend, startup flags, imports
- **What you can run** — keywords, persistent assignments, control structures, inline Python
- **Dot commands** — `.vars`, `.imports`, `.kw`, `.doc`, `.save`, …
- **Debugging from the REPL** — interactive breakpoints and the `(rdb)` debugger
- **Gotchas** — no section headers, RF 7.4+ relative imports, clean shutdown
- **Explore the system under test** — the get-state → act → re-check pattern
- **Move experiments into tests** — `.save` and promotion *(optional)*
- **Validate changes** — `analyze code` + targeted run

## Start or reuse a REPL

If a RobotCode REPL terminal is already running, reuse it — do not close and reopen it between experiments.

Otherwise just start it:

```bash
robotcode repl
```

**No agent-specific flags are needed.** RobotCode detects when it runs under an AI agent (via env vars like `CLAUDECODE`, `CURSOR_AGENT`, `COPILOT_AGENT`, the generic `AI_AGENT`/`AGENT`, …) and automatically drops to the plain input backend — no completion popups, syntax highlighting, or ANSI escapes that would corrupt captured stdin/stdout, and no persistent history pollution. A human at a terminal gets the rich prompt-toolkit backend instead.

Override only if the auto-detection is wrong for your setup: `--plain` forces the plain backend, `--backend prompt-toolkit` forces the rich one, and `ROBOTCODE_NO_AI_AGENT=1` disables agent detection entirely.

Startup options worth knowing (all optional):

- `robotcode repl <file> [...]` — **pre-execute** the keyword calls in one or more files (REPL syntax, not full suites), then exit. Add `--inspect` to drop into the interactive prompt afterwards with all the file's imports and variables still in scope — handy for replaying a known-good setup before exploring further.
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

Library search paths are normally configured in `robot.toml` (`python-path`) and picked up automatically, so you should not need to set them manually. For libraries needing import-time arguments, pass them as positional/named args, e.g. `Import Library    DatabaseLibrary    db_api_module_name=sqlite3`.

## What you can run

The REPL is line-oriented but is **not limited to single keyword calls** — it understands the full Robot Framework test-body syntax:

- **Single keyword per line** — the common case; executes as soon as the line parses.
- **Variable assignment that persists** across the whole session: `${id}=    Set Variable    42`, then `Log    ${id}` on a later line. State (variables, imports, library instances, open browsers/connections) lives for the lifetime of the session.
- **The last keyword's return value** is always available as `${_}` — e.g. `Get Text    h1` then `Should Be Equal    ${_}    Welcome`.
- **Multi-line control structures** — `FOR`/`WHILE`/`IF`/`TRY`/`VAR` blocks work. Send the block line by line including its `END`; the REPL keeps reading continuation lines (`...` prompt) until the block parses, then runs it as a unit. When driving from an agent, just send the whole block as consecutive lines (the closing `END` completes it; a trailing blank line force-submits if needed):
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
- `.kw [name-or-text]` — with a keyword name, full keyword documentation (signature, argument types, docstring, tags) without leaving the REPL; in-session alternative to `robotcode libdoc <Library> show "<Keyword>"`. Names resolve as in a suite (case/space/underscore-insensitive), including the explicit `Owner.Keyword` form (e.g. `.kw BuiltIn.Log`) to disambiguate when several imports share a keyword name. With **no argument** it lists every loaded keyword grouped by library/resource; with **partial text** that isn't an exact keyword it lists the matching keyword names — handy for discovery (`.kw click` to find every click keyword).
- `.doc <name>` — full documentation for an imported library or resource. Only what the session has imported is shown, addressed by its namespace name (a library imported with `AS` is found under the alias); a name that isn't loaded reports that instead of showing an empty page.
- `.cwd` — print the working directory that relative imports/variable files resolve against.
- `.clear` — clear the screen.
- `.save [-a] [-t NAME] FILENAME` — export the session as a runnable `.robot` file (see *Move experiments into tests*).
- `.exit` / `.quit` — clean exit (aliases).

A **human** on the rich backend also gets Tab completion, syntax highlighting, persistent history, and shortcuts (F1 help · Ctrl-R search · Ctrl-L clear · Ctrl-D exit). In the doc viewer that `.kw`/`.doc` open, the keyword names in a `.kw` listing are follow-able links — Tab to one and press Enter to open its documentation, `[` to go back to the list. An agent on the plain backend uses the dot commands instead (the list comes back as plain text).

## Debugging from the REPL

The same debugger is available for the **whole REPL session**, but it starts **detached** — attach it with `.debug on` (or start with `--debugger-attached`, or just pass `--break …`). Once attached you can debug a keyword *as you build it*: arm a breakpoint, run the keyword, and when it's hit, execution pauses in a `(rdb)` prompt with the live call stack, the variables in each frame, a source listing, and the ability to run further keywords in the paused context. `.debug off` detaches again without losing your breakpoints.

This is for debugging a keyword **you call yourself at the prompt** while building or exploring it. To debug an **existing failing test**, don't paste or rebuild it in here — run the real one in place with [`robotcode robot-debug`](debugging.md), scoped to that one test by name (`-bl "<longname>"` / `-t "<name>"`, not the whole file), which keeps the suite's setup/teardown, variables, and imports intact.

Breakpoints can be armed three ways — the interactive one is unique to the REPL:

- **Interactively, at the `>>>` prompt** (no restart): `.debug on` attaches the debugger (`.debug off` detaches, bare `.debug` shows the state); `.break "<Keyword>"`, `.break file.robot:42`, or conditional `.break Login, ${retries} > 3` — then run a keyword and it stops on the next hit (when that keyword runs, or when execution reaches that line). `.tbreak` is one-shot, `.breakpoints` lists them, `.delete` / `.disable` remove or pause them, and `.catch uncaught|all|test|suite` pauses on failures instead of locations. (The *stepping/resume* commands — `.continue`, `.step`, … — only act once you're actually stopped; before that they report `not at a breakpoint`.)
- **From the start, via flags**: `robotcode repl --break "<Keyword>"` / `--break file.robot:42`, plus the `--break-on-*` exception flags, arm breakpoints before the first prompt — and passing any of them (or `--debugger-attached`) attaches the debugger from the start.
- **From the file**: an embedded `Breakpoint` keyword (after `Library    robotcode.repl.Repl`) pauses whenever the debugger is attached (in the REPL, once you've attached with `.debug on`) — a no-op in a normal `robot` run.

At a `(rdb)` stop you get the full debug command set — `.where` (stack), `.vars` (variables), `.print ${x}`, `.step` / `.next` / `.continue`, and the rest. It is the *same* debugger as [`robotcode robot-debug`](debugging.md), which attaches it to a real run through the runner (scoped to whatever test/suite you select) rather than to single keywords typed at the prompt — **[debugging.md](debugging.md) is the full reference** for the breakpoint types, every debug command, and stepping through a session interactively.

One trap: at the `(rdb)` prompt `Ctrl-C` / `Ctrl-D` **resume** the run (the opposite of the `>>>` prompt, where they exit) — leave a stop with `.continue` / `.detach` / `.abort`.

## Gotchas

- **No section headers in the REPL**: `*** Settings ***` / `*** Keywords ***` / `*** Test Cases ***` fail with `No keyword with name '...' found`. Import with `Import Library` / `Import Resource` / `Import Variables` — or the Settings-style aliases `Library` / `Resource` / `Variables`, which work at the prompt too.
- **The REPL debugger starts detached** — a failing keyword just prints its error and leaves you at the `>>>` prompt; nothing pauses (unlike `robotcode robot-debug`, which is attached). Attach with `.debug on` (or `--debugger-attached`, or by passing `--break …`) to make breakpoints and failures pause into `(rdb)`; `.debug off` detaches again, keeping your breakpoints and `.catch` filters.
- **Bare relative paths in the BuiltIn import keywords need RF 7.4+**: `Import Resource    foo/my.resource` (and the `Import Library` / `Import Variables` path forms) only resolve against the importing file's directory starting in RF 7.4. On RF ≤ 7.3 such calls fail with `Resource file '...' does not exist.` — fall back to `${CURDIR}/foo/my.resource` or put the directory on the module search path.
- **Send one statement at a time and wait for the prompt** before the next, so output doesn't interleave — but a "statement" can be a whole multi-line `FOR`/`IF`/`TRY` block (send its lines through to `END`), not only a single keyword. (The auto-selected plain backend keeps echo/escape sequences from corrupting captured I/O — see *Start or reuse a REPL*.)
- **`.exit` is the clean exit** — `Ctrl+D` may leave child processes (browser, DB connection, server, …) lingering.

### Close the REPL when done

Shut the REPL down so spawned subprocesses don't linger:

1. Type `.exit` (or `.quit`) at the `>>>` prompt and press Enter.
2. If that doesn't return to the shell, send `Ctrl+C` (once for graceful stop, twice if stuck).
3. As a last resort, kill the terminal/process running the REPL.

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

`.save` hoists `Import Library` / `Import Resource` calls into a `*** Settings ***` section and puts everything else into a `*** Test Cases ***` block. Failed lines are skipped automatically, so the result is always runnable. Use `-a` / `--append` to add to an existing file instead of overwriting; `-t` / `--test-name` overrides the generated test-case name.

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

Use the REPL again to reproduce the failing state and refine the keyword sequence, locator, or wait condition before editing the test.
