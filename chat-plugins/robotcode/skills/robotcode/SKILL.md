---
name: robotcode
description: >-
  Robot Framework and RobotCode help for test-automation projects — `.robot` and
  `.resource` files, `robot.toml`, `output.xml`. Use it whenever the user writes
  or runs a suite (or a single test or task), or narrows a run to a subset by tag,
  suite, or name; asks why a suite or test failed or won't run, or wants to fix,
  debug, or step through a failing one; asks what a keyword or library does or
  which arguments it takes; configures, reviews, troubleshoots, or explains the project's `robot.toml` /
  profile configuration or a single setting;
  statically analyzes the project — errors, undefined keywords, wrong arguments,
  and unused keywords/variables — before running; inspects a finished run (its
  `output.xml`) or compares two runs to see what changed before and after; or
  wants to try a keyword or flow interactively against the system under test. Use
  it even when the user doesn't name RobotCode or the REPL — and do NOT
  read a raw `output.xml` or grep `.robot` / `.resource` files yourself; load this
  skill first.
license: Apache-2.0
compatibility: Runs from the project's Python environment with robotcode installed (Robot Framework 5.0+).
metadata:
  version: "1.0.0"
---

# robotcode CLI

`robotcode` wraps the Robot Framework toolchain and respects the project's `robot.toml` / profile configuration. Use it instead of calling `robot`, `rebot`, or `libdoc` directly when the task should honor project paths, variables, profiles, and Python paths.

RobotCode must run from the project's Python environment. Do not use isolated runners such as `uvx robotcode ...` or `pipx run robotcode ...` for real projects; they cannot see the project's libraries, resources, and local Python modules.

## Pick the mode first

Decide what the user actually wants *before* reaching for a command — these intents have different entry points, and mixing them up is the most common mistake: especially writing a `.robot` test file when the user asked you to *do* something, or reaching for the REPL to fix/debug a real test when that's the **debugger's** job. Several can chain in one task (explore → author → run → inspect).

