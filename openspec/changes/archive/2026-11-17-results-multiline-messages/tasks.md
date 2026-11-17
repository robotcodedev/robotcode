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

## 4. Whole lines and the summary (D1, D3, D4)

The first version of 1.1 cut the whole message anywhere; the maintainer's review on 2026-11-17 changed that to D1, D3 and D4.

- [x] 4.1 In `results.py`, one function shortens a message by D1, and `_truncate()` and `_make_test_item()` use it, so that `show` also marks a cut line with `...` (D4). `results summary` takes `--message-chars` with the default 120 and passes it to its list of failures (D3). Verify with the test of ten lines in the scratchpad (`rc625/ten`) that `show --failed`, `summary --failed`, `diff` and `compare --show failures` show two lines and `... (8 more lines)`, and with `--message-chars 0` all ten.
- [x] 4.2 Tests in `tests/robotcode/runner/cli/results/test_multiline_messages.py` for the scenarios of "Shortening a message": whole lines with `fullMessage`, a first line longer than the limit, the summary by default with a message of ten lines, and no limit; `test_message_chars_counts_the_line_breaks` goes, as the scenario it tested changed. Verify that the new tests pass with 4.1 and fail on the state before it (`5310aa731`), and that the tests of `--message-chars` in `test_show.py`, `test_diff.py` and `test_compare.py` still pass.
- [x] 4.3 Generate `docs/src/content/docs/reference/cli.md` again and verify that `results summary` lists `--message-chars`. In `references/results.md` of the skill, say that `summary --failed` is cut to `--message-chars` too, commit it in `robotframework-agent-plugins` on the maintainer's word, and sync `chat-plugins/`.
- [x] 4.4 `hatch run lint:all` and `hatch run test:test` pass.

## Workflow follow-up

- Commit only on request: the fix with `Fixes #625` and `Co-authored-by: Emil Söderberg <emil@stutt.se>` (D2); while it isn't pushed, section 4 can go into that commit. The OpenSpec files in `docs(openspec)` commits; push on request.
- Archive the change.
