# Tasks

## 1. Baseline

- [x] 1.1 Record the setup times of the affected fixtures before the change: run the shared server's module `test_hover.py`, the three parity modules and the three modules with their own temporary project with `hatch run test.rf75:test <modules> --durations=0`, and `test_namespace_cache_restart.py` alone. Note the setup time of each server and the run time in this task. Verify that the empty-workspace servers take about 3 s each.

  Note (2026-10-10, Robot Framework 7.5): setup of the shared server 7.91 s (in `test_hover.py`); of the parity pairs 4.72 s (inline values), 5.43 s (selection ranges) and 4.95 s (semantic tokens); of the six empty-workspace servers 3.01–3.36 s each. The seven modules ran in 76.8 s (539 passed, 39 skipped, 1 xfailed). Each restart test took 2.02 s for its two sessions, 6.1 s for the module.

## 2. The event

- [x] 2.1 In `diagnostics.py`, add `workspace_analyzed_event` to `DiagnosticsProtocolPart` and set and clear it in `run_workspace_diagnostics` as described in design.md: set when the list of documents that need an update is empty, before the pause; cleared when it has documents, before they are analyzed. Verify with a short scratch script on an empty and on the `data` workspace that the event is set when no document needs an update anymore (0.01 s on the empty workspace, at the end of the analysis on `data`).

## 3. The fixtures

- [x] 3.1 Let the seven fixtures with three waits wait once for `workspace_analyzed_event`, with a timeout of 300 s and an assertion with a message, and remove their handler for `on_workspace_diagnostics_end` and their local event:
  - `parts/conftest.py`;
  - `test_inline_value_model.py`, `test_selection_range_model.py`, `test_semantic_tokens_flag_parity.py`;
  - `test_completion_deprecated_keywords.py`, `test_private_keywords.py`, `test_semantic_tokens_variables.py`.

  Verify that these modules and `test_hover.py` pass on Robot Framework 7.5 and 5.0.
- [x] 3.2 Let `_start` in `test_namespace_cache_restart.py` wait for `workspace_analyzed_event` instead of its handler for `on_workspace_diagnostics_end`, and drop the comment about the handler that has to be added before the start. Verify that the module passes on Robot Framework 7.5.
- [x] 3.3 Remove `workspace_diagnostics_started_event` and `in_get_workspace_diagnostics_event` with their `set` and `clear` calls, after checking with a search over `packages/`, `src/` and `tests/` that nothing reads them anymore. Verify that `hatch run lint:all` reports nothing.

  Note (2026-10-10): after the change, only the loop itself set and cleared the two events. `hatch run lint:all` stopped at two E501 findings in `tests/robotcode/repl/test_input_errors.py`, a file another session was editing at that moment; ruff and ruff format pass for every file of this change, and mypy reports no issues in 459 source files.

## 4. Integration

- [x] 4.1 Repeat the measurement of 1.1 and note the times next to the baseline. Verify that each server on an empty workspace saves about 3 s and each server on `data` about 1 s.

  Note (2026-10-10, Robot Framework 7.5): the six empty-workspace servers took at most 0.38 s each (before 3.01–3.36 s). The parity pairs took 2.84 s (inline values, before 4.72 s), 3.56 s (selection ranges, before 5.43 s) and 4.34 s (semantic tokens, before 4.95 s). The shared server took 9.19 s (before 7.91 s): it is the first start of the run with an empty library cache, and its time varies by more than the 1 s saved. The seven modules ran in 57.6 s, and in 51.2 s in the run of 3.1 (before 76.8 s), with the same 539 passed, 39 skipped, 1 xfailed. The restart tests still took 2.02 s each: their handler was already added before the start, and the time of a session is the analysis of its project.
- [x] 4.2 Run `hatch run test:test` and verify that every Robot Framework environment is green, and note the run time per environment.

  Note (2026-10-10): green in all nine environments. Test time per environment: rf50 181 s, rf60 163 s, rf61 189 s, rf70 162 s, rf71 151 s, rf72 146 s, rf73 162 s, rf74 158 s, rf75 207 s, together 1519 s. The run of 2026-10-09 took 1802 s; that difference also contains the selection range fix (32369fee) committed in between.
- [x] 4.3 After the maintainer pushes, verify that the CI's Python tests are green on Linux, Windows and macOS.

  Note (2026-10-11): CI run 38088107994 for f5380a91 is green, all 139 jobs. The median of the "Test Python Packages" step went from 5.2 to 4.7 min on macOS, from 4.8 to 4.1 min on Ubuntu and from 6.1 to 5.8 min on Windows, compared with run 38083182393 for e9961d86; the 135 test jobs together took 10.8 h instead of 11.8 h.

## Workflow follow-up

- Archive the change after the maintainer's review. The change has no spec deltas, so no main spec is affected.
