# Tasks

Everything in `robotframework-agent-plugins` happens on `next`. Commits only on the maintainer's request; the maintainer pushes. Evals only in the rounds of D9, nothing small gets its own run.

## 1. The evals first

- [ ] 1.1 Add `"skills": []` to the check of `run.py`, name the skill for a Haiku model only when the case expects it, and add `--no-skill` (D9). Verify: a run of case 29 with a stubbed transcript in which the skill is loaded fails; `python3 -B -m py_compile evals/robotcode/run.py` passes.
- [ ] 1.2 Add cases 21–29 (D9) and their rows in the README, and replace "there is no official runner" there. Verify: all JSON files load; the `prepare` of case 25 creates its folder in a copy of the fixture; the regexes of each case match a command written by hand for the right way and not one for the wrong way.
- [ ] 1.3 Round 1: run cases 21–29 once with Sonnet against the skill of `88b5555` and robotcode before the changes of section 2. Verify: the table of results and, for each case that passes on the old text, why, in `playground/agent-skill-befunde.md`. A case that should fail and doesn't goes back to its checks.

## 2. robotcode

Each fix with its own tests, which pass with the fix and fail without it.

- [ ] 2.1 A line breakpoint matches by the end of the path, and `.breakpoints` shows it as given (D1). Verify: tests in `tests/robotcode/repl/` for a file name alone, part of the path, two files with that name, an absolute path, a path with `..`, `restart` keeping it, using `tmp_path` and both separators where the platform has them.
- [ ] 2.2 The warning for a breakpoint no keyword reached (D2). Verify: tests for a file that isn't in the run, the line of a test's name, a false condition (no warning), a keyword breakpoint, `.abort` and `.detach` (no warning), the unchanged exit code, and the warning in the answer of `session wait`.
- [ ] 2.3 `.abort` goes the way of SIGTERM (D3), also for `session stop`, `session restart` and the idle timeout. Verify: tests that read the output with `results summary` after each of them, with a teardown that runs and one with a breakpoint, exit code 253, and a teardown that hangs ended by the second signal; `hatch run test.rf50:test` and `hatch run test.rf75:test` on `tests/robotcode/repl/`.
- [ ] 2.4 `config info desc` and `list` find an exact name (D4). Verify: tests for `[profile].precedence` and `*.precedence`.
- [ ] 2.5 The example in `results --help` (D4). Verify: the example runs on a finished run; `hatch run create-cmd-line-docs` shows the new line in `reference/cli.md`.
- [ ] 2.6 A `{ expr }` that can't be evaluated (D4). Verify: tests for `robot` (252, no traceback), `discover tests` (1, no traceback) and `profiles show`.
- [ ] 2.7 Errors of dot commands reach `session send` (D4). Verify: tests for `.foo`, `.print ${nope}`, `.set ${nope} x`, `.doc` without a target (exit 1, the session goes on) and `.vars` (exit 0).
- [ ] 2.8 Update the unit tests and the spec of the sessions where they pin the old `.abort`. Verify: `hatch run test:test` once over the matrix and `hatch run lint:all` pass; a failure on a Robot Framework version that doesn't support the default Python is checked on `devel.pyX-rfYY`.

## 3. The corrections in the skill

- [ ] 3.1 Correct `SKILL.md` as in D5, without the new order yet. Verify: each command changed there runs as written on a copy of the fixture with the default user configuration.
- [ ] 3.2 Correct `references/debugging.md` and `references/repl.md` as in D5. Verify: as in 3.1; `wc -c` under 20 000 B for both.
- [ ] 3.3 Correct `references/config.md`, `workflows.md`, `analyze.md`, `authoring.md`, `large-projects.md`, `results.md` and `install.md` as in D5. Verify: as in 3.1, with workflow E run from its first step to the merge.
- [ ] 3.4 Remove the text of finding C (D5). Verify: `grep` for each quoted place; every link and its anchor has its target.

## 4. Order, length and description

- [ ] 4.1 Bring `SKILL.md` into the order of D6 and down to the target. Verify: the estimate with `tiktoken` (cl100k) gives at most 4800 tokens for the body; every link and anchor in the skill has its target; what moved out is in the file named in D6.
- [ ] 4.2 Replace the `description` (D7). Verify: under 1024 characters, and `claude plugin validate plugins/robotcode` passes from `robotframework-agent-plugins` with the separate configuration.

## 5. The docs

- [ ] 5.1 Update `guides/cli/robot-debug.md`, `guides/cli/sessions.md` and other pages on `.abort` (D8). Verify: `grep -rn "no reports" docs/src/content/docs/guides` finds nothing about `.abort`; `npm run docs:build` passes.
- [ ] 5.2 Correct the prose of the guide's pages (D8); they stay uncommitted with `docs-ai-agents-guide`. Verify: `grep -rn -E -- "(-p|--profile) [a-z]+ config show" docs/src/content/docs` finds only the recorded excerpt that task 3.8 of that change replaces.

## 6. Round 2

- [ ] 6.1 Run round 2 of D9 once. Verify: tables in the findings; each failure read against its transcript. A wrong way goes back to the text, a right way with a failed check to the check, and only those cases run again.
- [ ] 6.2 Count the references opened in that round. Verify: each reference is opened by at least one case, `install.md` by case 20; a reference no case opens gets its query changed.

## 7. Round 3

- [ ] 7.1 When everything else is done, run all cases once with Codex and opencode, after asking, because Codex costs credits. Verify: tables in the findings, and the same handling of failures as in 6.1.

## 8. Commits

- [ ] 8.1 Ask for the commits of robotcode, one per fix of section 2, and of the docs. Verify: `git show --stat` of each lists only its own paths; the guide's files are not among them.
- [ ] 8.2 Ask for the commits in `robotframework-agent-plugins` on `next`: the skill (`docs(skill)`) and the evals (`test(skill)`). After them, sync the vendored copy with `hatch run build:sync-chat-plugin` and ask for `chore(chat-plugin): sync robotcode skill from agent-plugins`, and for the plan (`docs(openspec)`). Verify: `python scripts/sync_manifests.py --check` and `hatch run build:sync-chat-plugin --check` pass, the commits are signed, and `chat-plugins/.upstream.json` names the new commit.

## Workflow follow-up

- `skill-sessions` is archived before this change.
- `/opsx:archive skill-review-fixes`, then `openspec validate --specs --strict`.
- Task 3.8 of `docs-ai-agents-guide` records the sessions with the corrected skill.
