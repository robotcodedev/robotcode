# Tasks: results-multiline-messages

## 1. The message as a whole (D1)

- [x] 1.1 In `packages/runner/src/robotcode/runner/cli/results/results.py`, `_truncate()` and `_make_test_item()` cut the whole message to `--message-chars`, line breaks counted, and keep it whole with 0. The help of `results show` says that each test comes with its message, cut to `--message-chars`, instead of its first line. Verify with the test of #625 that `show --failed`, `summary --failed` and `diff` show all three lines and `compare --show failures` shows them in one cell.
- [x] 1.2 Add tests in `tests/robotcode/runner/cli/results/` for the scenarios of the spec delta: `show --failed`, `summary --failed`, `diff`, `--message-chars 40` with `fullMessage`, `--message-chars 0`, and `compare --show failures`. Verify that they pass with 1.1 and fail without it.
- [x] 1.3 Generate `docs/src/content/docs/reference/cli.md` again with `hatch run create-cmd-line-docs` and verify that its text of `results show` no longer says "first line".

## 2. The skill

- [x] 2.1 In `robotframework-agent-plugins` (branch `next`), `plugins/robotcode/skills/robotcode/references/results.md` says for `summary --failed` and `show` that each failed test comes with its message, not its first line. Verify with `grep -n "first line"` on the file.
- [x] 2.2 After the commit in `robotframework-agent-plugins`, which needs the maintainer's word, sync the copy with `hatch run build:sync-chat-plugin` and verify that it matches the source.

## 3. Verification

- [x] 3.1 `hatch run lint:all` and `hatch run test:test` pass.

## Workflow follow-up

- Commit only on request: the fix with `Fixes #625` and `Co-authored-by: Emil Söderberg <emil@stutt.se>` (D2), the OpenSpec files in `docs(openspec)` commits; push on request.
- Archive the change.
