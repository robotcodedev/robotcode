# Design: results-multiline-messages

## Context

See proposal.md, Why. Measured on `main` on 2026-11-17 with the test of #625 (`Fail` with a message of three lines):

- `results show --failed`, `results show --failed --message-chars 0`, `results summary --failed` and `results diff` show only `This is the first line of the error`; `results log` shows all three lines, and the JSON of `show` has them in `fullMessage`.
- The cut happens where the message is taken from the result, in `results.py`: `_truncate()` (used by `diff` and `compare`) and `_make_test_item()` (used by `show` and, with no limit, by `summary --failed`) both keep `splitlines()[0]` and then cut that line to `--message-chars`.
- The Markdown output already quotes every line of a message (`_render.py`, the item of a test and of a diff entry), and the tables of `compare` already join a message's whitespace, line breaks included, into single spaces.
- `_truncate()` marks a cut with `...` (ASCII since `ascii-console-output`, #683); `_make_test_item()` cuts without a mark and keeps the whole message in `fullMessage`. `summary` has no `--message-chars`.

How long a message gets, measured with Robot Framework 7.5 and a test that fails with 60 lines: Robot Framework cuts a failure message when the failure happens, so `output.xml` itself holds 41 lines by default (lines 1 to 20, `[ Message content over the limit has been removed. ]`, lines 41 to 60; `--maxerrorlines`, default 40, a line over 78 characters counting as several) and all 60 with `robot --maxerrorlines NONE`. A first version of this change, which counted the whole message against `--message-chars` and cut it anywhere, showed a message of ten lines of about 48 characters in `show` as two lines and a third cut in its middle without a mark, and in `summary --failed` as all ten lines.

## Goals / Non-Goals

**Goals:**
- Every line a command shows, as many as fit into `--message-chars`, and a count of the lines left out.
- The same limit, with the same default, in `show`, `summary`, `diff` and `compare`.

**Non-Goals:**
- No change to how `compare` groups messages or to `results log`.
- No second option for lines.

## Decisions

### D1: Whole lines within the limit, and how many are left out

A message within `--message-chars` characters, line breaks counted, stays whole, as any message does with 0. A longer one keeps its lines from the first as long as they fit as a whole; a line `... (N more lines)` (`... (1 more line)` for one) follows for the lines left out, and isn't counted against the limit. A first line that alone is longer is cut to the limit and ends in `...`, as `_truncate()` cuts a line today, and the count follows it. One function does this for `_truncate()` and `_make_test_item()`, so all four commands shorten alike; the JSON `message` holds the same text as the output, and `fullMessage` of `show` keeps the whole message.

- Rejected: cutting the whole text at the limit, line breaks counted, wherever it falls (the first version of this change, the change of PR #626): a message of several lines then ends in the middle of a line, and nothing says how much is missing.
- Rejected: a limit of lines, `--message-lines`, next to `--message-chars` for each line: two options in four commands for one need.
- Chosen by the maintainer on 2026-11-17.

### D2: Credit for PR #626

PR #626 by Emil Söderberg (`kemilsoderberg`) made the change of keeping all lines in June; it no longer merges, as `results.py` has changed since, and `compare` came later. The maintainer closed it on 2026-11-17 and decided that the commit of this change carries `Co-authored-by: Emil Söderberg <emil@stutt.se>`, the name and address of his commits in the PR.

### D3: `summary` gets `--message-chars`

`results summary` takes `--message-chars` with the default of 120 that `show`, `diff` and `compare` have, and its list of failures shortens messages by D1. Without it, a message of 40 lines, or more with `--maxerrorlines NONE`, would stand whole in the overview. Chosen by the maintainer on 2026-11-17.

### D4: `show` marks a cut line

`show` ends a cut line in `...`, as `diff` and `compare` do; it follows from D1, which uses one function for all four. Chosen by the maintainer on 2026-11-17.

## Risks / Trade-offs

- [A message whose first lines are short and whose cause comes later shows only its start] → the count says how much is missing; `--message-chars 0`, `fullMessage` and `results log` have the rest.
- [Fewer characters than the limit are shown when the next line doesn't fit as a whole] → intended: no line is cut in its middle, apart from a first line that is longer than the limit.
- [`summary --failed` shows less than before for a first line over 120 characters] → it ends in `...`; `--message-chars 0` shows it whole.
