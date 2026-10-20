# Design

## Context

See proposal.md, Why. The facts behind the decisions, checked in the code on 2026-10-20:

- **Where a test ID is built.** The format `<source>;<long name>;<line>` is written out in five places:
  - `discover.py`, `Collector.visit_test`: `f"{absolute_path or ''};{test.longname};{test.lineno}"`, and next to it `range=Range(start=Position(line=test.lineno - 1, …))`, which raises the `TypeError` for `None`.
  - `listeners.py`, `ListenerV2.start_test` and `end_test`: `attributes.get('lineno', 0)`. Robot Framework passes the key with the test's `lineno` (RF 7.5 `output/listeners.py`, `_test_attrs`), so for a test without one the default does not apply and the ID ends in `;None`.
  - `listeners.py`, `ListenerV3.start_suite`, the enqueued items: `item.lineno`.
  - `listeners.py`, `ListenerV3.end_suite`, the re-marked tests: `data_item.lineno if data_item is not None else 0`.
- **What reads the line part of an ID.** Only PyCharm's `enqueuedTestCount` (`RobotCodeFailureDetails.kt`), which counts an enqueued item as a test when the last of its `;`-separated parts is an integer. VS Code and the Python packages compare IDs as a whole.
- **Where positions come from.** From the `range` of a discovery item, which is 0-based (`lineno - 1`), and from the `lineno` fields of discovery items and run events, which are 1-based, as Robot Framework's. VS Code computes `(lineno ?? 1) - 1` and draws decorations only for `lineno > 0`; PyCharm computes `(lineno ?: 1) - 1` and reads `range?`. `discover` leaves fields that are `None` out of its JSON.
- **The duplicate-name warning** in `visit_test` reads `Warning in file '<source>' on line <lineno>: Multiple tests with name …`.

## Goals / Non-Goals

**Goals:**
- One ID for a test without a line number, in the discovery and in every event of a run.

**Non-Goals:**
- No change to the IDs, lines or ranges of tests with a line number.
- No change to the clients.
- No shared function for the ID format (maintainer, 2026-10-20: not in this change).

## Decisions

### D1: `0` is the line part of the ID when the line is unknown (maintainer's choice)

- Robot Framework's line numbers start at 1, so `0` names no line, and the ID stays `<source>;<long name>;<integer>` for every test.
- `0` is already what the debugger falls back to where it has no line (`attributes.get('lineno', 0)`, `end_suite` without a data item).
- PyCharm's test count then covers these tests without a change in the plugin.
- A line number of `0` from a parser counts as unknown as well: Robot Framework never reports it for a real line, and `0 - 1` would make a range before the first line.
- **Alternative: keep `None`.** It is the Python spelling of "nothing", and PyCharm does not count such tests.
- **Alternative: a negative number such as `-1`.** It would work as well, but brings a sign into the ID and differs from the existing fallback.
- **Alternative: an empty last part (`…;`).** PyCharm would not count these tests either.

### D2: `lineno` and `range` stay empty

- The discovery item of such a test has no `lineno` and no `range`, and the run events carry no `lineno` for it, as today where they do not fail.
- Both clients turn only these fields into positions. A `0` there would become line `-1` in VS Code's `(lineno ?? 1) - 1`; left empty, the clients fall back to the first line of the file for a failure location, and VS Code shows no test marker in the editor.

### D3: The five places change in place

- `discover.py`: the ID with `test.lineno or 0`, the range only when `test.lineno` is set, and the warning without "on line …" when it is not.
- `listeners.py`: `attributes.get("lineno") or 0` in `start_test` and `end_test`, `item.lineno or 0` for the enqueued items, and the line of a data item or `0` in `end_suite`.
- **Alternative: one function that builds the ID, used by both packages.** It would keep the format in one place, but is a refactoring beyond this fix; the maintainer left it out.

## Risks / Trade-offs

- [Another consumer parses the line part of an ID] → None found in the Python packages, the VS Code extension and the PyCharm plugin besides PyCharm's count, which this change satisfies.
- [Results remembered under an old ID] → Tests without a line number never had a tree item, since the discovery failed; there is nothing to carry over.
- [The places drift apart again] → The tests compare the IDs of a run with those of the discovery for the same suite.
