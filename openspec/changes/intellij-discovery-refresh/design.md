# Design

## Context

See proposal.md for the motivation. The state that shapes the approach, checked against the code on main:

- **Discovery** lives in `testing/RobotCodeTestManager`:
  - It listens to document changes of suite files in its project, to VFS events through an application-wide `AsyncFileListener` without a project filter that reacts only to content events of suite files, and to opening and closing editors.
  - Opening or closing a suite file starts a per-file discovery. Folder events are ignored. After a file is deleted, its per-file discovery gets `{"items": []}` with exit code 0, so the empty suite stays in the model.
  - Discoveries run on an own `CoroutineScope(Dispatchers.IO.limitedParallelism(1))` that is never cancelled, and wait in `executeOnPooledThread { … }.get()`. Cancelling a job does not stop the running `robotcode` process.
  - A failure inside the pooled callable is logged by the platform as SEVERE and returns `null` (analysis notes, `test-discovery-errors`). The full discovery then sets the model to empty; the per-file discovery sets the suite's children to empty.
  - `testItems` is a plain property written from the IO thread and read by run markers and producers; the per-file discovery assigns `children` of a suite in place.
  - The JSON is decoded with the default, strict `Json`.
- **What discovery reports about broken files,** checked with Robot Framework 6.0, 7.0 and 7.5: robotcode's `discover all` leaves a file that Robot Framework cannot build into a suite out of the item tree, for example a file that is not valid UTF-8 or that has both tests and tasks. It reports the problem in `diagnostics`, keyed by the file's URI, with a line and a message. Files with tolerable problems, such as `Test Template` set twice, keep their items and get a diagnostic as well. The plugin decodes `diagnostics` as untyped JSON and ignores it; `RobotCodeTestItem.error` is decoded but unused, and it was not set in these cases.
- **Configuration files:** `listeners/RobotCodeVirtualFileListener` reacts to `robot.toml`, `.robot.toml`, `pyproject.toml` and `robocop.toml` by name, from any project, and calls `restartAll()`. The startup activity registers it application-wide for each project.
- **Restarts:** `restartAll()` in `RobotCodeHelpers.kt` debounces for 500 ms, then restarts the language server and refreshes discovery.
- **Planned changes this builds on, none of them implemented yet:**
  - `intellij-profiles`, which this change needs: the personal profile selection, `-p` on every process through a pure argument function, and `restartAll()` after a change.
  - The settings pages and their mapper (`intellij-settings-pages`), the Analysis, Diagnostics and Robocop pages with one debounced restart per Apply and initialization options (`intellij-analysis-settings`), and the extra arguments with their personal state and page-specific Apply rules (`intellij-extra-args`).
  - `intellij-environment-check`, which restarts on interpreter changes by itself.
  - `intellij-rpa-task-markers`, which changes the arguments of the per-file discovery and falls back to a full discovery when a file yields no suite.

## Goals / Non-Goals

**Goals:**

- One rule that decides from what changed whether the language server restarts and whether discovery runs, for every settings page, today's and future ones.
- Discovery that cannot be left half-updated, never leaks a process, and never empties the model because of a failure.
- Failures and unreadable files explained where users look.

**Non-Goals:**

- Restarts on interpreter changes.
- The arguments of the per-file discovery and the fallback for task suites.
- Coalescing many per-file discoveries into one, as VS Code does after five pending ones.
- Editor diagnostics from discovery, a switch for discovery, and a test tree before a run.

## Decisions

### Decide by comparing inputs, not by listing settings

The restart manager keeps two snapshots:
- what the running language server got: its command line with environment and working directory, the settings tree that `createSettings()` returns, and its initialization options;
- what the last full discovery got: its command line with environment and working directory.

On a settings event it waits for the 500-millisecond debounce, builds both snapshots from the current state, and compares them. It restarts the server if the server's snapshot differs, and runs a full discovery if the discovery snapshot differs. The comparison is a pure function of the two old and the two new snapshots, which unit tests cover. A new snapshot is taken whenever the server starts and whenever a full discovery runs.

Alternatives:
- VS Code's list of setting sections that restart (`index.ts:174-205`): it needs care for every new setting, and it misses inputs such as the interpreter or the profiles on the command line.
- The page-specific rules of the planned pages: each page decides on its own, and the rules drift apart.

### One settings topic, fed by pages and stored state

