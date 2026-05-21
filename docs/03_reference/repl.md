# Interactive Robot Framework with `robotcode repl`

Trying out a single Robot Framework keyword usually means more ceremony than the keyword call itself — write a `.robot` file with `*** Settings ***` and `*** Test Cases ***` headers, import the right library, run `robot`, open `log.html`, find your test, read the output. For a one-liner you just want to *try*, that's a lot of overhead, and the file lingers in the tree afterwards.

**`robotcode repl`** removes the ceremony. It's an interactive shell that runs Robot Framework syntax line by line through the same execution engine as `robotcode robot` — same library loading, same variable scoping, same keyword resolution — but with no `.robot` file, no boilerplate sections, and no output artefacts unless you ask for them. Type a keyword, press Enter, see the result. State persists across lines within a session, so you can import a library, build up a variable, then call a keyword on it, all without leaving the prompt.

Reach for it whenever "let me just *try* it" would be faster than writing a one-off test file — library exploration, keyword debugging, environment sanity checks, ad-hoc spikes.

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
- execute a `.robot`-style snippet from a file and either exit or drop into the prompt afterwards
- generate a `log.html` / `report.html` / `output.xml` from the interactive session, just like a normal `robot` run

This is intentionally **not** a replacement for writing real test files. It's the lightweight cousin: same engine, immediate feedback, no persistence unless you ask for it.

## Quick start

```bash
# Interactive prompt
robotcode repl

# Execute a snippet file, then exit
robotcode repl spike.robot

# Execute a snippet file, then drop into the prompt
robotcode repl --inspect spike.robot

# Pre-set variables for the whole session
robotcode repl -v BASE_URL:https://staging.example.com -v RETRIES:3

# Add a directory to the library search path
robotcode repl -P ./resources

# Capture a log.html / output.xml from the session
robotcode repl -d ./repl-output -o output.xml -l log.html
```

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

The prompt is a real line editor — arrow-keys for cursor movement, `Ctrl-R` for reverse history search, Tab for Robot-aware completion. On Unix and on Windows with Python 3.13+ this is wired up out of the box via Python's stdlib `readline`; on older Windows Pythons you only get plain `input()` unless you install `pyreadline3`.

### Picking a specific input backend

The REPL auto-picks the best available input backend on startup (`prompt_toolkit` → `readline` → bare `input()`). Pass `--backend` (or set `ROBOTCODE_REPL_BACKEND`) to force a specific one:

| Value | Effect |
| ----- | ------ |
| `auto` (default) | Run the fallback cascade. |
| `prompt-toolkit` | Use the prompt_toolkit backend. Requires the `[prompt-toolkit]` extra. |
| `readline` | Use the readline backend even when prompt_toolkit is installed. Useful for testing the readline code path or for users who prefer it. |
| `plain` | Bypass every editor layer and fall back to a bare `input()` prompt. |

Requesting a backend that isn't importable on the current Python aborts startup with a clear error and a `pip install` hint — there is no silent fallback, so the explicit choice is always honoured (or visibly refused).

#### Disabling all enhancements (AI agents, automation)

`--plain` (or `ROBOTCODE_REPL_PLAIN=1`) is a shorthand for `--backend=plain`. It bypasses every layer above and falls back to a bare `input()` prompt — no history, no completion, no candidate popup, no auto-suggest, no syntax highlighting. Use this for AI-agent invocations or automation pipelines where ANSI escape sequences and completion popups would corrupt stdin/stdout capture.

```bash
# AI-agent style: pipe input, capture clean output
ROBOTCODE_REPL_PLAIN=1 robotcode repl <<'EOF'
Log To Console    hello from agent
EOF
```

Combining `--plain` with a non-`plain` `--backend` value is rejected as a usage error; combining it with `--no-history` is fine (plain mode has no history file anyway).

### History across sessions

Every command you press Enter on is saved to a history file. Arrow-up recalls the previous line, `Ctrl-R` runs incremental reverse-search over the whole history — same keybindings as bash or Python's own shell.

Re-entering a line that's already in the history removes the older copy (fish-style), so arrow-up cycles through *unique* commands.

The history file lives in:

