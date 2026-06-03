# Interactive Robot Framework with `robotcode repl`

Trying out a single Robot Framework keyword usually means more ceremony than the keyword call itself — write a `.robot` file with `*** Settings ***` and `*** Test Cases ***` headers, import the right library, run `robot`, open `log.html`, find your test, read the output. For a one-liner you just want to *try*, that's a lot of overhead, and the file lingers in the tree afterwards.

**`robotcode repl`** removes the ceremony. It's an interactive shell that runs Robot Framework syntax line by line through the same execution engine as `robotcode robot` — same library loading, same variable scoping, same keyword resolution — but with no `.robot` file, no boilerplate sections, and no output artefacts unless you ask for them. Type a keyword, press Enter, see the result. State persists across lines within a session, so you can import a library, build up a variable, then call a keyword on it, all without leaving the prompt.

Reach for it whenever "let me just *try* it" would be faster than writing a one-off test file — library exploration, keyword debugging, environment sanity checks, ad-hoc spikes.

`robotcode repl` is also a **command-line debugger**. `robotcode robot-debug` runs a real `.robot` suite through the same runner as `robotcode robot`, but pauses at breakpoints — a `file:line`, a keyword name, an embedded `Breakpoint` keyword, or the first uncaught failure — and drops you into a `pdb`-style debug prompt with the live call stack, per-frame variables, a source listing, and the ability to run any keyword in the paused context. The interactive shell has the same debugger attached. See [Debugging](#debugging).

**Who this is for:**

- **Developers exploring an unfamiliar library** — `Import Library SeleniumLibrary`, then start calling keywords and watching what they do, without spinning up a full test.
- **Anyone debugging a keyword in isolation** — replicate the exact arguments a failing test passes and step through the response without re-running the whole suite.
- **Quick spike scripts** — try out an XPath, prototype a data-extraction snippet, validate that a library import works in the current environment.
- **AI-driven workflows** — coding agents (Claude Code, Cursor, Copilot, …) that need to call Robot Framework keywords interactively for test development or library exploration. Piping a snippet through `robotcode repl` is often faster than spawning a full `robot` run and parsing the output.
- **Teaching / demos** — show a live keyword call with its arguments and assignment without a slide full of `*** Settings ***`.

Typical things you can do with it:

- import a library and call any of its keywords with arguments
- assign and reference variables across multiple lines (state persists for the session)
- run control structures (FOR, WHILE, IF, TRY) interactively, multi-line
- execute a `.robotrepl` script and either exit or drop into the prompt afterwards
- generate a `log.html` / `report.html` / `output.xml` from the interactive session, just like a normal `robot` run
- set breakpoints and step through a real suite (or a keyword you run at the prompt) with a `pdb`-style debug prompt

This is intentionally **not** a replacement for writing real test files. It's the lightweight cousin: same engine, immediate feedback, no persistence unless you ask for it.

## Quick start

```bash
# Interactive prompt
robotcode repl

# Execute a REPL script, then exit
robotcode repl spike.robotrepl

# Execute a REPL script, then drop into the prompt
robotcode repl --inspect spike.robotrepl

# Pre-set variables for the whole session
robotcode repl -v BASE_URL:https://staging.example.com -v RETRIES:3

# Add a directory to the library search path
robotcode repl -P ./resources

# Capture a log.html / output.xml from the session
robotcode repl -d ./repl-output -o output.xml -l log.html

# Debug a real suite: pause at a line, step, inspect (see "Debugging")
robotcode robot-debug --break login.robot:42 tests/

# Pause at the very first keyword of a run
robotcode robot-debug --stop-on-entry tests/login.robot
```

## `repl` and `robot-debug`

Two commands:

| Command | What it does |
| --- | --- |
| `robotcode repl` (alias `shell`) | The interactive shell described on this page. Every existing `robotcode repl …` invocation keeps working unchanged. The debugger is attached (an embedded `Breakpoint`, `--break`, or an uncaught failure — on by default — pauses a keyword you run at the prompt). |
| `robotcode robot-debug` (alias `run-debug`) | Runs a real `.robot` suite through the normal runner with the debugger attached. Takes the same arguments as [`robotcode robot`](cli.md#robot) plus the debugger trigger flags. See [Debugging](#debugging). |

The shell-specific flags (`-v`, `-P`, `-d/-o/-l/-r/-x`, `--source`, `--inspect`, `--show-keywords`, and `.robotrepl` file arguments) live on `repl`. `robot-debug` instead accepts the full `robotcode robot` option set. The prompt/backend flags (`--backend`, `--plain`, `--no-history`) and the debugger triggers (`--break`, the `--break-on-*` exception flags, and — on `robot-debug` — `--stop-on-entry`) work on both.

## How the prompt works

When stdin is a terminal, `repl` shows the standard Robot Framework prompts:

- `>>> ` — primary prompt; type a single keyword line and press Enter to execute.
- `... ` — continuation prompt; appears when you've started a multi-line construct (`FOR`, `WHILE`, `IF`, `TRY`) that's not closed yet.

To **exit** the prompt, press Enter on an empty `>>> ` line. `Ctrl-C` clears the current multi-line buffer (or exits if there's no buffer).

When stdin is **not a terminal** (piped input, heredoc), prompts are suppressed and the REPL reads input until EOF. That makes it scriptable:

```bash
# bash / zsh — heredoc, exits when EOF is reached
robotcode repl <<'EOF'
${x}=    Set Variable    42
Log To Console    answer is ${x}
EOF

# bash / zsh — pipe a one-liner
printf 'Log To Console    hello\n' | robotcode repl
```

```powershell
# PowerShell — single-quoted here-string preserves ${x} verbatim
@'
${x}=    Set Variable    42
Log To Console    answer is ${x}
'@ | robotcode repl

# PowerShell — pipe a one-liner
'Log To Console    hello' | robotcode repl
```

## Prompt features

Two backends, no platform-specific caveats:

- **`prompt-toolkit`** (default) — rich line editor with candidate popup, syntax highlighting, signature toolbar, Ctrl-R reverse search, fish-style auto-suggest, multi-line cursor movement, persistent history, fullscreen doc viewer with mouse + search.
- **`plain`** — basic prompt fallback. No history, no completion, no popup. Active when you select it explicitly (`--plain` / `--backend=plain`), when stdin isn't an interactive terminal (piped input, heredoc, redirected file, CI), or when AI-agent detection falls back to it.

### Picking a specific input backend

The REPL uses the `prompt-toolkit` backend by default. Pass `--backend` (or set `ROBOTCODE_REPL_BACKEND`) to force a specific one:

| Value | Effect |
| ----- | ------ |
| `auto` (default) | prompt-toolkit on an **interactive terminal**; on piped/redirected stdin (`echo … \| robotcode repl`, heredocs, CI) — or inside a recognised AI agent — it falls back to `plain` automatically. |
| `prompt-toolkit` | Use the rich editor backend (same as `auto`; explicit form for clarity in scripts). |
| `plain` | Bypass the editor layer and fall back to a basic prompt. |

#### Disabling all enhancements (AI agents, automation)

`--plain` (or `ROBOTCODE_REPL_PLAIN=1`) is a shorthand for `--backend=plain`. It falls back to a basic prompt — no history, no completion, no candidate popup, no auto-suggest, no syntax highlighting. Use this for AI-agent invocations or automation pipelines where ANSI escape sequences and completion popups would corrupt stdin/stdout capture.

```bash
# AI-agent style: pipe input, capture clean output
ROBOTCODE_REPL_PLAIN=1 robotcode repl <<'EOF'
Log To Console    hello from agent
EOF
```

You usually don't need `--plain` for **piped or redirected** input either: when stdin isn't an interactive terminal (`echo … | robotcode repl`, heredocs, CI), the default `auto` backend already falls back to `plain` and reads until EOF. The same happens inside a known AI agent — `robotcode` detects popular agent environments (Claude Code, Cursor, Copilot CLI, OpenCode, Codex, …) and falls through to `plain` automatically. See [AI-agent detection](./ai-agents.md#ai-agent-detection) for the full list of marker env vars and the override hatches. (Pass `--plain` explicitly only when you want it on an interactive terminal too.)

Combining `--plain` with a non-`plain` `--backend` value is rejected as a usage error; combining it with `--no-history` is fine (plain mode has no history file anyway).

### History across sessions

Available on the prompt-toolkit backend; the plain backend has no history. Every command you press Enter on is saved to a history file. Arrow-up recalls the previous line, `Ctrl-R` runs incremental reverse-search over the whole history — same keybindings as bash or Python's own shell.

The history file lives in:

- `{project_root}/.robotcode_cache/repl_history` when the REPL is launched from inside a project (detected by `robot.toml` / `.robot.toml` / `pyproject.toml` / `.git` / `.hg`)
- the per-user cache directory otherwise — `~/.cache/robotcode/repl_history` on Linux, `~/Library/Caches/robotcode/repl_history` on macOS, `%LOCALAPPDATA%\robotcode\Cache\repl_history` on Windows
- `${ROBOTCODE_CACHE_DIR}/repl_history` if the env var is set — overrides both of the above

If you upgrade from an earlier build of robotcode whose history file used a different format, the old file is ignored on first read and new entries are written in the current format. The REPL keeps working; you only lose the old history.

| Flag / env var | Effect |
|---|---|
| `--no-history` | Skip loading and saving the history file. In-session arrow-up still works; nothing crosses session boundaries. |
| `ROBOTCODE_REPL_NO_HISTORY=1` | Same as `--no-history`, handy when the REPL is launched by a wrapper script. |
| `ROBOTCODE_REPL_HISTORY_SIZE=N` | Cap the history at N entries (default: 10000). Each new entry that would push the file past the cap evicts the oldest, so the file stays bounded as you keep using the REPL. |

`--no-history` is useful for AI-agent invocations, quick spike sessions, or working with secrets you don't want sitting on disk.

### Tab completion

Tab understands Robot's cell-separator semantics (2+ spaces or a tab) and its case-/whitespace-/underscore-insensitive name resolution. The candidates come from the live session, so completions reflect exactly what the REPL would resolve at that point.

| Where you press Tab | What you get |
|---|---|
| At the start of a cell | Keyword names from every loaded library and imported resource |
| Inside `${...}` / `@{...}` / `&{...}` | Variables from the live suite scope |
| Inside `%{...}` | Environment variables from the process environment |
| After `Import Library    ` | Library names — installed modules (`Coll<Tab>` → `Collections`), dotted module paths (`robot.libraries.Coll<Tab>`), filesystem paths (`./libs/My<Tab>` → `./libs/MyLib.py`) |
| After `Import Resource    ` | `.robot` / `.resource` files on disk |
| After `Import Variables    ` | `.py` / `.yaml` / `.yml` / `.json` variable files, plus discoverable variables modules |
| After `<keyword>    <arg>=` (RF 7+) | Literal values declared on the argument's type — e.g. for a library keyword `my_kw(level: Literal['DEBUG', 'INFO', 'WARN'])`, typing `my_kw    level=<Tab>` shows the three options. Activation rules mirror Robot itself: the name before `=` must be a real positional-or-named / named-only argument of the keyword (or the keyword takes `**kwargs`). Otherwise the cell stays a literal positional value — same as Robot's own runtime behaviour. |

When the prefix is ambiguous the full candidate list appears on the first Tab press — no double-tap, no `Display all NNN possibilities? (y or n)` prompt.

### Multi-line blocks with auto-indent

When you open a Robot block construct (`FOR`, `WHILE`, `IF`, `TRY`, `GROUP`), the next continuation line (`... ` prompt) is automatically indented to the matching depth. Nested blocks stack — `FOR` inside `IF` inside `FOR` gets three levels. `END` closes the innermost block and the line after it pops one level of indent.

```
>>> FOR    ${i}    IN RANGE    2
...     Log To Console    ${i}      # cursor lands here, already indented
...     IF    ${i} == 1
...         Log    inner             # two levels deep now
...     END
... END
```

On the prompt-toolkit backend you get a real multi-line buffer instead of one prompt per line. Plain **Enter** is *smart*: it submits when your buffer has no open block, otherwise it inserts a newline + auto-indent so you stay inside the block. **Alt-Enter** (`Esc` then `Enter`) and **Ctrl-J** always insert a newline + auto-indent, even when the block is balanced — useful when you want to add one more statement before committing. You can also use `Cursor-Up` / `Cursor-Down` to navigate back into earlier lines of the same buffer and edit them.

Shift-Enter isn't bound by default: most terminals send the same byte (`\r`) for Shift-Enter as for plain Enter, so a binding would never fire portably. Use Alt-Enter or Ctrl-J — both work in every terminal.

The plain backend falls back to one prompt per line; the auto-indent still works as a prefill on the next `... ` prompt.

### What the prompt-toolkit backend adds

Beyond the basic `plain` prompt, the default backend gives you several extra capabilities:

- **Live candidate popup** — completions appear *as you type*, in an inline menu under the cursor, with arrow-keys to pick and Enter to accept. No Tab needed (though Tab still works).
- **Fish-style auto-suggest** — as you type, the rest of the line you typed last time (matching the same prefix) appears greyed-out behind the cursor. Right-arrow accepts it.
- **Bracket auto-match**, multi-line cursor movement (up/down inside an open block), `Ctrl-R` reverse search with a dedicated UI.
- **Persistent history** — see *History across sessions* above. The plain backend has none.

The completion popup stays responsive even when there are hundreds of importable modules installed.

#### Argument signature in the bottom row

When the cursor sits in an argument cell of a recognised keyword, a single status line appears at the bottom of the prompt with the keyword's signature and the active argument highlighted:

```
 Log    message · level='INFO' · html=False · console=False · repr=False
                  ─────────
```

Highlight follows `name=…` syntax: typing `Log    msg    html=True` lights up `html`, not the positional cell at that index. Falls back to the positional cell index when the name before `=` isn't a real argument of the keyword.

The row only shows up when there's a signature to render — outside of an argument cell (or for an unrecognised keyword) the prompt has no toolbar at all.

#### Documentation hints in the popup

Each candidate in the completion popup shows a short context string to its right, so you know *what* a candidate is before picking it:

- **Keywords**: the first line of the keyword's docstring (`Log a message with the given level` next to `Log`, etc.).
- **Library / resource / variables imports**: the kind of import — a built-in library, a third-party library, a `.resource` file, or a Python file discovered on disk.
- **Variables (`${…}` / `@{…}` / `&{…}`)**: a truncated preview of the current value in the live suite scope — handy when you're trying to remember whether `${COUNT}` is `42` or `"42"`.
- **Environment variables (`%{…}`)**: a truncated preview of the environment variable's value.

#### Syntax highlighting

Coloured Robot syntax is on by default on the prompt-toolkit backend — keywords, variables, assigns, comments, block constructs (`FOR`, `IF`, `END`, …) and BDD prefixes (`Given`, `When`, `Then`, … plus localised variants from RF 6+ languages) each get their own colour. Variables decompose to the part level: the sigil and braces, the name, type hints (`${age: int}`), default values (`%{HOME=default}`), subscripts (`${dict}[key]`), nested variables (`${${inner}}`), and inline-Python expressions (`${{expr}}`) all render distinctly.

Colours match those used by RobotCode's VS Code extension, so the REPL prompt and the editor share a consistent palette.

### Interactive shortcuts

Available on both backends:

- **`${_}` — last result** — like Python's interactive shell. After every keyword call the return value is mirrored into the Robot variable `${_}`, so it always reflects the most recent keyword — including keywords that return `None` (e.g. `Log` itself), which set `${_}` to `None`. Use it directly in the next argument: `Evaluate    1 + 2` → `Log    ${_}` prints `3`. It's seeded to `None` at startup, so `${_}` resolves even before the first keyword runs.

`Ctrl-R` reverse-history search and the argument-signature toolbar are prompt-toolkit-only — see *History across sessions* and *Argument signature in the bottom row* above.

### REPL meta-commands

Dot-prefixed commands (lines that start with `.<word>`) are handled by the REPL itself — they aren't keyword calls, test steps, or log entries. Robot syntax never starts with a dot, so there's no clash with real Robot lines.

| Command | Effect |
| ----- | ------ |
| `.help [cmd]` | Without an argument: list all dot-commands. With an argument: detailed help (usage, flags, examples) for that command — e.g. `.help save`. Opens in the doc viewer (see below). |
| `.imports` | Show loaded libraries and resource files with their source path and keyword count. |
| `.vars [--user]` | Variables in the current scope, name + truncated `repr` of the value. `--user` filters out Robot's internal variables (`${OUTPUT_DIR}`, `${SUITE_NAME}`, …). |
| `.kw [name-or-text]` | Keyword documentation in the doc viewer — signature, argument table (types + defaults), tags, docstring body. Same renderer the editor's hover uses. Bare `.kw` lists all loaded keywords; with non-matching text it lists keywords whose name contains it. |
| `.doc <name>` | Full library or resource documentation in the doc viewer — version + scope, introduction (with the auto-linked Table of Contents), every keyword with its own signature + arguments + body. Loads the documentation on demand even when the library isn't currently imported. |
| `.history [N]` | Show the last N entries (default 20), numbered. Available on the prompt-toolkit backend; plain backend has no history. |
| `.history clear` | Truncate the in-memory history and the persistent history file. |
| `.history del <N>` | Drop the single entry at index N from both. |
| `.cwd` | Print the current working directory (where relative paths in imports resolve from). |
| `.clear` | Erase the screen. |
| `.save [-a] [-t NAME] <file>` | Export the session as a runnable `.robot` file (see below). |
| `.exit` / `.quit` | Leave the REPL — equivalent to `Ctrl-D` on an empty prompt. |

`.kw` and `.doc` show the same documentation the editor displays on hover — full per-keyword pages with signature, argument table (types + defaults), tags, and docstring body. It's rendered as styled Markdown, so headings, lists, code blocks, tables, and inline emphasis show up formatted in any modern terminal.

#### The doc viewer

`.help`, `.kw`, `.doc` (and `F1`, which is the keyboard shortcut for `.help`) open the rendered output in a fullscreen viewer (like `less`, `man`, or `vim`). Your prompt and scrollback are untouched: when you close the viewer the terminal snaps back to exactly where you were.

| Key | Effect |
| --- | ------ |
| `j` / `↓` / Mouse wheel down | Scroll one line down |
| `k` / `↑` / Mouse wheel up | Scroll one line up |
| `PgDn` / `Ctrl-D` / `Space` | Scroll one page down |
| `PgUp` / `Ctrl-U` / `b` | Scroll one page up |
| `g` / `Home` | Jump to top |
| `G` / `End` | Jump to bottom |
| `/` | Open search input |
| `n` / `N` | Next / previous search match |
| `Tab` / `Shift-Tab` | Cycle through links in the current viewport |
| `f` / `Enter` (on a focused link), mouse click | Follow link — `#anchor` scrolls to the section, `http(s)://` opens in your browser |
| `[` / `]` | Browser-style back / forward through anchor follows |
| `Shift` + drag | Native terminal text selection (mouse capture is suspended while Shift is held) |
| `q` / `Esc` / `Enter` (with no link focused) | Close the viewer |

Search is case-insensitive substring. The current match is highlighted in reverse; `n`/`N` walk through all matches and scroll them into view. Link cycling skips back to the user's current scroll position if you've scrolled away, so `Tab` always lands on something you can see.

On the plain backend the doc-display commands still work — they print the rendered markdown through the pager with no colour, no fullscreen overlay. Useful in AI-agent sessions and headless environments where a fullscreen overlay would get in the way.

### Saving a session as a runnable `.robot` file

`.save scratch.robot` writes the inputs you typed (the ones that round-tripped through Robot's parser without errors) to a `.robot` file you can re-run with `robot scratch.robot`:

```
robotcode repl
>>> Import Library    Collections
>>> ${d}=    Create Dictionary    a=1    b=2
>>> Log    ${d}[a]
1
>>> .save scratch.robot
Wrote scratch.robot (3 entries)
>>> .exit
$ robot scratch.robot
```

The exporter does two things automatically:

- **Hoists imports.** `Import Library / Resource / Variables` calls in the session move to a `*** Settings ***` section as `Library / Resource / Variables    <name>`.
- **Wraps the body** in a single `*** Test Cases ***` block named `REPL Session <ISO-timestamp>`. Override the name with `-t MyTest`.

`-a` appends to an existing file instead of overwriting, so you can build a test suite incrementally across multiple REPL sessions.

Failed entries — anything Robot's parser rejected — are silently skipped, so the exported file always parses cleanly. One caveat: REPL-only variables such as `${_}` parse fine but don't exist in a standalone `robot` run, so a session that relied on them may need a small edit before the exported file runs on its own.

## What syntax the REPL accepts

The REPL treats each input as a **test-case body** — the lines you'd write inside `*** Test Cases ***`. So you can use:

- keyword calls with positional and named arguments
- variable assignment (`${x}=    Set Variable    42`) and references (`Log    ${x}`)
- multi-line control structures (`FOR`, `WHILE`, `IF` / `ELSE IF` / `ELSE`, `TRY` / `EXCEPT` / `FINALLY`, `GROUP`)
- inline `VAR    ${name}    value    scope=GLOBAL` statements
- `Import Library    LibraryName    arg1    arg2` to add libraries during a session
- `Import Resource    path/to/resource.robot` to bring user keywords into scope

What you **can't** type at the prompt:

- `*** Settings ***` / `*** Test Cases ***` / `*** Keywords ***` headers — the REPL is already inside a test body. Use `Import Library` / `Import Resource` instead of a `Settings` section, and put reusable keywords in a `.resource` file that you import.
- Defining new user keywords inline — same reason. Put them in a `.resource` file and import it.
- `*** Test Cases ***`-level metadata (`[Tags]`, `[Setup]`, `[Teardown]`, …) — the REPL session is one synthetic test; per-test metadata doesn't apply.

## State persists across lines

Variables, library imports, and the suite's variable scope all carry over from one prompt line to the next. So this works:

```
>>> ${greeting}=    Set Variable    Hello
>>> Log To Console    ${greeting}, world!
Hello, world!
>>> Import Library    Collections
>>> ${items}=    Create List    apple    banana    cherry
>>> Log To Console    ${items}
['apple', 'banana', 'cherry']
```

Variables behave the way they would inside a single test case.

## Loading libraries and resources

`BuiltIn` is the only library available out of the box (same as a normal Robot run). Everything else — `Collections`, `OperatingSystem`, `SeleniumLibrary`, your own libraries — needs an explicit import:

```
>>> Import Library    SeleniumLibrary
>>> Import Library    OperatingSystem
>>> Import Resource   ./resources/common.resource
```

If your libraries live in a directory that isn't on `sys.path`, add it with `-P` at startup:

```bash
robotcode repl -P ./libs -P ./vendor/python-libs
```

`-P` accepts the same `PATH` strings as `robot --pythonpath`.

> **Heads-up for Robot Framework < 7.4.** Bare relative paths in the BuiltIn import keywords `Import Resource` / `Import Library` / `Import Variables` (e.g. `Import Resource    foo/my.resource`) only resolve against the directory of the importing file starting with RF 7.4. On older RF versions these keywords look the path up via the module search path only, so a bare relative form will fail with `Resource file '…' does not exist.` On those versions, either prefix the path with `${CURDIR}/` (e.g. `Import Resource    ${CURDIR}/foo/my.resource`) or put the directory on the module search path. On RF 7.4+ the bare form just works.

## Pre-seeding variables

Variables can be set up before the prompt opens:

| Flag | Effect |
|---|---|
| `-v NAME:VALUE` | Equivalent to `robot --variable NAME:VALUE`. Repeatable. |
| `-V PATH` | Equivalent to `robot --variablefile PATH`. Loads `.py`, `.yaml`, or `.json` files. Repeatable. |

```bash
robotcode repl -v BASE_URL:https://staging.example.com -V ./creds.yaml
```

Once inside, the variables are accessible like any other:

```
>>> Log To Console    ${BASE_URL}
https://staging.example.com
```

You can also define variables inline via the `VAR` statement (RF 7+) or classic assignment.

## Running REPL scripts

Pass one or more **REPL scripts** to execute their content before the prompt. Each is read as a **test-case body** — the same syntax as the prompt itself: just keyword calls and control structures, one entry per line. These scripts conventionally use the `.robotrepl` (or `.robotscript`) extension, which the RobotCode VS Code extension highlights as REPL input.

> **These are REPL scripts, not full `.robot` suites.** Because the content runs as the body of a single implicit test, section headers like `*** Settings ***` or `*** Test Cases ***` are **not** allowed — a file containing them fails with `No keyword with name '*** Settings ***' found`. Import libraries and resources from inside the body with the `Import Library` / `Import Resource` keywords instead of a Settings section.

```bash
robotcode repl setup.robotrepl                  # execute, then exit
robotcode repl setup.robotrepl more.robotrepl   # multiple files, in order, then exit
robotcode repl --inspect setup.robotrepl        # execute, then drop into the prompt
```

With `--inspect`, the file runs the same way but, instead of exiting, leaves you at `>>>` with everything it set up still in scope — variables, plus any libraries or resources imported via `Import Library` / `Import Resource`. Handy for inspecting the state a long setup sequence produced without rerunning it each time.

## Capturing the session as a Robot run

By default, `repl` runs everything in-process and discards the report. The standard `robot`-style output flags work here too, with the same names:

| Flag | Effect |
|---|---|
| `-d, --outputdir DIR` | Directory for any output files. |
| `-o, --output FILE` | Write `output.xml`. |
| `-l, --log FILE` | Write `log.html`. |
| `-r, --report FILE` | Write `report.html`. |
| `-x, --xunit FILE` | Write a JUnit-style `xunit.xml`. |

```bash
robotcode repl -d ./repl-output -o output.xml -l log.html
```

After the session ends (you press Enter on an empty prompt or `EOF` arrives), the output files are written and you can feed them right back to `robotcode results`:

```bash
robotcode repl -d ./tmp -o output.xml
# … type a few keyword calls …
robotcode results log -o ./tmp/output.xml
```

Useful when you're prototyping a sequence of keywords and want to attach the resulting `log.html` to a bug report or an issue comment.

## `--source` for working-directory context

```bash
robotcode repl --source ./tests/login_spike.robot
```

`--source FILE` does **one** thing: it uses the parent directory of `FILE` as the REPL session's working directory. Relative paths in `Import Resource`, `Import Library`, file-based variables, etc. then resolve against that directory — handy when you're prototyping a snippet that will eventually live in a real test file and want the import paths to behave the same way.

The file itself is never read or written, so the path doesn't have to exist. If you only care about the directory, point at any (real or imagined) filename inside it:

```bash
robotcode repl --source ./tests/_.robot
```

## Tracing executed keywords

```bash
robotcode repl --show-keywords
```

`-k / --show-keywords` prints a `KEYWORD <Library>.<Name>  arg1  arg2` line for every keyword the REPL dispatches, before the keyword's own output. Useful when you suspect the wrong keyword is being resolved (e.g. a name collision between two libraries, or a user keyword shadowing a library keyword):

```
>>> Log To Console    hi
KEYWORD BuiltIn.Log To Console  hi
hi
```

## Debugging

`robotcode repl` is a command-line debugger as well as a shell. There are two ways in:

- **`robotcode robot-debug`** (alias `run-debug`) runs a real `.robot` suite through the normal runner with the debugger attached. It takes the same options and arguments as [`robotcode robot`](cli.md#robot) — paths, `--variable`, `--include`, profiles, … — plus the trigger flags below.
- **`robotcode repl`** (the interactive shell) has the *same* debugger attached: a breakpoint that matches a keyword you run at the prompt drops you into the debug prompt too.

The debugger sees every keyword and control-structure (FOR / IF / TRY / WHILE / …) start and end, on every supported Robot Framework version (5.0 – 7.x).

### Setting breakpoints

There are several ways to make a run pause; they combine freely.

| Trigger | How |
| --- | --- |
| **Line breakpoint** | `--break path/to/test.robot:42` — pause when execution reaches that line. Repeatable. |
| **Keyword breakpoint** | `--break "Open Browser"` — pause whenever a keyword with that name is about to run. Repeatable. |
| **Embedded `Breakpoint` keyword** | Add `Breakpoint` as a step in your `.robot` / `.resource` (after `Library    robotcode.repl.Repl`). It's a no-op when run normally and a hard breakpoint under the debugger — no flag needed. |
| **Stop on entry** | `--stop-on-entry` (`robot-debug` only) — pause at the very first keyword. |
| **Uncaught exception** | **On by default** — pause at an uncaught failing keyword (not caught by `TRY`/`EXCEPT` or `Run Keyword And …`), *before* the failure unwinds. Turn off with `--no-break-on-exception`. |
| **Every exception** | `--break-on-all-exceptions` — pause at *every* failing keyword, even ones caught by `TRY`/`EXCEPT` or `Run Keyword And …`. |
| **Failing test / suite** | `--break-on-failed-test` / `--break-on-failed-suite` — pause at the end of a failing test / suite. |

The exception breakpoints are armed in both `repl` and `robot-debug`; each is toggleable at runtime with `.catch` (see [Exception breakpoints](#exception-breakpoints) below).

```bash
# A run pauses at the first uncaught failure out of the box
robotcode robot-debug tests/

# Add line + keyword breakpoints
robotcode robot-debug --break login.robot:42 --break "Submit Login" tests/

# Also pause at failing tests; don't pause on uncaught failures
robotcode robot-debug --break-on-failed-test --no-break-on-exception tests/
```

You can also add and remove breakpoints from the debug prompt at runtime with `.break` / `.tbreak` / `.delete` / `.disable` (see below).

> **Plain backend for non-interactive runs.** On an interactive terminal the debug prompt gives you completion, history, and highlighting at the stop. When you feed it from a pipe, a script, or CI, the default `auto` backend falls back automatically to a plain prompt (or pass `--plain` explicitly). See [Picking a specific input backend](#picking-a-specific-input-backend).

### At a stop

When the run pauses, the debugger prints a one-line banner and opens a prompt:

```
* breakpoint  Submit Login  (login.robot:42)
(rdb)
```

The banner is `* <reason>  <keyword>  (<file>:<line>)`, where reason is `breakpoint`, `step`, `entry`, `pause`, or `exception`. At the `(rdb)` prompt you have the full debug command set (below) **plus** every shell command (`.kw`, `.doc`, `.vars`, …), and you can run any keyword in the paused context — its result is echoed and any variable it assigns stays in scope, exactly like at the shell prompt.

`robot-debug` produces the **same console output as `robotcode robot`** — the run is fully visible, and continuing or stepping shows execution proceeding. The debug prompt is simply interleaved with Robot's live console at each stop; when a test happens to finish right at a prompt its `| PASS |` marker lands next to the prompt, which is cosmetic. (Use `.detach` at the prompt to let the rest of the run finish and print normally.)

### Debug commands

The debugger commands follow **pdb**: the same names, the same single-letter shortcuts, the same semantics. Each command has one canonical long name and (where pdb has one) one short letter; long names also accept any unambiguous prefix (`.bre` → `.break`). At the *shell* prompt, where there is no active stop, the navigation/resume commands simply report `Not at a breakpoint.`

**Stepping and resuming**

| Command | pdb | Effect |
| --- | --- | --- |
| `.continue` / `.c` | `c` | Resume until the next breakpoint, stop, or the end of the run. |
| `.step` / `.s` | `s` | Step into: stop at the next keyword, descending into calls. |
| `.next` / `.n` | `n` | Step over: stop at the next keyword in the current frame. |
| `.return` / `.r` | `r` | Continue until the current keyword returns, then stop. |
| `.until` | `unt` | Continue until a *later* line in the current frame — past a loop's remaining iterations — or until the frame returns. |

**Stack and frames**

| Command | pdb | Effect |
| --- | --- | --- |
| `.where` / `.w` | `w` | Show the call stack — innermost frame is `#0`, `>` marks the selected one. |
| `.up` / `.u` | `u` | Select the calling (outer) frame. |
| `.down` / `.d` | `d` | Select the called (inner) frame. |
| `.frame N` / `.f N` | — | Select frame number N directly (`#0` is the innermost). |

**Inspecting**

| Command | pdb | Effect |
| --- | --- | --- |
| `.list` / `.l` | `l` | Show the source at the current stop. On prompt-toolkit: the whole file in the scrollable viewer, scrolled to the current line (marked `->`). On the plain backend: a ±5-line inline window. |
| `.source <kw>` | `source` | Show a keyword's source. On prompt-toolkit: the **whole file** in the scrollable viewer, opened at the definition line (marked `->`). On the plain backend: inline from the definition downward — 10 lines, or `.source <kw> <n>` for `n`. |
| `.print <expr>` / `.p` | `p` | Evaluate a variable or expression in the selected frame and print the result. |
| `.pprint <expr>` / `.pp` | `pp` | Same, but pretty-printed — readable for nested dicts / lists. |
| `.whatis <expr>` | `whatis` | Print the Python type of a variable or expression. |
| `.vars` / `.v` | `a` | Show the variables in scope (Local / Test / Suite / Global), name + value. `--user` skips Robot internals. |
| `.set ${x} <value>` | `!x=…` | Set a **scalar** variable in the selected frame's local scope (the value is variable-substituted, like `Set Variable`). List/dict variables (`@{…}`/`&{…}`) and item access (`${x}[0]`) aren't supported. |
| `.display <expr>` | `display` | Show `<expr>`'s value automatically at every following stop. Bare `.display` lists/shows the registered expressions. |
| `.undisplay <expr>` | `undisplay` | Stop displaying `<expr>`; bare `.undisplay` clears the list. |

You can also just type a keyword at the `(rdb)` prompt to run it in the paused context — pdb's `interact`, but native to Robot.

`.source` resolves keywords from imported libraries and resources. A keyword defined directly in the suite file currently being run is *not* resolvable by name; when you're stopped inside one, use `.list` to see its source at the current line.

**Breakpoints**

| Command | pdb | Effect |
| --- | --- | --- |
| `.break <loc>[, <cond>]` / `.b` | `b` | Add a breakpoint — `file:line` or a keyword name, optionally conditional (`.break Login, ${retries} > 3`). |
| `.tbreak <loc>[, <cond>]` | `tbreak` | Same, but one-shot: removed after it first stops. |
| `.breakpoints` / `.bp` | `b` (bare) | List the breakpoints, numbered, with their attributes and the active exception filters. |
| `.condition <n> <expr>` | `condition` | Set a condition on breakpoint `<n>` (bare `.condition <n>` clears it). |
| `.ignore <n> <count>` | `ignore` | Skip breakpoint `<n>`'s next `<count>` hits. |
| `.delete <n>` | `clear` | Remove breakpoint `<n>`; bare `.delete` removes all. |
| `.disable <n>` / `.enable <n>` | `disable` / `enable` | Turn breakpoint `<n>` off / on; bare form applies to all. |
| `.commands <n>` | `commands` | Attach debugger commands to breakpoint `<n>`, replayed at each hit (enter one per line, end with `end`; a leading `silent` suppresses the banner; a resuming command lets the run continue automatically). |

Breakpoints are referenced by the stable number shown in `.breakpoints`. A **condition** is evaluated in the stopped frame each time the breakpoint is reached; if the expression itself raises, the debugger stops anyway so the breakage is visible (pdb's behaviour). `.ignore` skips the next *N* triggering hits.

**Exception breakpoints**

| Command | Effect |
| --- | --- |
| `.catch uncaught` | Pause at uncaught keyword failures (same as `--break-on-exception`). |
| `.catch all` | Pause at *every* keyword failure, even ones caught by `TRY`/`EXCEPT` or `Run Keyword And …`. |
| `.catch test` / `.catch suite` | Pause at a failing test end / suite end. |
| `.catch off` | Clear all exception breakpoints. Bare `.catch` shows what's armed. |

The CLI flags set the *initial* filters — `--break-on-exception` (on by default) ↔ `.catch uncaught`, `--break-on-all-exceptions` ↔ `.catch all`, `--break-on-failed-test` ↔ `.catch test`, `--break-on-failed-suite` ↔ `.catch suite` — and `.catch` adjusts them at runtime.

**Ending the session**

| Command | pdb | Effect |
| --- | --- | --- |
| `.detach` | — | Stop debugging but let the run finish normally — clears all breakpoints and runs to the end. |
| `.abort` | `q` | Abort the run immediately and exit (no further keywords, no reports). |

At a stop, `.exit` / `.quit` (which leave the *shell*) would be ambiguous, so they point you at `.continue` / `.detach` / `.abort` instead of quitting.

### A debug session, end to end

```
$ robotcode robot-debug --break "Greet" hello.robot

* breakpoint  Greet  (hello.robot:11)
(rdb) .list
      6      Log    hello
      7
      8  *** Test Cases ***
      9  T
     10      Log    start
->   11      Greet
     12      Log    end
(rdb) .where
> #0  Greet  hello.robot:11
  #1  T      hello.robot:9
  #2  Hello  hello.robot
(rdb) .print ${name}
${name} = 'world'
(rdb) Log    debugging ${name}
[ INFO ] debugging world
=> None
(rdb) .continue
```

Typing a keyword at the prompt runs it in the paused context: its log output appears (`[ INFO ] …`) and the `=> <value>` line echoes the keyword's return value (`None` for `Log`).

### Relationship to the VS Code debugger

This is the **command-line** debugger. For graphical step-debugging inside the editor — breakpoints in the gutter, a Variables pane, the call-stack view — use the **RobotCode** VS Code extension's debugger, which speaks the Debug Adapter Protocol. Both pause Robot Framework runs; the CLI debugger is the terminal-native, scriptable counterpart.

## Recipes

```bash
# Explore a library's API live
robotcode repl
>>> Import Library    Browser
>>> ${cat}=    Get Library Instance    Browser
>>> Log    ${cat}
… inspect the instance, try keywords on it …

# Replicate the exact arguments a failing test passes to a keyword
robotcode repl -v USER:alice -v PASS:s3cr3t
>>> Import Resource    ./resources/login.resource
>>> Login With Credentials    ${USER}    ${PASS}

# Prototype a keyword sequence and capture a log.html for review
robotcode repl -d /tmp/probe -o output.xml -l log.html

# Debug a failing suite: pauses at the first uncaught failure out of the box
robotcode robot-debug tests/login.robot
# … at (rdb): .where, .vars, .print ${response}, .up, .continue …

# Stop at a keyword, drive the debug prompt from a script (plain backend)
printf '.where\n.vars\n.continue\n' \
  | robotcode robot-debug --plain --break "Submit Login" tests/

# CI smoke check — pipe a sequence through stdin, exit non-zero on failure
# bash / zsh
printf 'Run Keyword And Expect Error    *    Fail    sanity\n' \
  | robotcode repl

# Validate a YAML/Python variable file loads correctly
robotcode repl -V ./vars.yaml
>>> Log To Console    ${SOME_KEY_FROM_VARS}

# Run a REPL script then poke at the resulting state
robotcode repl --inspect ./scratch/setup_world.robotrepl
```

```powershell
# CI smoke check on Windows / PowerShell
'Run Keyword And Expect Error    *    Fail    sanity' | robotcode repl

# Multi-line input through a here-string
@'
${BASE_URL}=    Set Variable    https://staging.example.com
Log To Console    pinging ${BASE_URL}
'@ | robotcode repl
```

## What it isn't

- **Not a Python REPL.** It's keyword-driven, not expression-driven. Type Robot Framework syntax, not Python.
- **Not a *graphical* debugger.** `robot-debug` is a `pdb`-style *command-line* debugger (see [Debugging](#debugging)). For step-debugging inside the editor — gutter breakpoints, a Variables pane, the call-stack view — use the **RobotCode** VS Code extension's debugger.
- **Not a way to define new user keywords.** Those go in `.resource` files; the REPL imports them.
- **Not persistent.** Closing the prompt throws away the session unless you've passed `-o` / `-l` / `-r` / `-x` to capture artefacts.

For the per-flag reference of the base `repl` options see the auto-generated [CLI reference](cli.md#repl).
