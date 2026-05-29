---
name: robotcode
description: Robot Framework and RobotCode guidance for test automation projects — project structure, keywords, libraries, resources, variables, tags, suites, tests, profiles, configuration, execution, discovery, static analysis, result inspection, installation, CLI workflows, and editor tooling. Also covers the RobotCode REPL for interactive, step-by-step work — exploring a system under test or a keyword/library, and developing test cases and keywords one line at a time (use even when the user does not say "REPL"). Always use project-local `robotcode libdoc` first for library, resource, and keyword documentation — before Context7, web search, or generic knowledge — and fall back only when libdoc cannot answer. Inspect finished runs with `robotcode results` rather than loading large raw `output.xml` files.
license: Apache-2.0
---

# robotcode CLI

`robotcode` wraps the Robot Framework toolchain and respects the project's `robot.toml` / profile configuration. Use it instead of calling `robot`, `rebot`, or `libdoc` directly when the task should honor project paths, variables, profiles, and Python paths.

RobotCode must run from the project's Python environment. Do not use isolated runners such as `uvx robotcode ...` or `pipx run robotcode ...` for real projects; they cannot see the project's libraries, resources, and local Python modules.

## Pick the mode first

Decide what the user actually wants *before* reaching for a command — these intents have different entry points, and mixing them up is the most common mistake (especially writing a `.robot` test file when the user asked you to *do* something). Several can chain in one task (explore → author → run → inspect).