- **Use the REPL — explore, with no existing test in play** — *"try this keyword", "open a Robot shell", "go to … and check", "fetch …", "build this keyword step by step", "does this keyword/library work?", "so I can watch".* Standalone interactive work: poke at a keyword, drive the application, prototype a keyword/test line by line. **Not for fixing or debugging a real test or suite** — its behavior, its variables, or *why it fails*: the REPL runs in a *different context* (no suite setup, variables, or `__init__.robot`), so for that use **Debug** (run keywords at its `(rdb)` stop, in the real context). See [references/repl.md](references/repl.md).
- **Author tests or keywords** — *"write / create / add a test or suite".* See [references/authoring.md](references/authoring.md).
- **Run a suite or tests** — *"run the tests", "execute the smoke suite", "run only tag X", "run just suite Y / this one test".* A whole suite, or a subset filtered by tag/suite/name. **To run one test, select it by longname (`-bl`), not the `.robot` file** — the file may hold other tests, and a bare file skips the parent suites' `__init__.robot`. See [Running tests](#running-tests--robotcode-robot).
- **Inspect or compare a finished run** — *"what failed?", "did it pass?", "why did X fail?", "did this regress?", "what changed since the last run?".* No re-run; try this **first** for "why did X fail?". See [references/results.md](references/results.md).
- **Debug a live run** — *"fix this test", "why does this test fail / won't it run?", "step through it", "break at line X", "what is `${response}` there?", "try this in the actual test/suite".* Pause the real run; inspect the live stack/variables **and run keywords at the `(rdb)` prompt in the real context**. This — not the REPL — is how you experiment *inside* a real test or suite. See [references/debugging.md](references/debugging.md).
- **Analyze / lint the code** — *"find issues", "check my robot code", "any undefined keywords / wrong arguments?", "are there unused keywords or variables?".* Static analysis (errors, undefined keywords, wrong args, unresolved/unused variables), no run. See [references/analyze.md](references/analyze.md).
- **Inventory / understand the project** — *"what tests/tags/suites exist?", "which tests have tag X?", "how big is this?".* See [Discovery](#discovery--whats-in-the-project).
- **Configure the project** — *"set up robot.toml", "add a CI profile", "configure variables/paths", "what's my effective config?".* See [references/config.md](references/config.md).
- **Look up a keyword or library** — *"what does X do?", "what args does it take?".* See [Documentation lookup priority](#documentation-lookup-priority).

For **standalone exploration** ("watch me", "try …", "do it for me") prefer the REPL over writing a throwaway `.robot` file — a working session promotes into a test cheaply (`.save`), whereas a prematurely written test wastes effort, can't be watched, and tears its browser/connection down at the run's end. But the moment a **real test or suite** is in play — fixing it, stepping it, or asking *why it fails* — use the **debugger** (or read the recorded failure with [`results`](references/results.md) first), **not the REPL**, because only the debugger runs the test in its real context. In short: **the REPL is for trying things out; the debugger is for debugging a test.**

## Documentation lookup priority

For Robot Framework libraries, project resources, and keyword signatures, always query project-local RobotCode documentation first:

1. `robotcode libdoc <LibraryOrResource> list`
2. `robotcode libdoc <LibraryOrResource> show "<Keyword>"`
3. `robotcode repl` when behavior, locators, state, or keyword sequencing must be verified against the active project/application
4. Existing project tests and resources
5. External documentation sources such as Context7, official web docs, or web search only if `libdoc` cannot answer or the topic is outside the local Robot environment

This priority applies to Robot Framework, Browser Library, SeleniumLibrary, project-local `.resource` files, and any imported Robot library available in the project's environment. `libdoc` is the easiest and most accurate source because it uses the active Python environment, installed library versions, import arguments, Python path, and project-local resources. Do not start with Context7 or web documentation for Robot keyword arguments, keyword availability, or local resource documentation.

For non-obvious RobotCode CLI details that are not library/resource keyword documentation, fetch the RobotCode docs instead of guessing:

1. <https://robotcode.io/llms-full.txt> — complete RobotCode docs as LLM-friendly text.
2. <https://robotcode.io/llms.txt> — small navigation index for individual pages.

## Contents

- **Setup** — If robotcode is missing, read [references/install.md](references/install.md).
- **Cross-cutting** — Global options, output formats, profiles, tags, suites, tests.
- **Commands** — Discovery, static analysis, library info, REPL, runs, debugging, configuration.
- **Results** — Inspecting finished runs; full reference in [references/results.md](references/results.md). **Always read this file before issuing any `robotcode results` command — do not guess flags from `--help` output alone.**
- **Scale** — Large-project tactics in [references/large-projects.md](references/large-projects.md).
- **Recipes** — Multi-step workflows in [references/workflows.md](references/workflows.md).
- **REPL** — Interactive exploration and step-by-step development of tests and keywords in [references/repl.md](references/repl.md).
- **Debugging** — Pausing a live run at a breakpoint and inspecting the stack/variables (`robotcode robot-debug`, `repl --break`) in [references/debugging.md](references/debugging.md).
- **Authoring** — Writing/extending tests and reusable keywords (reuse → prototype → analyze → run) in [references/authoring.md](references/authoring.md).
- **Configuration** — `robot.toml` and profiles (loading order, inheritance, `extend-`, computed `{ expr }` / `{ if }` values, previewing a profile with `discover`) in [references/config.md](references/config.md).
- **Reference** — Gotchas that prevent common agent mistakes.

## If robotcode isn't installed (or a command is missing)

If `command -v robotcode` fails, or `robotcode <command>` reports `Error: No such command 'X'`, read [references/install.md](references/install.md) before installing anything.

Key rules:

- Install into the project environment, not an isolated tool runner.
- The base `robotcode` package is only the CLI core; commands live in extras such as `runner`, `analyze`, and `repl`.
- Ask before installing. Decide both install scope and extras in one user prompt.
- `Error: No such command 'X'` means the relevant extra is missing; do not retry alternate spellings.

## Global options worth knowing

Global options go before the subcommand:

```bash
robotcode --profile ci robot tests/      # profile applied
robotcode robot --profile ci tests/      # wrong: Robot sees --profile
```

Use these often:

- `-p, --profile <name>` — select a profile globally for `config`, `profiles`, `discover`, `analyze`, `results`, `libdoc`, and `robot`. **Repeatable** — pass it several times (`-p ci -p docker`) to merge profiles, and each `<name>` is a glob (`-p "ci*"` selects every matching profile). See [Configuration & profiles](#configuration--profiles) for merge order.
- `-r, --root <dir>` — override project-root detection only when needed.
- `--format {text|json|json-indent|toml}` — request structured output where supported (global; goes before the subcommand).
- `-d, --dry` — print what would happen.

## Output formats (`--format`)

Default to text output. It is designed to be readable directly and avoids unnecessary parsing.

Use JSON only when a script, `jq`, CI pipeline, editor integration, or nested tree projection needs structured data. `discover`, `config`, `profiles`, `results`, and `analyze code` all honor the global `--format json` (before the subcommand — e.g. `robotcode --format json analyze code`). `robot` / `rebot` run Robot Framework directly; the global `--format` does not change Robot's native console output.

## Concepts: profiles, tags, suites, tests

| Concept | What it is | User language | Flag |
| --- | --- | --- | --- |
| **Profile** | Named preset in `robot.toml` / `pyproject.toml` | "use the dev profile", "ci + docker profiles" | `--profile <name>` before the subcommand (repeatable; multiple merge) |
| **Tag** | `[Tags]` label on tests/tasks | "smoke tests", "slow ones" | `-i <tag>` / `-e <tag>` |
| **Suite** | `.robot` file or directory-derived suite | "Login suite" | `-s <name-pattern>` |
| **Test** | One `*** Test Cases ***` entry | "test called Login Works" | `-t <name-pattern>` or `-bl <longname>` |

When wording is ambiguous, verify instead of guessing:

```bash
robotcode profiles list
robotcode discover --no-diagnostics tags --no-tests
robotcode discover --no-diagnostics suites
```

## Robot Framework options work everywhere

`discover`, `robot`, `run`, and `rebot` accept Robot Framework options such as `-i`, `-e`, `-s`, `-t`, variables, listeners, and pre-run modifiers. Tag patterns use Robot Framework syntax (`smokeANDcritical`, `regressionNOTwip`, `ui_*`), not shell glob semantics.

RobotCode also adds exact longname filters:

- `-bl, --by-longname "Suite.Sub.Test"` — include exact longnames.
- `-ebl, --exclude-by-longname "Suite.Sub.Test"` — exclude exact longnames.

Use longname filters when you copied a full name from `discover` or `results show` and want to avoid glob ambiguity.

**To run or debug one specific test, select it by its longname (`-bl "<longname>"`) — never by passing the `.robot` file.** This holds for `robotcode robot` and `robotcode robot-debug` alike: the file usually contains other tests (a bare path runs them all), and pointing Robot at a single file makes it the top suite, so the parent suites' `__init__.robot` (suite setup/teardown, suite variables, tags) never runs and the test behaves unlike a real run. Get the longname from `discover` or `results`; to run a whole directory/suite, pass the directory (it loads its `__init__.robot`), not one file.

## Discovery — what's in the project?

Use `robotcode discover` to inspect what the active profile would see without executing tests.

**Do not answer "what tests / tags / suites exist?" by reading or grepping `.robot` files.** Which tests, tasks, suites, and tags actually exist is decided at *resolution time*, and a static file scan misses all of it:

- **Robot's own rules** decide which files even become suites vs. resources vs. ignored, how directories nest into suites, and how `__init__.robot` and naming shape the tree.
- **`robot.toml` / profiles** set the `paths` in scope, plus variables and name transforms that change suite and test names from what the file literally says.
- **`-i/-e/-s/-t` filters and pre-run modifiers** add, remove, rename, or retag tests *before* execution — so a literal `[Tags]` line in a file is not necessarily the effective tag set, and a `*** Test Cases ***` entry may not survive into the run at all.

`discover` performs that whole resolution with the project's installed Robot Framework and returns the real answer; grep cannot. (Same reasoning as preferring `libdoc` over reading library source.) When the user constrains by tag/suite/profile, pass the matching filters so the inventory reflects exactly that scope.

| Goal | Command |
| --- | --- |
| Environment and versions | `robotcode discover info` |
| Whole suite/test/task tree | `robotcode discover all` |
| Flat test or task lists | `robotcode discover tests`, `robotcode discover tasks` |
| Suites only | `robotcode discover suites` |
| Tags and tagged tests/tasks | `robotcode discover tags --tests` / `--tasks` |
| Source files Robot would parse | `robotcode discover files` |

Filter discovery like a run with Robot options (`-i`, `-e`, `-s`, `-t`, paths, variables). Add `--search TEXT` or `--search-regex PATTERN` to match names, paths, docs, tags, metadata, and test-body content. Use `--format json` when an integration needs the tree shape.

Parse-time diagnostics go to stderr. Suppress them with `discover --no-diagnostics <subcommand>` when you only need stdout data.

## Static analysis — `analyze code`

`robotcode analyze code [PATHS]` statically checks the project — undefined/duplicate keywords, unresolved variables, wrong argument counts, failing imports, deprecated syntax, and (opt-in) unused keywords/variables — **without running anything**. Output is one diagnostic per line (`path:line:col: [SEVERITY] CODE: message`, the tag a full word like `[ERROR]`) plus a summary; the exit code is a **bitmask** (`1` errors, `2` warnings, `4` infos, `8` hints — check bits, not values).

Filter with `--severity` / `--code` (not `grep`), find dead code with `--collect-unused`, suppress with `# robotcode: ignore[CODE]` or `-mi`, and gate CI by masking severities out of the exit code. **[references/analyze.md](references/analyze.md)** is the full reference — every flag, the diagnostic codes, the four suppression scopes, exit-code masking, machine-readable output, and the cache.

## Library & keyword information — `libdoc`, `repl`

Use `robotcode libdoc` for Robot Framework library, resource, and keyword documentation. Prefer it before generic documentation tools: it runs in the project environment, respects import arguments and Python paths, and can inspect project-local libraries and `.resource` files that external docs usually cannot see.

```bash
robotcode libdoc BuiltIn list
robotcode libdoc BuiltIn show "Should Be Equal"
robotcode libdoc resources/common.resource list
robotcode libdoc "MyLib::config.yaml::strict" show
```

Use `robotcode repl` for interactive, step-by-step work inside the project configuration — trying out keywords/libraries, exploring against the live application, or developing a test case or keyword one line at a time and saving it. (To debug a *real* failing test, reach for `robotcode robot-debug`, not the REPL — see [references/debugging.md](references/debugging.md).) REPL input is not a `.robot` file: no section headers, no indentation, and imports are keyword calls — `Import Library    Collections` (the Settings-style `Library    Collections` works too, as a REPL alias). No agent-specific flags are needed — RobotCode auto-detects when it runs under an AI agent and drops to a plain, capture-safe backend on its own. For the full step-by-step exploration → validate → promote-into-tests workflow (dot commands, `.save`, clean shutdown), see [references/repl.md](references/repl.md).

`robotcode repl-server` is for external clients that attach to a REPL session; use it only when such an integration is explicitly needed.

`robotcode testdoc` generates browsable test/suite documentation (the Robot Framework `testdoc` tool); reach for it only when the user explicitly wants a generated test-doc artefact, not for answering keyword questions.

## Running tests — `robotcode robot`

`robotcode robot [ROBOT_OPTIONS] [PATHS]` runs tests through the active RobotCode configuration. Aliases: `robotcode run` is equivalent; `robotcode rebot` reruns reporting over existing output.

```bash
robotcode robot
robotcode --profile ci robot -i smoke -e wip
robotcode robot -bl "Suite.Sub.Test Name"
robotcode robot --rerunfailed output.xml
```

**To run one specific test, select it by longname (`-bl "<longname>"`, copied from `discover` or `results`) — not by its file path.** Pointing Robot at a single `.robot` file makes that file the top suite, so the parent suites' `__init__.robot` — its Suite Setup/Teardown, suite variables, and the setup/tags/timeouts it applies to the tests below — never runs, and the test can behave differently than in a full run. Selecting by longname builds the whole suite tree from `robot.toml` paths, so that initialization applies. The same holds under the debugger (see *Debugging a run*).

Do not append paths or output options by default; `robot.toml` often already provides them. Add CLI paths only to narrow a one-off run (a *directory* is fine — it loads its `__init__.robot`; a single test file is not, see above).

Runs can be long. Use the maximum timeout your tool supports or run in the background; wait for the process exit code. Do not watch `output.xml` for completion because it is written continuously during a run.

Robot returns the number of failed tests, capped at 250. Non-zero means failures or execution errors; inspect with `robotcode results summary`.

## Debugging a run — `robotcode robot-debug`

`robotcode robot-debug` (alias `run-debug`) runs a real suite through the same runner as `robotcode robot` but pauses at breakpoints and opens a `pdb`-style debug prompt with the live call stack, per-frame variables, introspection of the loaded keywords / libraries / resources (with their docs and sources), and the ability to run any keyword in the paused context. It takes the **full `robotcode robot` option set** plus trigger flags; the same debugger is available in `robotcode repl`, where it starts **detached** (attach with `.debug on`, `--debugger-attached`, or by passing `--break …`) and breakpoints can be set up front with `--break` or interactively at the prompt with `.break`. Comes from the `repl` extra.

```bash
robotcode robot-debug -bl "Suite.Login Works"            # debug ONE known test by longname (preferred — never a bare .robot file)
robotcode robot-debug --break login.robot:42 -t "Login Works"  # break at a line, but scope the run to that test
robotcode robot-debug tests/                              # whole suite: pause at the first uncaught failure (default)
robotcode robot-debug --break "Submit Login" tests/      # keyword breakpoint across a suite
robotcode repl --break "Open Browser"                    # break at the REPL prompt
```

Target one test by its **longname** (`-bl`), never a bare `.robot` file — a file path skips the parent suites' `__init__.robot` (suite setup/variables), exactly as it would for `robotcode robot` above. Reach for it over `results` when a recorded log isn't enough and you need the **live** state at the failure point. **Like the REPL, it's an interactive prompt — step through it live**, command by command (stop → `.where` / `.vars` / `.print ${x}` → choose the next step), and end with `.continue` / `.detach` / `.abort`; never start it and block on its exit. (An agent that can't drive a terminal can pipe a fixed command sequence instead — a fallback, see the reference.) Full breakpoint triggers, debug commands, and the interactive workflow are in [references/debugging.md](references/debugging.md).

## Configuration & profiles

| Goal | Command |
| --- | --- |
| List setting keys | `robotcode config info list` |
| Explain a setting — read its docs (type, description, TOML example) | `robotcode config info desc <key>` |
| Config files used / detected root | `robotcode config files` / `robotcode config root` |
| Effective config — all files merged, incl. user-global defaults | `robotcode config show` (`-s` shows each setting's source; `--format json`) |
| Effective config for a profile | `robotcode --profile <name> config show` |
| List / show profiles | `robotcode profiles list` / `robotcode --profile <name> profiles show` |
| Preview a profile's effect on a run | `robotcode --profile <name> discover tests` |

**To explain, write, or edit a setting, read its documentation from `config info desc <key>`** (type, description, and a TOML example; wildcards `*tag*`, `rebot.*`) instead of guessing, then confirm the result with `config show`. **A setting's effective value can come from a profile** — when explaining what is actually in effect, account for the active profile(s): `robotcode --profile <name> config show` shows the value under that profile, and `config show -s` attributes each setting to the file or profile it came from. Profiles (`[profiles.<name>]`) layer onto the top-level settings; `--profile` is repeatable and globbed, and multiple profiles merge by `precedence`.

**Full reference — loading order, profile inheritance / `precedence` / `enabled` / `extend-`, recipes, and previewing a profile with `discover` — see [references/config.md](references/config.md).**

## Interpreting results

Use `robotcode results` to inspect a finished run. Do not read, grep, parse, or summarize raw `output.xml` unless the user explicitly asks for raw XML. Real Robot Framework outputs can be hundreds of megabytes; loading them into chat wastes context and is slower than asking RobotCode for the exact slice you need. `robotcode results` reads the same file server-side and returns bounded summaries, listings, logs, stats, diffs, or JSON. See [references/results.md](references/results.md) for full examples.

- `summary` — headline counts; add `--failed` for failing tests.
- `show` — one line per test with filters, caps, tags, sorting, and full-message options.
- `log` — execution tree in text; use `--max-depth`, `--level`, `--keyword-info`, and `--suite-info` to control detail.
- `stats` — aggregate by tag, suite, or status.
- `diff BASELINE [CURRENT]` — compare two runs.

Report results with counts first, then short failure reasons, then `log.html` / `report.html` paths for human follow-up. Do not dump JSON or XML into the response.

## Working with large projects

For large projects, see [references/large-projects.md](references/large-projects.md). Default to filtering or aggregation before enumeration. Prefer source-side filters, `discover tags` / `discover suites`, bounded `results` queries, and JSON projections with `jq` when the tree shape matters.

## Common workflows

For multi-step workflows, see [references/workflows.md](references/workflows.md):

- Run tests and report failures.
- Investigate a single failing test without rerunning first.
- Lint only changed Robot files.
- Analyze a project and manage suppressions / exit-code masks.
- Fix a whole failing run: triage by cause, debug one representative per cause, re-validate with `--rerunfailed` against a *pinned* output file (intermediate runs overwrite `output.xml`).

## Gotchas — agent-correction notes

- For Robot Framework library, resource, or keyword documentation, do not start with Context7, web search, or generic knowledge. Query project-local `robotcode libdoc` first; fall back to external documentation only when `libdoc` cannot answer or the topic is outside the local Robot environment.
- Global options belong before the subcommand; otherwise Robot Framework may reject them.
- `analyze code` and `robot` have different exit-code semantics.
- **JSON from `analyze code` → `robotcode --format json analyze code`** (global `--format`, *before* the subcommand — same as `results` / `discover`).
- `output.xml` is not a completion signal and should not be read directly for normal result analysis. After a run, use `robotcode results summary`, `show`, `log`, `stats`, or `diff` instead of loading a potentially huge XML file into context.
- `Error: No such command 'X'` means a RobotCode extra is missing.
- `uvx` / `pipx` isolates RobotCode from the project and gives wrong answers for real projects.
- `No profiles defined.` is an empty result, not an error.
- REPL syntax is not `.robot` file syntax.
- **Experimenting inside a real test or suite → `robotcode robot-debug`, not the REPL.** Run keywords at the `(rdb)` stop, where the suite's setup/variables/imports/`__init__.robot` are live; the REPL runs in a *different context* and misleads.
- **One test → select it by longname (`-bl`), never a bare `.robot` file — for `robotcode robot` and `robot-debug` alike.** The file holds other tests (all run) and skips the parent `__init__.robot` (setup/variables), so it behaves unlike a real run. Longname from `discover`/`results`; a whole suite → pass the *directory*.
- **"Fix this test" / "why does it fail or not run?"** → read the recorded error first with `robotcode results` (`show --failed`, `log`) — it often names the cause; if not, debug the *actual* test with `robotcode robot-debug -bl "<longname>"` (longname rule above). Don't reconstruct it in a REPL or detour into external tools / an MCP probe first — that's a *different context* and chases the wrong cause.
- **`robot-debug`/`repl` are interactive prompts** — step through live, end with `.continue`/`.detach`/`.abort`; never start one and block on its exit (it waits forever). At `(rdb)`, `Ctrl-C`/`Ctrl-D` *resume* — use `.abort` to stop. (Missing `repl` extra → `Error: No such command 'robot-debug'`.)
- "What tests/tags/suites exist?" — and any "which tests have tag X / are in suite Y" question — is answered with `robotcode discover`, never by reading or grepping `.robot` files. The effective set is resolved at runtime (paths, config, profiles, variables, pre-run modifiers); static sources don't show it.