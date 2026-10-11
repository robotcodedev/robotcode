# Proposal

## Why

Eight test fixtures start a language server and wait until its workspace analysis is done before the tests run. The workspace diagnostics loop has no signal for "done". It only reports each pass: `workspace_diagnostics_started_event` when a pass starts, and `in_get_workspace_diagnostics_event` and the `on_workspace_diagnostics_end` event when it ends. These signals come for every pass, also for a pass without work and for one that a change has broken off. Seven fixtures therefore wait for the end of a pass, then for the start and the end of the next one. The restart tests of the namespace cache wait for the first end only.

Between two passes without work, the loop pauses for one second (`check_current_task_canceled(1)`). The fixtures wait for passes that only come after these pauses. Measured on 2026-10-10 on Robot Framework 7.5, from the start of the server until the waits return, compared with the moment no document needs an update anymore:

| workspace | the fixtures' waits | all documents analyzed | difference |
|---|---|---|---|
| empty (the modules with their own temporary project) | 3.01 s | 0.01 s | 3.0 s |
| `data` (the shared server and the parity pairs) | 43.3–81.9 s | 42.3–80.9 s | 1.0 s |

The fixtures start six servers on empty workspaces and seven on `data` in each Robot Framework environment, so the pauses cost about 25 s of the about 200 s a run takes.

The waits are also not reliable. If the first pass is broken off, its end is reported although documents still need an update. The fixtures add their handler for `on_workspace_diagnostics_end` only after `_initialized`, so the first end of a fast analysis can come before the handler exists.

## What Changes

- The workspace diagnostics loop gets an event that is set while no document needs an update: the loop sets it when a pass finds no such document, and clears it when a pass starts with work.
- The eight fixtures wait for this event once, with a timeout, and fail with a message when it expires.
- `workspace_diagnostics_started_event` and `in_get_workspace_diagnostics_event` are removed. Only these fixtures read them.

Not part of this change:
- the one-second pause of the loop and the one-second timers of `refresh` and `break_workspace_diagnostics_loop`;
- clearing the event when new work arrives between two passes (in `force_refresh_*` or when a document cache is invalidated), which waiting after a change would need;
- using the event in the language server, for example to tell whether the reference index is complete before Find References answers;
- how the tests group their servers and caches, which stays as it is.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

<!-- none -->

None, so the change sets `skip_specs: true` in `.openspec.yaml`. No client of the language server reads the new event or the two removed ones, so RobotCode's behaviour, and with it every requirement under `openspec/specs/`, stays the same. The shorter and more reliable waits of the tests are goals that design.md and tasks.md check.

## Impact

- `packages/language_server/src/robotcode/language_server/common/parts/diagnostics.py`: the new event, set and cleared in `run_workspace_diagnostics`; the two per-pass events removed.
- Test fixtures:
  - `tests/robotcode/language_server/robotframework/parts/conftest.py` (the shared server);
  - `test_inline_value_model.py`, `test_selection_range_model.py` and `test_semantic_tokens_flag_parity.py` (the parity pairs);
  - `test_completion_deprecated_keywords.py`, `test_private_keywords.py` and `test_semantic_tokens_variables.py` (own temporary projects);
  - `tests/robotcode/language_server/robotframework/test_namespace_cache_restart.py`.
- Test time: about 3 s less for each server on an empty workspace and about 1 s less for each server on `data`, about 25 s per Robot Framework environment.
