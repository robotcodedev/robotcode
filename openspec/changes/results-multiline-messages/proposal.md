# Proposal: results-multiline-messages

## Why

`robotcode results show`, `results summary --failed` and `results diff` show only the first line of a test's message, also with `--message-chars 0`, whose help says "no truncation" (#625). A failure whose cause is in its second line, such as a multi-line assertion or a traceback-like message, then shows only its start. Only `results log` and the JSON field `fullMessage` of `show` have the whole message. PR #626 by Emil Söderberg fixed this in June, but no longer merges and doesn't cover `results compare`, which came later; it was closed on 2026-11-17 so that the change is made here, with him as co-author.

## What Changes

- `results show`, `results summary --failed` and `results diff` show all lines of a message, each as a line of the quote under the test, as they already do for a message that comes with line breaks after shortening.
- `--message-chars N` cuts the message as a whole, line breaks counted, to N characters; `--message-chars 0` shows it whole, as its help says.
- `results compare` puts the whole message, up to `--message-chars`, into its table cell, with its lines joined by spaces, where it showed the first line.
- The help of `results show` and the skill's reference on `results` no longer say "the first line of the message".

## Capabilities

### New Capabilities
- `results-test-messages`: how the `results` commands show the failure and skip messages of tests, and how `--message-chars` shortens them.

### Modified Capabilities

None. `results-compare` says that a group shows one of its messages, cut by `--message-chars`; that stays true.

## Impact

- `packages/runner/src/robotcode/runner/cli/results/results.py`: shortening of messages for `show`, `summary`, `diff` and `compare`; the help of `show`.
- `tests/robotcode/runner/cli/results/`: tests for messages of several lines.
- `docs/src/content/docs/reference/cli.md` (generated).
- Skill: `references/results.md` in `robotframework-agent-plugins`, then the copy in `chat-plugins/`.
- Not affected: `results log`, which shows whole messages already, and the VS Code extension and the IntelliJ plugin, which don't call these commands.