- `{project_root}/.robotcode_cache/repl_history` when the REPL is launched from inside a project (detected by `robot.toml` / `.robot.toml` / `pyproject.toml` / `.git` / `.hg`)
- the per-user cache directory otherwise — `~/.cache/robotcode/repl_history` on Linux, `~/Library/Caches/robotcode/repl_history` on macOS, `%LOCALAPPDATA%\robotcode\Cache\repl_history` on Windows
- `${ROBOTCODE_CACHE_DIR}/repl_history` if the env var is set — overrides both of the above

| Flag / env var | Effect |
|---|---|
| `--no-history` | Skip loading and saving the history file. In-session arrow-up still works; nothing crosses session boundaries. |
| `ROBOTCODE_REPL_NO_HISTORY=1` | Same as `--no-history`, handy when the REPL is launched by a wrapper script. |
| `ROBOTCODE_REPL_HISTORY_SIZE=N` | Cap the buffer at N entries (default: 1000). |

`--no-history` is useful for AI-agent invocations, quick spike sessions, or working with secrets you don't want sitting on disk.

### Tab completion

Tab understands Robot's cell-separator semantics (2+ spaces or a tab) and its case-/whitespace-/underscore-insensitive name resolution. The candidates come from the live execution context, so completions reflect exactly what the REPL would resolve at that point in the session.

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

With the `prompt-toolkit` extra installed (see below) you get a real multi-line buffer instead of one prompt per line. Plain **Enter** is *smart*: it submits when your buffer has no open block, otherwise it inserts a newline + auto-indent so you stay inside the block. **Alt-Enter** (`Esc` then `Enter`) and **Ctrl-J** always insert a newline + auto-indent, even when the block is balanced — useful when you want to add one more statement before committing. You can also use `Cursor-Up` / `Cursor-Down` to navigate back into earlier lines of the same buffer and edit them.

Shift-Enter isn't bound by default: most terminals send the same byte (`\r`) for Shift-Enter as for plain Enter, so a binding would never fire portably. Use Alt-Enter or Ctrl-J — both work in every terminal.

### A richer prompt with `prompt_toolkit`

Install the `prompt-toolkit` extra to swap the readline frontend for a `PromptSession`-driven one:

```bash
pip install 'robotcode-repl[prompt-toolkit]'
```

What you get on top of the readline behaviour:

- **Live candidate popup** — completions appear *as you type*, in an inline menu under the cursor, with arrow-keys to pick and Enter to accept. No Tab needed (though Tab still works). The verbose `Import Library  Foo` / `Import Library  Bar` row layout is replaced by just the labels.
- **Fish-style auto-suggest** — as you type, the rest of the line you typed last time (matching the same prefix) appears greyed-out behind the cursor. Right-arrow accepts it.
- **Bracket auto-match**, multi-line cursor movement (up/down inside an open block), `Ctrl-R` reverse search with a dedicated UI.

The completer runs in a background thread (`complete_in_thread=True`), and Robot's library / resource discovery is cached for the session, so the popup stays responsive even when there are hundreds of importable modules on `sys.path`.

History is shared with the readline backend — same plain-text file, so swapping between the two extras (or having neither) doesn't lose arrow-up recall.

#### Argument signature in the bottom row

When the cursor sits in an argument cell of a recognised keyword, a single status line appears at the bottom of the prompt with the keyword's signature and the active argument highlighted:

```
 Log    message · level='INFO' · html=False · console=False · repr=False
                  ─────────
```

Highlight follows `name=…` syntax: typing `Log    msg    html=True` lights up `html`, not the positional cell at that index. Falls back to the positional cell index when the name before `=` isn't a real argument of the keyword.

The row only shows up when there's a signature to render — outside of an argument cell (or for an unrecognised keyword) the prompt has no toolbar at all. Discover dot-commands and shortcuts through `.help` instead; `.cwd` prints the working directory on demand.

#### Documentation hints in the popup

