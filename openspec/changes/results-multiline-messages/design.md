# Design: results-multiline-messages

## Context

See proposal.md, Why. Measured on `main` on 2026-11-17 with the test of #625 (`Fail` with a message of three lines):

- `results show --failed`, `results show --failed --message-chars 0`, `results summary --failed` and `results diff` show only `This is the first line of the error`; `results log` shows all three lines, and the JSON of `show` has them in `fullMessage`.
- The cut happens where the message is taken from the result, in `results.py`: `_truncate()` (used by `diff` and `compare`) and `_make_test_item()` (used by `show` and, with no limit, by `summary --failed`) both keep `splitlines()[0]` and then cut that line to `--message-chars`.
- The Markdown output already quotes every line of a message (`_render.py`, the item of a test and of a diff entry), and the tables of `compare` already join a message's whitespace, line breaks included, into single spaces. So only the cut needs to change.
- `_truncate()` marks a cut with `...` (ASCII since `ascii-console-output`, #683); `_make_test_item()` cuts without a mark and keeps the whole message in `fullMessage`.

## Goals / Non-Goals

**Goals:**
- The message as a whole, up to `--message-chars`, wherever the `results` commands show it.

**Non-Goals:**
- No `--message-chars` for `summary`: its list of failures shows whole messages, as it does today for their first line.
- No change to how `compare` groups messages or to `results log`.
- No change to the mark of a cut: `...` where there is one today, none in `show`.

## Decisions

### D1: The limit counts the whole message

`_truncate()` and `_make_test_item()` stop taking the first line: a message longer than `--message-chars` is cut at that character, line breaks counted, and a message within it, or any message with `--message-chars 0`, stays whole. This is the change of PR #626.

- Rejected: cutting each line to the limit, or counting lines. Both need a second option or a second meaning of the one there is, while one length for the whole message keeps `--message-chars` as its help describes it.

### D2: Credit for PR #626

PR #626 by Emil Söderberg (`kemilsoderberg`) made the change of D1 in June; it no longer merges, as `results.py` has changed since, and `compare` came later. The maintainer closed it on 2026-11-17 and decided that the commit of this change carries `Co-authored-by: Emil Söderberg <emil@stutt.se>`, the name and address of his commits in the PR.

## Risks / Trade-offs

- [A long message of many lines makes `show` and `summary --failed` longer] → `--message-chars` limits it in `show` and `diff`; the default of 120 characters stays.
- [A cut can end in the middle of a line] → as today within the first line.