- **Explore / do it for me** — *"go to … and check", "fetch …", "try this keyword", "does X work?", "why does this fail?", "so I can watch".* A one-off, interactive task — **not** a test. Start a REPL and drive it live; when the user wants to watch, open the browser **non-headless** and keep the session open. **Do not write a `.robot` file** — see [references/repl.md](references/repl.md). Offer to turn it into a test *afterwards*, only if the user then asks.
- **Author tests or keywords** — *"write / create / add a test or suite".* Reuse existing keywords (`libdoc`) and conventions (`discover`), prototype uncertain steps in the REPL, write, then check with `analyze code` before running. See [references/authoring.md](references/authoring.md).
- **Run tests** — *"run the tests", "execute the smoke suite".* `robotcode robot` (see *Running tests*), then summarize via `results`.
- **Inspect a finished run** — *"what failed?", "did it pass?", "why did X fail?"* — `robotcode results` over the existing `output.xml`/`output.json`; no re-run needed (works on CI artifacts and a colleague's run too). See [references/results.md](references/results.md).
- **Analyze / lint the code** — *"find issues", "are there unused keywords?", "check my robot code".* `robotcode analyze code` (static analysis: missing keywords, wrong args, unresolved variables).
- **Inventory / understand the project** — *"what tests/tags/suites exist?", "which tests have tag X?", "how big is this?", "what's my effective config?"* — `robotcode discover` (tree without running) and `config` / `profiles`. **Never read or grep `.robot` files to answer this** — see *Discovery* below for why a file scan gives the wrong answer.
- **Look up a keyword or library** — *"what does X do?", "what args does it take?"* — `robotcode libdoc` (see *Documentation lookup priority* below).

When a request is action-oriented or "watch me", default to the REPL over writing a file: promoting a working REPL session into a test later is cheap (`.save`), but a prematurely written test wastes effort, can't be watched, and tears its browser/connection down at the end of the run.

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
- **Commands** — Discovery, static analysis, library info, REPL, runs, configuration.
- **Results** — Inspecting finished runs; full reference in [references/results.md](references/results.md). **Always read this file before issuing any `robotcode results` command — do not guess flags from `--help` output alone.**
- **Scale** — Large-project tactics in [references/large-projects.md](references/large-projects.md).
- **Recipes** — Multi-step workflows in [references/workflows.md](references/workflows.md).
- **REPL** — Interactive exploration and step-by-step development of tests and keywords in [references/repl.md](references/repl.md).
- **Authoring** — Writing/extending tests and reusable keywords (reuse → prototype → analyze → run) in [references/authoring.md](references/authoring.md).
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

- `-p, --profile <name>` — select a profile globally for `config`, `profiles`, `discover`, `analyze`, `results`, `libdoc`, and `robot`. **Repeatable** — pass it several times (`-p ci -p docker`) to merge profiles, and each `<name>` is a glob (`-p "ci*"` selects every matching profile). See *Configuration & profiles* for merge order.
- `-r, --root <dir>` — override project-root detection only when needed.
- `-f, --format {text|json|json_indent|toml}` — request structured output where supported.
- `-d, --dry` — print what would happen.

## Output formats (`-f`)

Default to text output. It is designed to be readable directly and avoids unnecessary parsing.

Use JSON only when a script, `jq`, CI pipeline, editor integration, or nested tree projection needs structured data. `discover`, `config`, `profiles`, and `results` support formats broadly. `analyze code` honors the global `-f json` and additionally has its own `--output-format {concise|json|json-indent|sarif|github|gitlab}` (plus `--output-file`) for CI artefacts. `robot` / `rebot` run Robot Framework directly; global `-f` does not change Robot's native console output.

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

Filter discovery like a run with Robot options (`-i`, `-e`, `-s`, `-t`, paths, variables). Add `--search TEXT` or `--search-regex PATTERN` to match names, paths, docs, tags, metadata, and test-body content. Use `-f json` when an integration needs the tree shape.

Parse-time diagnostics go to stderr. Suppress them with `discover --no-diagnostics <subcommand>` when you only need stdout data.

## Static analysis — `analyze code`

`robotcode analyze code [PATHS]` reports static issues such as missing keywords, wrong arguments, unresolved variables, duplicate imports, and unused items.

Useful flags:

- `-f, --filter '<glob>'` — limit files.
- `--severity {error|warn|info|hint}` — only report these severities (repeatable/comma-separated); filtered-out severities vanish from output, summary, and exit code. Prefer this over piping through `grep`.
- `--code <CODE>` — only report these diagnostic codes (e.g. `KeywordNotFound`); filters without changing severity.
- `-mi <CODE>` — ignore a diagnostic.
- `-me / -mw / -mI / -mh <CODE>` — reclassify severity.
- `-xm / -xe {error|warn|info|hint|all}` — mask severities from the exit code.
- `--collect-unused` — include unused keyword / variable diagnostics.
- `--output-format {concise|json|json-indent|sarif|github|gitlab}` + `--output-file <FILE>` — machine-readable / CI reports (SARIF, GitHub annotations, GitLab Code Quality).

The exit code is a bitmask: `1` errors, `2` warnings, `4` infos, `8` hints. Check bits, not exact values. Default text output is one diagnostic per line — `path:line:col: [SEVERITY] CODE: message` (the tag is the full word, e.g. `[ERROR]`, `[WARN]`) — plus a summary. For structured consumption use `-f json` or `--output-format`. For commit-focused linting and suppression workflows, see [references/workflows.md](references/workflows.md).

## Library & keyword information — `libdoc`, `repl`

Use `robotcode libdoc` for Robot Framework library, resource, and keyword documentation. Prefer it before generic documentation tools: it runs in the project environment, respects import arguments and Python paths, and can inspect project-local libraries and `.resource` files that external docs usually cannot see.

```bash
robotcode libdoc BuiltIn list
robotcode libdoc BuiltIn show "Should Be Equal"
robotcode libdoc resources/common.resource list
robotcode libdoc "MyLib::config.yaml::strict" show
```

Use `robotcode repl` for interactive, step-by-step work inside the project configuration — trying out keywords/libraries, debugging against the live application, or developing a test case or keyword one line at a time and saving it. REPL input is not a `.robot` file: no section headers, no indentation, and imports are BuiltIn keyword calls such as `Import Library    Collections`. No agent-specific flags are needed — RobotCode auto-detects when it runs under an AI agent and drops to a plain, capture-safe backend on its own. For the full step-by-step exploration → validate → promote-into-tests workflow (dot commands, `.save`, clean shutdown), see [references/repl.md](references/repl.md).

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

Do not append paths or output options by default; `robot.toml` often already provides them. Add CLI paths only to narrow a one-off run.

Runs can be long. Use the maximum timeout your tool supports or run in the background; wait for the process exit code. Do not watch `output.xml` for completion because it is written continuously during a run.

Robot returns the number of failed tests, capped at 250. Non-zero means failures or execution errors; inspect with `robotcode results summary`.

## Configuration & profiles

| Goal | Command |
| --- | --- |
| List setting keys | `robotcode config info list` |
| Describe one setting | `robotcode config info desc <key>` |
| Config files used | `robotcode config files` |
| Effective configuration | `robotcode config show` |
| Effective configuration for a profile | `robotcode --profile <name> config show` |
| Detected root | `robotcode config root` |
| List profiles | `robotcode profiles list` |
| Show a profile | `robotcode --profile <name> profiles show` |

Use `config show` for resolution questions. Use `config info` for supported keys and setting descriptions. Select profiles with the global `--profile <name>` option before the subcommand.

**Multiple profiles merge.** `--profile` is repeatable and each value is a glob against the defined profile names, so `-p ci -p "docker*"` selects and combines several profiles into one effective configuration:

- **Order / conflicts** — profiles are applied in ascending `precedence` (default `0`); on a conflicting scalar key, the higher-precedence profile wins.
- **Override vs. append** — within the merge, a plain key (e.g. `args`, `paths`) **replaces** the accumulated value, while its `extend-`-prefixed twin (`extend-args`, `extend-paths`, `extend-variables`, …) **appends** to it. This is how a profile adds to the base config instead of clobbering it.
- **`inherits`** — a profile can pull in other profiles by name (string or list); parents are selected and merged too.
- **`enabled` / `hidden`** — a profile can switch itself off (`enabled = false`, or an `if` condition) or hide from listings; disabled profiles are skipped during merge.
- **`default-profiles`** — config key choosing what runs when no `--profile` is given.

To see the merged result of a selection, run `robotcode -p <a> -p <b> config show` (or `profiles show` for a single profile's own definition).

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
- Investigate a failing test without rerunning first.
- Lint only changed Robot files.
- Analyze a project and manage suppressions / exit-code masks.

## Gotchas — agent-correction notes

- For Robot Framework library, resource, or keyword documentation, do not start with Context7, web search, or generic knowledge. Query project-local `robotcode libdoc` first; fall back to external documentation only when `libdoc` cannot answer or the topic is outside the local Robot environment.
- Global options belong before the subcommand; otherwise Robot Framework may reject them.
- `analyze code` and `robot` have different exit-code semantics.
- `output.xml` is not a completion signal and should not be read directly for normal result analysis. After a run, use `robotcode results summary`, `show`, `log`, `stats`, or `diff` instead of loading a potentially huge XML file into context.
- `Error: No such command 'X'` means a RobotCode extra is missing.
- `uvx` / `pipx` isolates RobotCode from the project and gives wrong answers for real projects.
- `No profiles defined.` is an empty result, not an error.
- REPL syntax is not `.robot` file syntax.
- "What tests/tags/suites exist?" — and any "which tests have tag X / are in suite Y" question — is answered with `robotcode discover`, never by reading or grepping `.robot` files. The effective set is resolved at runtime (paths, config, profiles, variables, pre-run modifiers); static sources don't show it.