Each candidate in the completion popup now shows a short context string to its right (prompt-toolkit's `display_meta`), so you know *what* a candidate is before picking it:

- **Keywords**: the first line of the keyword's docstring (`Log a message with the given level` next to `Log`, etc.). Sourced from `library_doc.keywords[name].short_doc` on RF 7+ and `.shortdoc` on RF 5/6.
- **Library / resource / variables imports**: the discovery kind — `MODULE_INTERNAL` for built-in libraries, `MODULE` for third-party ones, `RESOURCE` for `.resource` files, `FILE` for filesystem-discovered Python files.
- **Variables (`${…}` / `@{…}` / `&{…}`)**: `repr(value)[:40]` of the current value in the live suite scope — handy when you're trying to remember whether `${COUNT}` is `42` or `"42"`.
- **Environment variables (`%{…}`)**: `repr(os.environ[name])[:40]`.

#### Syntax highlighting

Coloured Robot syntax is automatically on when you install the `prompt-toolkit` extra — keywords, variables, assigns, comments, block constructs (`FOR`, `IF`, `END`, …) and BDD prefixes (`Given`, `When`, `Then`, … plus localised variants from RF 6+ languages) each get their own colour. Variables decompose to the part level: the sigil and braces, the name, type hints (`${age: int}`), default values (`%{HOME=default}`), subscripts (`${dict}[key]`), nested variables (`${${inner}}`), and inline-Python expressions (`${{expr}}`) all render distinctly.

The highlighter uses Robot Framework's own production tokenizer (`robot.api.get_tokens`) plus the `robotcode` semantic analyzer's variable decomposer — the same code path RobotCode's VS Code extension uses for semantic-token rendering. Colour assignments match the LSP semantic-token mapping, so the REPL prompt and the VS Code editor use a consistent palette.

No additional dependency: Robot is already required by `robotcode-repl`, and the variable decomposer ships with `robotcode-robot`.

### Interactive shortcuts

Across all backends (PlainBackend / Readline / prompt_toolkit, with the obvious caveat that Plain has no editor):

- **`${_}` — last result** — like Python's interactive shell. After every keyword call the return value is mirrored into the Robot variable `${_}`. Use it directly in the next argument: `Evaluate    1 + 2` → `Log    ${_}` prints `3`. Keywords that return `None` (e.g. `Log` itself) don't overwrite `${_}`, so the most recent meaningful value stays reachable across "noisy" interleaved calls.
- **Ctrl-R reverse-history search** — type a substring and press `Ctrl-R` to walk backwards through past entries. Enter accepts, Esc cancels. Works in both the readline and prompt_toolkit backends — we deliberately leave the binding to the framework's default so users don't lose a feature they expect from every modern REPL.
- **Argument signature in the bottom row** — only on the prompt_toolkit backend. When the cursor is in an argument cell of a recognised keyword, a row at the bottom shows the full signature with the active argument highlighted. Outside that context the row is hidden.

### REPL meta-commands

Dot-prefixed commands (lines that start with `.<word>`) are intercepted **before** Robot's parser sees them and run REPL-internal logic — no keyword call, no test step, no log entry. Robot syntax can't legitimately start with a dot, so the prefix is collision-free.

| Command | Effect |
| ----- | ------ |
| `.help [cmd]` | Without an argument: list all dot-commands. With an argument: print detailed help (usage, flags, examples) for that command — e.g. `.help save`. |
| `.imports` | Show loaded libraries and resource files with their source path and keyword count. |
| `.vars [--user]` | Variables in the current scope, name + truncated `repr` of the value. `--user` filters out Robot's internal variables (`${OUTPUT_DIR}`, `${SUITE_NAME}`, …). |
| `.kw <name>` | Rich-rendered Markdown documentation for the keyword: signature, tags, docstring, source path. |
| `.doc <name>` | Rich-rendered Markdown documentation for a library or resource: name, version, intro doc, list of contained keywords with one-line descriptions. Falls back to a fresh `get_library_doc()` load when the library isn't currently imported. |
| `.history [N]` | Show the last N entries (default 20), numbered. |
| `.history clear` | Truncate the in-memory history and the persistent history file. |
| `.history del <N>` | Drop the single entry at index N from both. |
| `.cwd` | Print the current working directory (where relative paths in imports resolve from). |
| `.clear` | Erase the screen. |
| `.save [-a] [-t NAME] <file>` | Export the session as a runnable `.robot` file (see below). |
| `.exit` / `.quit` | Leave the REPL — equivalent to `Ctrl-D` on an empty prompt. |

The `.kw` and `.doc` output goes through `rich.markdown.Markdown` (already a dependency of the `robotcode-plugin` package), so headings, lists, code blocks and inline emphasis render properly in any modern terminal. Robot's docstring format (the default for built-in libraries) is converted to Markdown via `MarkDownFormatter` first, so `*bold*`, `_italic_`, lists, tables and preformatted blocks all survive the round-trip.

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

- **Hoists imports.** `Import Library / Resource / Variables` calls in the session move to a `*** Settings ***` section as `Library / Resource / Variables    <name>` (so the resulting file is canonical Robot syntax, not literal REPL replays).
- **Wraps the body** in a single `*** Test Cases ***` block named `REPL Session <ISO-timestamp>`. Override the name with `-t MyTest`.

`-a` appends to an existing file instead of overwriting, so you can build a test suite incrementally across multiple REPL sessions.

Failed entries — anything Robot's parser rejected — are silently skipped, which is why the exported file is always runnable.

### libedit-backed Pythons

macOS' system Python and some Linux interpreters built via `python-build-standalone` (used by `uv`, `rye`, …) link `readline` against **libedit** instead of GNU readline. libedit silently ignores most of the bindings the REPL relies on, so you'd see Tab inserting a literal tab character and the verbose default completion display.

Install the `gnureadline` extra to switch to a real GNU readline that the REPL drives correctly:

```bash
pip install 'robotcode-repl[gnureadline]'
```

The package isn't published for Windows (where readline works differently and isn't needed) and is harmless to install on Pythons whose stdlib `readline` is already GNU-backed.

