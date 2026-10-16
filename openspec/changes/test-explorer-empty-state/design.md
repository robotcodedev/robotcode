# Design

## Context

See proposal.md for the motivation. Checked on 2026-10-16:

- VS Code shows welcome content in the Testing view only when no test controller is busy and the whole test collection is empty (`reevaluateWelcomeState` in `src/vs/workbench/contrib/testing/browser/testingExplorerView.ts`). Its two built-in entries, the sentence "No tests have been found in this workspace yet." and the button "Install Additional Test Extensions...", have no `when` clause and are always shown.
- An extension contributes to the same list with `contributes.viewsWelcome` and `view: "testing"`, which `viewsWelcomeExtensionPoint.ts` maps to `workbench.view.testing`. `group` and `order` are honoured only with the proposed API `contribViewsWelcome`; without it an entry gets the default group and order 5, the same as VS Code's sentence and before its button (order 10). A paragraph that is only a command or web link renders as a button; `when` takes a context-key expression.
- `vscode-client/extension/testcontrollermanager.ts`: `robotcode discover --read-from-stdin all` without tests returns a workspace item whose suite has no children (checked for an empty project with `robot.toml` and for a folder with only a resource file); `refreshItem` does not keep container items without children and without error (`:1215-1218`, `:1264-1266`), so the tree ends empty. A discovery failure becomes a workspace item with `error` (`:1058-1070`) that stays in the tree. A folder with `robotcode.testExplorer.enabled: false` or `robotcode.disableExtension` is skipped (`isTestExplorerEnabledForWorkspace`, `:1131`). The controller sets no context keys today; `chatPluginsManager.ts` shows the extension's pattern with `setContext`.
- Changes of `robotcode.testExplorer` settings already run a workspace refresh (`:287-304`), as do folder changes and the file watcher.

## Goals / Non-Goals

**Goals:**

- The hint appears exactly when VS Code would show its own text and RobotCode knows why the tree is empty.
- No new wiring: one context key, computed where the controller already knows the result of every folder.

**Non-Goals:**

- Hiding VS Code's own sentence or button; the view API does not allow it.
- A hint while a discovery still runs, or next to an error item.
- Folder names or other dynamic text in the hint.

## Decisions

### One context key with three states, computed at the end of the workspace refresh

The controller sets `robotcode.testExplorer.state` after the root branch of `refreshItem` has handled every workspace folder: `disabled` when no folder is enabled, `noTests` when every enabled folder was discovered without error and ended with no test or task, `hasTests` otherwise (tests found, or a folder with an error item). The two welcome entries use `when: robotcode.testExplorer.state == noTests` and `== disabled`.

Alternative, `when: config.robotcode.testExplorer.enabled == false` for the switched-off case: rejected, because `config.` keys read the window-level value, while the setting is per folder and `robotcode.disableExtension` has the same effect; the controller already evaluates both per folder.

Alternative, deriving the state from the tree being empty: rejected, because VS Code decides the emptiness itself; the key only has to say why the tree is empty, and `hasTests` keeps the entries out of the way whenever the tree is not.

### Static texts with two buttons each

Entry one (state `noTests`): one paragraph, "RobotCode found no tests or tasks in this workspace. Tests are looked for as `robotcode discover` does, with the `paths`, profiles and `.robotignore` of the folder's `robot.toml`; problems while reading them are listed in the Problems view.", followed by the buttons `[Refresh Tests](command:testing.refreshTests)` and `[Troubleshooting](https://robotcode.io/guides/vscode/troubleshooting/)`.

Entry two (state `disabled`): "RobotCode's Test Explorer integration is switched off by `robotcode.testExplorer.enabled` or `robotcode.disableExtension`.", followed by `[Open Settings](command:workbench.action.openSettings?%22robotcode.testExplorer%22)`.

Both texts come after VS Code's own sentence in sense, so they read as the RobotCode-specific reason; the web link is the only external one and goes to the project's own documentation.

### No change to discovery or the tree

The controller keeps dropping empty containers and keeps the error item for a failed discovery; the first makes the tree empty, the second keeps the hint away, both as today.

## Risks / Trade-offs

- [VS Code's sentence and ours stand together] → the text is written to continue it, not to repeat it.
- [Order of entries with equal order is not defined by VS Code] → the text makes sense before or after VS Code's sentence; the install button has order 10 and stays last.
- [A mixed workspace, one folder disabled, one without tests] → `noTests` wins, because the enabled folder's discovery is the reason the tree is empty.
- [The key lags behind a discovery that is cancelled or aborted] → it is set only when the root branch completes; an aborted refresh leaves the previous state, and the next refresh sets it again.
