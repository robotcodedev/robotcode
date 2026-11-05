---
name: robotcode
description: >-
  Robot Framework and RobotCode CLI support: DO NOT answer Robot Framework or RPA
  questions from memory, by grepping `.robot`/`.resource` files, reading raw
  `output.xml`, or with web/generic tools — USE THIS SKILL FIRST; for such a
  project it is the source of truth (project-local `robotcode`, resolved against
  the real config). It covers test-automation AND RPA — `.robot`/`.resource`,
  `robot.toml`, `output.xml` — and tasks are as first-class as tests. Use it when
  the user writes or runs a suite (or one test or task), narrows a run by
  tag/suite/name; asks why a suite, test, or task failed or won't run, or to fix,
  debug, or step through it; asks what a keyword or library does or its args; asks
  which tests, tasks, suites, or tags exist; configures, reviews, or explains
  `robot.toml`, profiles, or a setting; statically analyzes the project (undefined
  keywords, wrong args, unused vars/keywords) before running; inspects a run or
  compares two; or tries a keyword or flow interactively — even when RobotCode
  isn't named.
license: Apache-2.0
compatibility: Runs from the project's Python environment with robotcode installed (Robot Framework 5.0+).
metadata:
  version: "2.8.0"
---

# robotcode CLI

`robotcode` wraps the Robot Framework toolchain and respects the project's `robot.toml` and profiles. Use it instead of `robot`, `rebot` or `libdoc`, from the project's Python environment: isolated runners such as `uvx robotcode ...` or `pipx run robotcode ...` don't see the libraries and other packages installed in it.

**It is probably already installed: try it before installing anything.** Get into the project's environment (activate its venv, use its runner such as `uv run robotcode …`, `hatch run`, `poetry run` or `pdm run`, or the interpreter the IDE is configured with) and run the command. Read [references/install.md](references/install.md) only when `robotcode` is genuinely missing there: `command -v robotcode` is empty *with that environment active*, or the first word after `robotcode` gives `No such command 'X'`, which means an extra is missing or robotcode is older than this skill. Don't retry other spellings.

## Pick the mode first

Decide what the user actually wants *before* reaching for a command — these intents have different entry points, and mixing them up is the most common mistake. Several can chain in one task (explore → author → run → inspect).