Both extras can be combined: `pip install 'robotcode-repl[prompt-toolkit,gnureadline]'` covers the case where you've installed prompt-toolkit but also want a clean fallback if you uninstall it later.

## What syntax the REPL accepts

The REPL treats each input as a **test case body** — the lines you'd write inside `*** Test Cases ***`. So you can use:

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

The session shares a single Robot Framework execution context. Variables behave the way they would inside a single test case.

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

## Running a `.robot` snippet file

Pass one or more **files** to execute their content before the prompt. The files are read as test-case bodies — same syntax constraints as the prompt itself (no `*** Settings ***` headers; just keyword lines and control structures).

```bash
robotcode repl smoke.robot                    # execute, then exit
robotcode repl smoke.robot setup.robot        # multiple files, in order, then exit
robotcode repl --inspect smoke.robot          # execute, then drop into the prompt
```

`--inspect` is the bridge between "run my snippet" and "let me poke at the result interactively". It runs the file the same way, but instead of exiting it leaves you at `>>>` with all the variables and imports the file set up still in scope.

This is useful for testing what `${RESULT}` looks like after a long sequence of setup keywords without rerunning everything every time.

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

# CI smoke check — pipe a sequence through stdin, exit non-zero on failure
# bash / zsh
printf 'Run Keyword And Expect Error    *    Fail    sanity\n' \
  | robotcode repl

# Validate a YAML/Python variable file loads correctly
robotcode repl -V ./vars.yaml
>>> Log To Console    ${SOME_KEY_FROM_VARS}

# Run a snippet file then poke at the resulting state
robotcode repl --inspect ./scratch/setup_world.robot
```

```powershell
# CI smoke check on Windows / PowerShell
'Run Keyword And Expect Error    *    Fail    sanity' | robotcode repl

# Multi-line snippet through a here-string
@'
${BASE_URL}=    Set Variable    https://staging.example.com
Log To Console    pinging ${BASE_URL}
'@ | robotcode repl
```

## What it isn't

- **Not a Python REPL.** It's keyword-driven, not expression-driven. Type Robot Framework syntax, not Python.
- **Not a debugger.** For line-by-line stepping through existing test files (with breakpoints, variable inspection, and call stacks), use the **RobotCode** VS Code extension's debugger.
- **Not a way to define new user keywords.** Those go in `.resource` files; the REPL imports them.
- **Not persistent.** Closing the prompt throws away the session unless you've passed `-o` / `-l` / `-r` / `-x` to capture artefacts.

For the exhaustive option list see the auto-generated [CLI reference](cli.md#repl).
