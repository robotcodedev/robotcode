# Proposal: results-multiline-messages

## Why

`robotcode results show`, `results summary --failed` and `results diff` show only the first line of a test's message, also with `--message-chars 0`, whose help says "no truncation" (#625). A failure whose cause is in its second line, such as a multi-line assertion or a traceback-like message, then shows only its start. Only `results log` and the JSON field `fullMessage` of `show` have the whole message. PR #626 by Emil Söderberg fixed this in June, but no longer merges and doesn't cover `results compare`, which came later; it was closed on 2026-11-17 so that the change is made here, with him as co-author.

Showing every line needs a limit that works for lines: a message in `output.xml` has up to 40 lines by default and any number with `robot --maxerrorlines NONE`, and `summary --failed` has no limit at all.

## What Changes

- `results show`, `results summary --failed`, `results diff` and `results compare` show a message with as many whole lines, from the first, as fit into `--message-chars` characters, and a line `... (N more lines)` for the lines left out. A first line that alone is longer is cut and ends in `...`, as a single line is cut today. `--message-chars 0` shows the whole message, as its help says.
- `results summary` gets `--message-chars`, with the default of 120 that `show`, `diff` and `compare` have.
- `results show` marks a cut line with `...`, as `diff` and `compare` do.
- `results compare` puts the lines it shows into its table cell, joined by spaces.
- The help of `results show` and the skill's reference on `results` no longer say "the first line of the message".

## Capabilities

### New Capabilities
- `results-test-messages`: how the `results` commands show the failure and skip messages of tests, and how `--message-chars` shortens them.

### Modified Capabilities

None. `results-compare` says that a group shows one of its messages, cut by `--message-chars`; that stays true.

## Impact

- `packages/runner/src/robotcode/runner/cli/results/results.py`: shortening of messages for `show`, `summary`, `diff` and `compare`; `--message-chars` for `summary`; the help of `show`.
- `tests/robotcode/runner/cli/results/`: tests for messages of several lines.
- `docs/src/content/docs/reference/cli.md` (generated).
- Skill: `references/results.md` in `robotframework-agent-plugins`, then the copy in `chat-plugins/`.
- Not affected: `results log`, which shows whole messages already, and the VS Code extension and the IntelliJ plugin, which don't call these commands.