- **Use the REPL — explore, with no existing test in play** — *"try this keyword", "open a Robot shell", "go to … and check", "fetch …", "build this keyword step by step", "does this keyword/library work?", "so I can watch it drive the app".* Standalone interactive work. Prefer it over a throwaway `.robot` file: what worked at the prompt promotes into a test cheaply (`.save`), whereas a prematurely written test wastes effort and tears its browser/connection down at the run's end. [**Not for anything involving a real test case**](#a-real-test-case-the-debugger-not-the-repl). See [references/repl.md](references/repl.md). Run it with `robotcode repl`, or with `robotcode session start repl` if your shell tool can't keep a command running and write to its input.
- **Author tests or keywords** — *"write / create / add a test or suite".* Reuse what exists → prototype → write → `robotcode analyze code` before running → run only what you added. See [references/authoring.md](references/authoring.md).
- **Run a suite or tests** — *"run the tests", "execute the smoke suite", "run only tag X", "run just suite Y / this one test".* To run one test or suite, [select it by longname](#selecting-one-test-or-suite). See [Running tests](#running-tests--robotcode-robot).
- **Inspect or compare a finished run** — *"what failed?", "did it pass?", "why did X fail?", "did this regress?", "what changed since the last run?".* No re-run; try this **first** for "why did X fail?". See [references/results.md](references/results.md).
- **Debug a live run** — *"fix this test", "why does this test fail / won't it run?", "step through it", "watch / inspect this test as it runs", "break at line X", "what is `${response}` there?", "try this in the actual test/suite".* Pause the real run; inspect the live stack/variables and run keywords at the `(rdb)` prompt in the real context. Also the tightest loop while developing or fixing a test: a failure stops you live to prove a fix on the spot; then write that fix into the file and re-run, since running it at the prompt doesn't change the source. This, not the REPL, is how you experiment *inside* a real test or suite. See [references/debugging.md](references/debugging.md). Run it with `robotcode robot-debug`, or with `robotcode session start debug` if your shell tool can't keep a command running and write to its input.
- **Analyze / lint the code** — *"find issues", "check my robot code", "any undefined keywords / wrong arguments?", "are there unused keywords or variables?".* Static analysis, no run. See [references/analyze.md](references/analyze.md).
- **Inventory / understand the project** — *"what tests/tasks/tags/suites exist?", "which tests or tasks have tag X?", "how big is this?".* `robotcode discover`, not grep. See [Discovery](#discovery--whats-in-the-project).
- **Configure the project** — *"set up robot.toml", "add a CI profile", "configure variables/paths", "what's in effect under this profile?".* See [references/config.md](references/config.md).
- **Look up a keyword or library** — *"what does X do?", "what args does it take?", "which keywords does this resource have?".* `robotcode doc keywords` / `robotcode doc keyword`. See [Documentation lookup priority](#documentation-lookup-priority).

## Selecting one test or suite

**To run, debug or inspect one test, task or suite, select it by longname (`-bl "<longname>"`), never by a single `.robot` file.** This holds for `robot`, `robot-debug`, `session start debug`, `discover` and `results`. A single file becomes the top suite, so the parent suites' `__init__.robot` (setup/teardown, variables, tags, timeouts) never runs and it behaves unlike a real run; a file with several tests also runs them all. The same goes for a folder below the top one, which also changes the names: select it with `-bl "Tests.Sub"`.

Take the longname from `robotcode discover`. One from `robotcode results` holds only if that run had the same paths; otherwise the run says `contains no tests after model modifiers`. The top suite is named after `paths`, not after the project's folder (`paths = ["tests"]` gives `Tests`); names for `-s` and `-bl` come from `robotcode discover suites`.

Robot Framework's other selectors work too: `-i`, `-e`, `-s`, `-t`, with tag patterns such as `smokeANDcritical` or `ui_*`. `-ebl` excludes by longname, and `-btm "Issue:4409"` / `-ebtm` select by a test's own `[Metadata]` (RF 7.5+; `robotcode discover metadata --values` lists what is in use). **Robot Framework's own options go before a path:** `robotcode robot -i smoke tests/`.

## Running tests — `robotcode robot`

`robotcode robot [ROBOT_OPTIONS] [PATHS]` (alias `run`) runs tests through the active configuration; `robotcode rebot` reports over existing output.

```bash
robotcode robot
robotcode --profile ci robot -i smoke -e wip
robotcode robot -bl "Suite.Sub.Test Name"
robotcode robot --rerunfailed results/output.xml
```

Do not append paths or output options by default; `robot.toml` often provides them. Without `paths` there, pass the test folder, the same in every command. `--output` is relative to the output directory, while `-o`, `--rerunfailed` and `rebot` take paths from the project root; the run prints its `Output:`.

**Global options go before the subcommand:** `robotcode --profile ci robot tests/`, not `robotcode robot --profile ci tests/`. They are `-p, --profile <name>` (repeatable, `-p ci -p docker` merges, each name a glob), `-r, --root <dir>`, `-d, --dry`, and `--format {text|json|json_indent|toml}`. Default to text; use JSON only for a script, `jq` or a nested tree. `robot` and `rebot` keep Robot's own console output.

Runs can be long. Use the maximum timeout your tool supports or run in the background; wait for the process exit code. Do not watch `output.xml` for completion: it is written continuously during a run.

Robot returns the number of failed tests, capped at 250; inspect with `robotcode results summary`. Exit code `252` means the run didn't start (invalid data or options, such as an invalid `robot.toml`): read the error output, because `results summary` would show the previous run.

## Interpreting results

Use `robotcode results` to inspect a finished run. **Always read [references/results.md](references/results.md) before issuing any `robotcode results` command — do not guess flags from `--help` output alone.** For a run other than the last one, `-o <file>` goes after the subcommand: `robotcode results summary -o <file>`. To find out whether a value or an argument occurred in a run, use `robotcode results log --search <text>`: it shows only the tests where it appears, also as an argument of a keyword. A value that only passed through a variable isn't recorded unless it was logged.

**Do not read, grep, parse, or summarize raw `output.xml`** unless the user explicitly asks for raw XML. Real outputs can be hundreds of megabytes; `robotcode results` returns bounded summaries, listings, logs, stats, diffs, or JSON.

- `summary` — headline counts; add `--failed` for failing tests.
- `show` — one line per test with filters, caps, tags, sorting.
- `log` — execution tree in text; `--max-depth`, `--level` control detail.
- `stats` — aggregate by tag, suite, or status.
- `diff BASELINE [CURRENT]` — compare two runs.

Report results with counts first, then short failure reasons, then `log.html` / `report.html` paths for human follow-up. Do not dump JSON or XML into the response.

## Debugging a run — `robotcode robot-debug`

`robotcode robot-debug` (alias `run-debug`) runs a real suite through the same runner as `robotcode robot`, with its full option set, but pauses at breakpoints and opens a `pdb`-style prompt with the live call stack, per-frame variables, and the ability to run any keyword in the paused context. Reach for it over `results` when a recorded log isn't enough and you need the **live** state.

```bash
robotcode robot-debug -bl "Suite.Login Works"                         # pause at its first uncaught failure (the default)
robotcode robot-debug --break login.robot:42 -bl "Suite.Login Works"  # break at a line
robotcode robot-debug --break "Submit Login" tests/                   # keyword breakpoint across a suite
```

**Drive it step by step.** If your shell tool can keep a command running and write to its input, start it there and write one command at a time, reading the answer up to the prompt `(rdb) `. **If not, run it as a session:** `robotcode session start debug <options>` runs to the first stop and prints `Started session <ID>.` and the output up to that stop; then one `robotcode session send <ID> '<command>'` per step (`.where`, `.vars --user`, `.print ${x}`, a keyword, `.continue`), each chosen from what the last answer showed, and `robotcode session stop <ID>` at the end. Never start a bare `robot-debug` and wait for it to exit. End a stop with `.continue`, `.detach` or `.abort`. Breakpoints, debug commands and sessions are in [references/debugging.md](references/debugging.md#start-or-reuse-a-debug-session).

**A debug run replaces the output files of the last run.** If that run is still needed, add `--output NONE --log NONE --report NONE`.

### A real test case: the debugger, not the REPL

**A real test case is involved → the debugger, never the REPL.** Running, watching, stepping, or inspecting a `*** Test Cases ***` (or `*** Tasks ***`) entry live, not only when it fails, is the debugger: it pauses the real run with the suite's setup, variables, imports, and `__init__.robot` all live, and you run keywords at the `(rdb)` stop. The REPL has **no test**: it runs only the keywords you type, in a different context, so "trying the test in the REPL" runs a misleading copy. "Interactive" alone does not mean REPL. **For "fix this test" or "why does it fail or not run?"**, read the recorded error first with `robotcode results` (`show --failed`, `log`), which often names the cause; if it doesn't, debug the actual test. Don't detour into external tools or an MCP probe first.

## REPL — `robotcode repl`

Use `robotcode repl` for interactive, step-by-step work inside the project configuration: trying out keywords and libraries, exploring the live application, developing a test or keyword one line at a time and saving it. **Can your shell tool keep a command running and write to its input,** as `write_stdin` or `send_to_terminal` do (a background process fed through a file or a FIFO doesn't count)? Then start `robotcode repl` there and write one input at a time, reading the answer up to the prompt `>>> `. **If not, run it as a session:** `robotcode session start repl` prints `Started session <ID>.`; each `robotcode session send <ID> '<input>'` runs one input and returns with its output and an exit code (`0` passed, `1` failed); `robotcode session stop <ID>` ends it. Never start a bare `robotcode repl` and wait for it to exit. REPL input is not a `.robot` file: no section headers, no indentation, and imports are keyword calls (`Import Library    Collections`). The full workflow is in [references/repl.md](references/repl.md).

## Discovery — what's in the project?

Use `robotcode discover` to inspect what the active profile would see without executing tests. **Do not answer "what tests, tasks, tags, or suites exist?" by reading or grepping `.robot` files**, also not for `*** Tasks ***` or `*** Test Cases ***`: what exists is decided at *resolution time*, by Robot's own rules, `robot.toml` and profiles, filters and pre-run modifiers, and `discover` performs that resolution. When the user constrains by tag, suite or profile, pass the matching filters. A folder outside `paths` goes last: `robotcode discover tasks tasks/`.

| Goal | Command |
| --- | --- |
| Environment and versions | `robotcode discover info` |
| Whole suite/test/task tree | `robotcode discover all` |
| Flat lists | `robotcode discover tests` (no tasks), `robotcode discover tasks` |
| Suites only | `robotcode discover suites` |
| Tags and what carries them | `robotcode discover tags --tests` / `--tasks` |
| Metadata and what carries it | `robotcode discover metadata --values --tests` / `--suites` |
| Files after `.gitignore` / `.robotignore` | `robotcode discover files` |

Add `--search TEXT` or `--search-regex PATTERN` to match names, paths, docs, tags, metadata, and test bodies.

## Static analysis — `analyze code`

`robotcode analyze code [PATHS]` checks the project statically, **without running anything**: undefined or duplicate keywords, unresolved variables, wrong argument counts, failing imports, deprecated syntax and, opt-in, unused keywords and variables. Without a path it checks the whole project, also outside `paths`. Its exit code is a **bitmask**, unlike `robot`'s. Filter with `--severity` / `--code`, not `grep`. **[references/analyze.md](references/analyze.md)** is the full reference.

## Documentation lookup priority

For Robot Framework libraries, project resources, and keyword signatures, always query project-local RobotCode documentation first:

1. `robotcode doc keywords <LibraryOrResource> [PATTERN]` — names, arguments, first paragraph
2. `robotcode doc keyword <LibraryOrResource> "<Keyword>"` — the full documentation
3. `robotcode repl` when behavior, locators or keyword sequencing must be verified against the project or application
4. Existing project tests and resources
5. External sources such as Context7 or web search only if `robotcode doc` cannot answer or the topic is outside the local Robot environment

`robotcode doc` uses the active environment, the installed library versions, variables, the Python path and project-local `.resource` files, which Context7 or web docs can't. Import arguments go as in Libdoc (`"MyLib::config.yaml::strict"`). `robotcode doc lib <Target>` prints the whole page. If a target can't be imported, fix it or its arguments rather than reading the library source.

For non-obvious RobotCode CLI details, fetch <https://robotcode.io/llms-full.txt> (complete) or <https://robotcode.io/llms.txt> (an index) instead of guessing.

## Configuration & profiles

| Goal | Command |
| --- | --- |
| List setting keys | `robotcode config info list` |
| Explain a setting | `robotcode config info desc <key>` |
| Config files used / detected root | `robotcode config files` / `robotcode config root` |
| The configuration as written, files merged, no profile applied | `robotcode config show` (`-s` shows each file's own) |
| **What is in effect**, profiles applied and expressions evaluated | `robotcode [-p <name>] profiles show` |
| List profiles | `robotcode profiles list` |
| Preview a profile's effect on a run | `robotcode -p <name> discover tests` |

**To explain, write, or edit a setting, read its documentation from `config info desc <key>`** instead of guessing, then confirm the result with `profiles show`. The full reference, with the loading order, inheritance, `precedence`, `enabled`, `extend-`, computed `{ expr }` / `{ if }` values and recipes, is [references/config.md](references/config.md).

## Tests or tasks? (RPA)

Robot Framework does acceptance testing and RPA with the same engine, files and commands; an RPA suite holds **`*** Tasks ***`** instead of `*** Test Cases ***`. **Everything in this skill applies to tasks: read "test" as "task" throughout**, except that `robotcode discover tests` lists no tasks. `--rpa` is only for `robot` and `rebot`, and **mixing test files and task files in one run is an error**. Details are in [references/authoring.md](references/authoring.md).

## Working with large projects

See [references/large-projects.md](references/large-projects.md). Default to filtering or aggregation before enumeration.

## Common workflows

For multi-step workflows, see [references/workflows.md](references/workflows.md): run tests and report failures; investigate a single failing test without rerunning first; lint only changed Robot files; analyze a project and manage suppressions; fix a whole failing run by cause, with `--rerunfailed` against a *pinned* output file.
