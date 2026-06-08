# Common workflows

Stringing the right commands together matters as much as picking the right command. Five multi-step flows where the orchestration isn't obvious from the individual sections in [SKILL.md](../SKILL.md).

> **Note**: RobotCode auto-detects non-interactive use and disables paging/colors automatically — no extra flags needed.

## Contents

- [A. Run tests and report what failed](#a-run-tests-and-report-what-failed) — the default `run → summarize` lifecycle
- [B. Investigate a failing test](#b-investigate-a-failing-test) — drill down on *one* failure without re-running
- [C. Lint only the files about to commit](#c-lint-only-the-files-about-to-commit) — git-diff-driven `analyze code`
- [D. Analyze a project for code issues](#d-analyze-a-project-for-code-issues) — full static-analysis sweep, including unused-keyword/variable detection and how to suppress noise
- [E. Fix a whole failing run](#e-fix-a-whole-failing-run) — *many* failures: triage by cause, debug one representative per cause, re-validate in a loop without clobbering `output.xml`

## A. Run tests and report what failed

The default lifecycle: invoke a run, wait for *completion*, then summarize — never reach for the `output.xml` file directly even though the run prints its path.

1. **Run** with whatever filters / profile the task needs:
   ```bash
   robotcode --profile <p> robot -i <tag> -e <wip>
   ```
   **Set the shell timeout to the maximum your tool supports, or run in background** — never guess "how long this will take" and pick a number. The run's `Output: …/output.xml` printout is a human-facing pointer, not a parsing target.
2. **Wait for the process to exit.** The exit code is the completion signal (0 = all passed, `N` = N failed tests, capped at 250). `output.xml` is *not* a completion marker — it's written continuously throughout the run.
3. **Summarize via the CLI:**
   ```bash
   robotcode results summary --failed
   ```
   That gives counts plus a one-line-per-failure listing. For deeper drill-downs use `results show --failed --top N` or jump straight to workflow B. See [results.md](results.md) for the full `results` reference.
4. **Report back to the user**: headline first (`X passed, Y failed, Z skipped`), then the listed failures with a one-line reason each, then mention `log.html` / `report.html` paths from the run output for human follow-up. Don't dump JSON or XML into the response.

## B. Investigate a failing test

When the user asks "why did `X` fail?", drill down to that specific test without re-running. The key move: once you have the test's **full longname** from `show`, use `-bl` (exact match) instead of `-t` (glob) on the follow-up commands — no ambiguity if multiple tests share a name, no risk of accidentally matching siblings.

1. **List the failures and pick the exact test.**
   ```bash
   robotcode results show --failed                                # short list with messages
   robotcode results show --search "<error fragment>"             # narrow if the user mentioned a symptom
   ```
   The output gives one line per test with the **full longname** (e.g. `MyProject.Acceptance.Login.Login With Invalid Password`). Copy that for the next steps.

2. **Look at the test's execution tree.**
   ```bash
   robotcode results log -bl "<full longname from step 1>"
   ```
   `-bl` is exact-match on longname — no glob ambiguity. Add `--max-depth 2` on a first read for deeply nested suites; raise it (or drop the flag) once you've located the failing keyword. Combine with `--level WARN` if the trace is noisy.

3. **Resolve a confusing keyword** (only if the log surfaces one whose behaviour isn't obvious):
   ```bash
   robotcode libdoc <Library> show "<Keyword Name>"
   ```

4. **If the recorded log isn't enough, re-run under the debugger** to capture the *live* state at the failure. The recorded tree from step 2 is usually sufficient, but when you need a variable's value at a specific point, the live call stack, or to try keywords against the paused context, re-run the test under `robotcode robot-debug` and **step through it interactively**:
   ```bash
   robotcode robot-debug -bl "<full longname from step 1>"   # -bl scopes the run to that one test, so the pause lands in it
   ```
   Select the failing test by its **longname** (`-bl`, exact) rather than handing over the file — a bare `.robot` file skips the parent suites' `__init__.robot` (suite setup/variables/tags), so the test runs unlike a real run; selecting by longname builds the full suite tree (its `__init__.robot` runs), only that test executes, and the pause lands inside it instead of on whichever test in the file fails first. It pauses (at the first uncaught failure by default, or a breakpoint you set); inspect with `.where` / `.vars` / `.print ${x}`, move with `.step` / `.next` / `.continue`, and decide each step from what you see. **Always end with a resuming command** (`.continue`/`.detach`/`.abort`) and never start it and wait for its exit — with no input the prompt blocks forever. See [debugging.md](debugging.md).

5. **Re-run just that one test to confirm a fix.**
   ```bash
   robotcode robot -bl "<full longname from step 1>"
   ```
   By longname, not the file path — so the parent suites' `__init__.robot` runs and the confirm-run matches a real run (a bare `.robot` file would skip that directory-level setup). For re-validating *several* previously failing tests at once — or making a whole run of failures green — see **workflow E**, which feeds `--rerunfailed` from a *pinned* output file (the default `output.xml` is overwritten by intermediate runs, including the `robot-debug` run in step 4, so it's not a reliable rerun source).

## C. Lint only the files about to commit

`analyze code` accepts paths on the command line, so feed it the changed `.robot` / `.resource` files from git rather than scanning the whole project:

```bash
git diff --name-only --diff-filter=ACMR HEAD | grep -E '\.(robot|resource)$' \
  | xargs -r robotcode analyze code
```

Exit code is a bitmask (see [analyze.md](analyze.md)): non-zero with bit 1 set means errors — block the commit; only bits 2+ (warnings/infos/hints) means non-blocking.

## D. Analyze a project for code issues

Full static-analysis sweep and cleanup. `analyze code` is the entry point — **[analyze.md](analyze.md)** is the full reference (every flag, the diagnostic codes, the suppression scopes, exit-code masking, the cache). The order that works:

1. **Baseline scan** — `robotcode analyze code` (no path = `robot.toml` `paths`; narrow with a path or `--filter '<glob>'`).
2. **Errors first** — `--severity error` (CI usually blocks only on errors; the severity tag is a full word, so filter, don't `grep`).
3. **Unused items** — add `--collect-unused` for `KeywordNotUsed` / `VariableNotUsed` (off by default; noisy on intentionally-exported keywords).
4. **Suppress what genuinely doesn't apply** — inline `# robotcode: ignore[CODE]`, `-mi CODE` for one run, or project-wide in `robot.toml`.
5. **Gate CI** — the exit code is a bitmask (`1` errors, `2` warnings, `4` infos, `8` hints); mask the non-blocking ones (`-xm warn -xm info -xm hint`, or `exit-code-mask` in `robot.toml`).
6. **Stale cache?** — after refactors, upgrades, or branch switches, `robotcode analyze cache clear` (or `--no-cache-namespaces` for a one-off).

## E. Fix a whole failing run

When a run comes back with several failures and the job is to make it green, fix **by root cause, not by test** — and don't try to do it inside one long debugger session. Two anti-patterns to avoid up front:

- **Debugging test-by-test from the start.** Multiple failures usually trace to *one or two* causes — a broken shared keyword, a changed locator, a config/resource/environment change. Blindly debugging every failure debugs the same cause repeatedly. The recorded messages already cluster the failures; read them first.
- **Stepping through the whole run in one paused session.** You *could* `.continue` from failure to failure, but it buys nothing: the actual fix is a file edit, which the running, paused process won't pick up. You'd exit, edit, and re-run anyway.

So the loop is: **triage with `results` → fix per cause → re-validate** — using the debugger only on a single representative test when a recorded log isn't enough.

The one thing to get right is that **`output.xml` is not a stable snapshot across this loop.** Every run through the runner overwrites the default `output.xml` — including `robotcode robot-debug` and any confirm-the-fix run. So pin the full run's output to its own filename, treat it as the immutable source for both `results` and `--rerunfailed`, and keep intermediate runs from writing over it.

1. **Run once and pin the output.** Give the full run its own file (or copy `output.xml` aside immediately):
   ```bash
   robotcode robot --output results/full.xml          # the immutable source of truth for this loop
   ```

2. **Triage against the pinned file — cluster failures, don't debug yet.** Pass `-o` explicitly so you never read a clobbered default:
   ```bash
   robotcode results summary --failed -o results/full.xml
   robotcode results show --failed -o results/full.xml                     # per-test messages, to group by cause
   robotcode results stats --by suite --failed -o results/full.xml         # is failure clustered in one area?
   ```
   Failures sharing a message, a keyword, or a suite are almost certainly one cause. The recorded error often already names it (an unresolved/mis-composed variable, a wrong value, a missing import) — no debugger needed.

3. **Per cause, debug one representative test — only if the log isn't enough.** Scope the debug run to that single test (workflow B), and suppress its outputs so it doesn't overwrite the pinned file:
   ```bash
   robotcode robot-debug -bl "<one failing longname>" --output NONE --log NONE --report NONE
   ```
   Step through it (`.where` / `.vars` / `.print ${x}` → `.continue`/`.detach`/`.abort`) to confirm the cause. `--output NONE` (with `--log NONE --report NONE`) tells Robot to write no result files at all. See [debugging.md](debugging.md).

4. **Fix the cause** — edit the keyword / resource / config — then `robotcode analyze code <changed files>` before re-running, to catch the obvious breakage statically.

5. **Re-validate from the pinned file into a *new* file, and iterate.** `--rerunfailed` selects the tests that failed *in the file you hand it*, so feed it the pinned full run — not the mutated default — and write the rerun somewhere new so each round is preserved:
   ```bash
   robotcode robot --rerunfailed results/full.xml --output results/rerun1.xml
   robotcode results summary --failed -o results/rerun1.xml
   ```
   Still red? Repeat from the rerun file (`--rerunfailed results/rerun1.xml --output results/rerun2.xml`) — the source advances `full → rerun1 → rerun2`, each one kept. For a consolidated final report where reruns supersede the originals:
   ```bash
   robotcode rebot --merge results/full.xml results/rerun1.xml
   ```

**The exception — when you genuinely debug the *whole* run.** If a test fails only as part of the full run but passes in isolation — state leaking between tests, execution-order dependence, shared suite setup/teardown — then scoping to one test with `-bl`/`-t` *hides* the bug. Run the whole suite under the debugger and let it stop at each failing test so you can watch the interplay. `--break-on-failed-test` pauses at each failing test's **end** (after the keyword has unwound) — which is what you want here: you inspect the accumulated suite/global state, not a mid-keyword frame. The `--output NONE --log NONE --report NONE` triple is here for the same reason as step 3 — keep this whole-suite debug run from overwriting the pinned `full.xml`:
   ```bash
   robotcode robot-debug --break-on-failed-test tests/ --output NONE --log NONE --report NONE
   ```