A project topic announces that RobotCode settings changed. Every RobotCode settings page publishes it after `apply()`, and every RobotCode state component publishes it in `loadState()`. The platform calls `loadState()` again when the storage file changes outside the IDE, for example through a VCS update; this is documented platform behaviour and is checked in the harness. The direct restart and discovery calls that the planned pages and the Select Configuration Profiles action make are replaced by publishing. Events for the default project are ignored, as the planned pages already do for it.

Alternative: publishing only from the pages misses external edits of `.idea/robotcodeSettings.xml`.

### Configuration files: only the project's own, with the ignore files

`RobotCodeVirtualFileListener` adds `.gitignore` and `.robotignore`. In `prepareChange`, before the change is applied, it keeps only events for files in the project's content or below the project folder. `robocop.toml` requests a language server restart. The other files request both a restart and a full discovery, because both the server and discovery read them. The listener uses the same debounce.

### Discovery on the service scope, one at a time, with an immutable model

`RobotCodeTestManager` takes the coroutine scope that the platform injects into the service, so that it ends with the project. Discoveries run one at a time:
- A full discovery runs inside `withBackgroundProgress`, so users can see and cancel it. A new full discovery cancels the running one and the pending per-file discoveries.
- A per-file discovery runs without progress.
- A cancelled discovery destroys its `robotcode` process.

The model is an immutable tree in a `@Volatile` property. A full discovery replaces it. A per-file discovery builds a copy of the path from the root to the changed suite and swaps the root. A failed or cancelled discovery leaves the property as it is. Decoding uses `Json { ignoreUnknownKeys = true }`, and the existing test that documents the strict decoding changes accordingly.

Alternative: keeping `executeOnPooledThread { }.get()`, which can neither be cancelled nor fail without a SEVERE entry.

### Triggers by event kind

- A content change of a suite file, from VFS or from the editor's document, requests a per-file discovery after the existing 1-second debounce.
- Creating, deleting, moving or renaming a suite file, and any such event for a folder in the project, requests a full discovery.
- Opening and closing editors requests nothing.
- Settings events go through the comparison above.
- Tools | RobotCode | Refresh Robot Framework Tests requests a full discovery. It is enabled only with a project.

The planned task-marker change states the per-file rediscovery as happening when a suite file is "opened, closed or edited". This change drops opening and closing as triggers, so when both are archived, that requirement's list of triggers needs the same edit.

### Failures: keep the model, one notification

A non-zero exit code, output that cannot be decoded, or an exception while starting the process ends the discovery as failed. The failure handling:
- logs the command line, the exit code and the complete output at WARN;
- keeps the model;
- shows a notification of a new `RobotCode` notification group, registered in `plugin.xml` with balloon display. Its content holds the first five lines of stderr, or the decoding error. Its actions are "Retry", which requests a full discovery, and "Open robot.toml", only when the project folder has one.

The manager keeps the notification it shows. A failure with the same content shows nothing new, a different failure expires the old notification and shows its own, and the next successful discovery expires it. Users find the complete text of the notification in the Notifications tool window as well.

Alternatives:
- VS Code's error item in the Test Explorer: IntelliJ shows no RobotCode test tree before a run.
- A "Show Log" action: the notification and idea.log already hold the output, so the action would add little.

### Problems at the markers, from discovery's diagnostics

`RobotCodeDiscoverResult.diagnostics` gets a type: a map from file URI to a list of entries with range, message and severity. The run marker on line 1 of a suite file appends the messages of its file to its tooltip, through the non-deprecated `RunLineMarkerContributor.Info(Icon, AnAction[], Function)` constructor. For a file that has diagnostics but no suite in the model, a separate `LineMarkerProvider` shows an error icon on line 1 with the messages as tooltip. That icon offers no action, because Robot Framework cannot run the file.

Alternative: a run marker without actions for such files; whether the run gutter shows a marker without actions is not verified, and the separate provider avoids depending on it.

## Risks / Trade-offs

- [The comparison restarts the server for settings it could also take without a restart] → VS Code restarts for them too, and the analysis found that many values are read only once per server process.
- [The platform's `loadState()` call on external changes is an assumption] → The harness changes the stored settings file outside the IDE and checks the restart.
- [A visible progress for every full discovery] → Full discoveries run only on real changes, and per-file discoveries stay silent.
- [Conflict with the planned single-file requirement, which names opening and closing as triggers] → Noted above; the requirement's trigger list changes when both are archived.
- [The per-file arguments change in the task-marker change] → This change wraps the per-file discovery without depending on its arguments.

## Migration Plan

None. Nothing that is stored changes.
