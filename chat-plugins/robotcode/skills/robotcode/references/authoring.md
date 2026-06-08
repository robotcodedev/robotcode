# Authoring tests and keywords with RobotCode

Authoring tests, tasks, and reusable keywords with RobotCode follows a project-aware loop: **reuse** what already exists → **prototype** the uncertain parts live → **write** → **check statically before running** → **validate** — leaning on RobotCode's tooling at each step instead of guessing. This file covers that loop and the `robotcode` commands behind each step.

It applies whenever the task is to write, create, or extend a `.robot`/`.resource` test, task, or keyword — as opposed to a one-off exploration ([repl.md](repl.md)) or running existing tests (workflow A in [workflows.md](workflows.md)). Robot Framework's own syntax is assumed knowledge (or look it up with `libdoc`).

## Contents

1. Before writing: reuse, don't reinvent
2. Match the project's conventions
3. Prototype the uncertain parts in the REPL
4. Write the file
5. Check statically before you run
6. Run just what you added, then iterate
7. Refactor into reusable keywords / resources
8. Best practices

## 1. Before writing: reuse, don't reinvent

The single most common authoring mistake is writing a keyword (or a whole test) that already exists. Check first:

```bash
robotcode libdoc <Library> list                 # keywords a library already provides
robotcode libdoc <Library> show "<Keyword>"      # exact signature, args, defaults, docs
robotcode libdoc resources/common.resource list  # keywords your own resource files export
robotcode discover tests --search "<term>"        # is there already a similar test? where?
robotcode discover suites                          # existing suite layout to slot into
robotcode discover tags                            # the tag vocabulary already in use
```

Resolve every keyword you intend to call against `libdoc` rather than from memory — it reflects the *installed* library version, the project's import arguments, and project-local resources. See *Documentation lookup priority* in [SKILL.md](../SKILL.md).

## 2. Match the project's conventions

A new file is only useful if discovery and runs pick it up and it looks like its neighbours:

```bash
robotcode config show       # effective paths, output-dir, variables, python-path, profiles
robotcode config files      # which config files are in play
```

- Place the file under one of the configured `paths` so `discover` / `robot` see it without extra CLI arguments.
- Mirror a sibling `.robot` / `.resource`: section order, naming, tag scheme, Suite Setup/Teardown style, how resources are split.
- Imports resolve through the project's `python-path` / `robot.toml`, so import by name (`Library    Browser`, `Resource    ../common.resource`) — don't hardcode absolute paths.

## 3. Prototype the uncertain parts in the REPL

If locators, keyword sequencing, or a library's behavior are uncertain, **verify them live before committing them to a file** — it is far cheaper than write → run → read failure → guess → repeat. Drive the steps in the REPL (see [repl.md](repl.md)), then `.save` a scratch file or transcribe the lines that worked. This is the natural bridge from an exploration session into a real test.

## 4. Write the file

Standard sections — `*** Settings ***` (Library / Resource / Variables, Suite/Test Setup + Teardown), `*** Variables ***`, `*** Keywords ***`, and `*** Test Cases ***` (or `*** Tasks ***` for RPA). Build calls from the keywords found in step 1; add `[Tags]` so the test is selectable later. Keep each test a complete user/system flow and push mechanical detail down into keywords.

## 5. Check statically before you run

This is RobotCode's biggest authoring advantage — a fast feedback loop that needs **no execution**:

```bash
robotcode analyze code path/to/new.robot
```

Catches missing keywords, wrong/missing arguments, unresolved variables, and duplicate/unused imports. Loop write → `analyze code` → fix *before* spending time on a real run. For the diagnostic format, severity/exit-code rules, suppression, and `--collect-unused`, see [analyze.md](analyze.md) — the full reference (*Static analysis* in [SKILL.md](../SKILL.md) is the summary).

> If you author inside an editor with the RobotCode extension, the language server surfaces these same diagnostics inline as you type — the CLI `analyze code` is the headless equivalent.

For control-flow-heavy suites, a Robot Framework dry run is a good final structural check — it resolves all keywords and imports without executing bodies:

```bash
robotcode robot --dryrun path/to/new.robot
```

## 6. Run just what you added, then iterate

Don't run the whole suite to test one new case:

```bash
robotcode discover tests path/to/new.robot          # confirm it's picked up; copy the longname
robotcode robot -bl "Suite.Sub.New Test Name"        # run only it (exact longname, no glob ambiguity)
robotcode results summary --failed                   # then inspect — see results.md
robotcode results log -bl "Suite.Sub.New Test Name"  # full execution tree if it failed
```

That run-and-read loop confirms the test is wired up and shows a recorded failure. **When a test fails and you want to fix it live, switch to the debugger:** run it through `robotcode robot-debug -bl "<longname>"` rather than a plain `robot` run, so the failure stops you in the live context to inspect and prove a fix on the spot. That trial is ephemeral — so **write the proven fix back into the `.robot` / `.resource` file** and re-run to confirm; running a keyword at the prompt doesn't change your source. (The session mechanics — break-on-failure, `.where` / `.vars` / `.print`, `.continue` — are in [debugging.md](debugging.md).) Drop to the REPL only to refine an *isolated* building block (a locator, a wait, a keyword sequence), not to reproduce a failing *test*.

## 7. Refactor into reusable keywords / resources

Once a sequence is used more than once, extract it into a `*** Keywords ***` block or a shared `.resource` file:

```robotframework
Item Should Exist
    [Arguments]    ${item_id}
    ${response}=    GET    ${BASE_URL}/items/${item_id}
    Status Should Be    200    ${response}
    Should Be Equal    ${response.json()}[id]    ${item_id}
```

Then verify the extraction with RobotCode:

```bash
robotcode libdoc resources/items.resource show "Item Should Exist"  # your keyword now documents itself
robotcode analyze code --collect-unused                              # spot keywords/variables nothing references
```

`--collect-unused` is noisy on resource files that *intentionally* export keywords for other suites — scope it or suppress `KeywordNotUsed` there (see [analyze.md](analyze.md), or workflow D in [workflows.md](workflows.md)).

## 8. Best practices

- **Reuse before you write** (§1) — a `libdoc` / `discover` check up front prevents duplicate keywords and misplaced files.
- **Assert observable outcomes**, not just "no error" — check the resulting state after each meaningful step.
- **Prefer stable identifiers** (primary keys, slugs, ISO codes, robust locators) over volatile ones (timestamps, generated UUIDs, list indices).
- **Tag for selectability** so the test slots into the existing `-i` / `-e` scheme.
- **Keep tests as flows**, push detail into keywords, and keep keywords single-purpose.
- **`analyze code` clean is the definition of done** for the static side; a green targeted run is the dynamic side.
