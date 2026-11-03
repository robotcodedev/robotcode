# Tasks

Everything in `robotframework-agent-plugins` happens on `next`. Commits only on the maintainer's request; the maintainer pushes. Evals only in the rounds of D6.

## 1. The eval first

- [ ] 1.1 Add the case `30-results-of-another-run.json` and its row in `evals/robotcode/README.md` (D6). Verify: the JSON loads; `must_run` matches a command written by hand for the right way (`robotcode results log -o out/login/output.xml`, `robotcode results log --failed --output=out/login/output.xml`) and not the wrong ways; `must_not_run` matches `robotcode results -o out/login/output.xml log` and `robotcode results log out/login/output.xml`, and not the right ways.
- [ ] 1.2 Round 1: run the case 3 times with Sonnet against the skill of `next` before section 3. Verify: the result, and for each failure what the transcript shows, in `playground/agent-skill-befunde.md`. If it passes all 3, change the query once and run it again (D6).

## 2. `results log --suite-info`

- [ ] 2.1 Show the suites above a test in the text output (D1, D2, D3), and say so in the help of `--suite-info`. Add `Metadata` to `tests/robotcode/runner/cli/results/suites/nested/__init__.robot`, and tests in `test_log.py` for the nested suites and their order, the documentation and metadata of the top suite, and one selected test. Verify: these tests pass with the change and fail without it, the existing tests of `--suite-info` pass unchanged, `hatch run test:test` and `hatch run lint:all` pass.
- [ ] 2.2 Update the paragraph on `--suite-info` and its example in `guides/cli/analyzing-results.md`, and regenerate `reference/cli.md` with `hatch run create-cmd-line-docs`. Verify: `git diff` of `reference/cli.md` shows only the help of `--suite-info`; `npm run docs:build` passes.

## 3. `SKILL.md`

- [ ] 3.1 Add the sentence on the file of another run (D4). Verify: the command runs as written on a copy of the fixture; the estimate with `tiktoken` (cl100k) gives at most 4800 tokens for the body.
- [ ] 3.2 Change the wording on starting a session in both places (D5). Verify: `grep "prints its ID"` finds nothing in `SKILL.md`; both commands print what the text says, on a copy of the fixture.
- [ ] 3.3 Round 2: run the case 3 times with Sonnet and once with GitHub Copilot CLI (D6). Verify: the table in `playground/agent-skill-befunde.md`; each failure read against its transcript; a wrong way goes back to the text, a right way with a failed check to the check, and only that case runs again.

## 4. Commits

- [ ] 4.1 Ask for the commits of `robotcode`: the fix with its tests and the help (`fix(runner)`), the docs (`docs(website)`). Verify: `git show --stat` of each lists only its own paths.
- [ ] 4.2 Ask for the commits in `robotframework-agent-plugins` on `next`: the skill (`docs(skill)`) and the eval (`test(skill)`). After them, sync the vendored copy with `hatch run build:sync-chat-plugin` and ask for `chore(chat-plugin): sync robotcode skill from agent-plugins`, and for the plan (`docs(openspec)`). Verify: `python scripts/sync_manifests.py --check` and `hatch run build:sync-chat-plugin --check` pass, the commits are signed, and `chat-plugins/.upstream.json` names the new commit.

## Workflow follow-up

- `/opsx:archive results-suite-info-and-skill-wording`, then `openspec validate --specs --strict`.
