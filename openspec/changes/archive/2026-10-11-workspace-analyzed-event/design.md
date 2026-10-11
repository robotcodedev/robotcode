# Design

## Context

See proposal.md for the motivation. How it works today, in `packages/language_server/src/robotcode/language_server/common/parts/diagnostics.py`:

- **When a document needs an update:** `_doc_need_update` is true while the document's `DiagnosticsData` has `force` set, its `version` differs from the document's, or `skipped_entries` is set. A document is marked in three ways:
  - `force_refresh_all` and `force_refresh_document` set `force`; `ensure_workspace_loaded` calls `force_refresh_all` after loading the workspace documents;
  - an invalidated document cache sets `force` for the document and the documents related to it;
  - an open document gets a new version.

  The loop takes the mark away while it analyzes and collects a document (`reset_document_diagnostics_data`, `create_document_diagnostics_task`).
- **A pass of `run_workspace_diagnostics`:** it starts with `on_workspace_diagnostics_start`, clears `in_get_workspace_diagnostics_event` and sets `workspace_diagnostics_started_event`. It then lists the documents that need an update.
  - With none, it waits one second (`check_current_task_canceled(1)`) and ends the pass.
  - With some, it analyzes and collects them. A change can break the pass off (`_break_diagnostics_loop_event`).

  In its `finally` block every pass clears `workspace_diagnostics_started_event`, sets `in_get_workspace_diagnostics_event`, calls `on_workspace_diagnostics_end` and, after a pass without work, waits one more second.
- **Readers of these signals:** only the test fixtures read `workspace_diagnostics_started_event`, `in_get_workspace_diagnostics_event` and `on_workspace_diagnostics_end`. Other hooks of the loop have readers in the language server: `on_workspace_diagnostics_collect` (code lens) and `on_workspace_diagnostics_break` (reference cache).

**Measured on 2026-10-10:** a scratch script started a server as the fixtures do, on Robot Framework 7.5, and waited like them. A handler for `on_workspace_diagnostics_start` and a wrapper around `_doc_need_update` recorded the start of the first pass without work. On an empty workspace that came after 0.01 s, the waits returned after 3.01 s (1.00 s per wait). On `data` it came at the end of the analysis, the waits returned 1.00 s later: after a pass with work the next pass starts at once and finds nothing, and only its end comes after the pause.

## Goals / Non-Goals

**Goals:**

- One signal for "no document needs an update", which a waiter cannot miss.
- Fixtures that wait for it once, without the pauses of the loop.

**Non-Goals:**

- A signal that is exact right after a change (see Risks).
- Changing the pauses and timers of the loop.

## Decisions

### Set the event where the loop finds no work

`DiagnosticsProtocolPart` gets `workspace_analyzed_event`, a `threading.Event`. In `run_workspace_diagnostics`, right after the list of documents that need an update is built:
- an empty list sets the event, before the pause;
- a list with documents clears it, before the pass analyzes them.

The event starts cleared. `ensure_workspace_loaded` runs before the first pass and marks all loaded documents, so the event cannot be set before the workspace documents are known. An empty workspace sets it in the first pass.

Alternative: count the documents that need an update and signal when the count reaches zero. Rejected because the marks are set in several places and taken away by the loop and the document tasks; the loop's own list is the only place that sees all of them at one moment.

### Clear the event only in the loop

The event is cleared only when a pass finds work. Between the moment new work arrives (`force` set, new version) and the next pass, the event can still be set, for at most the one-second pause.

Alternative: also clear it in `force_refresh_all`, `force_refresh_document` and when a document cache is invalidated. Rejected for this change: the fixtures wait right after the start, before any change, and a new version of an open document is only noticed by the loop's list anyway. It can be added when something has to wait after a change.

### One wait in every fixture

The seven fixtures with three waits and `_start` of the restart tests wait with `protocol.diagnostics.workspace_analyzed_event.wait(<timeout>)` and assert the result with a message. The timeout is 300 s, the longest of today's waits. An event keeps its state, so it does not matter whether the fixture waits before or after `_initialized`.

The handler registration for `on_workspace_diagnostics_end` and the local `threading.Event` go away in all eight places.

### Remove the two per-pass events

`workspace_diagnostics_started_event` and `in_get_workspace_diagnostics_event` lose their last readers and are removed with their `set` and `clear` calls. `on_workspace_diagnostics_end` stays: it is a hook of the loop like the others, and removing a hook is not needed for this change.

Alternative: keep both events. Rejected because they would be set and cleared without any reader, next to a second signal for nearly the same purpose.

## Risks / Trade-offs

- **[A document that never gets up to date]** → If a document keeps needing an update, for example because its collection sets `skipped_entries` every time, the event is never set, and a fixture fails at its timeout with a message. The loop would analyze that document again and again anyway. On `data` the analysis reached a pass without work after two passes.
- **[Set although work just arrived]** → see "Clear the event only in the loop". The fixtures are not affected.
- **[Fixtures that relied on the second pass]** → Today the fixtures on `data` wait for one more pass after the first end. The new event is only set by a pass without work, which is a stronger condition than the end of any pass.
