# Proposal

## Why

In PyCharm and IntelliJ IDEA, the analysis settings of RobotCode cannot be changed: the diagnostic mode, diagnostic modifiers, library loading options, cache options, exclude patterns and the Robocop settings all keep VS Code's defaults, with no page to edit them. The plugin also sends the language server no initialization options, so the server keeps its analysis cache in `<project>/.robotcode_cache`. IntelliJ shows that folder in the Project view and indexes it again whenever the cache database changes. And the plugin shows Information and Hint diagnostics at the same level, the IDE's silent "information" level: neither appears in the Problems view, so moving a code to `information` hides it almost as well as `ignore` does.

This is the second step towards settings that match VS Code (issue #417).

## What Changes

- Add two sub-pages to the "Robot Framework" settings node that follow VS Code's settings categories:
  - **Analysis**: diagnostic mode, progress mode, find unused references, references code lens, the cache settings (save location, ignored libraries, ignored variables, ignore arguments for library), the global library search order and load library timeout, the five diagnostic modifier lists (ignore, error, warning, information, hint), and VS Code's one-setting categories Workspace (exclude patterns) and Experimental (semantic model);
  - **Robocop**: enabled, config file, ignore Git dir, ignore file config.
- The labels are VS Code's setting titles, so that users find a setting under the same name in both IDEs and tips from one IDE work in the other. The choices keep IntelliJ terms, such as "IDE system directory" for VS Code's `workspaceStorage`.
- The language server receives the values from these pages. The page texts say which lists are added to those in `robot.toml` (`[tool.robotcode-analyze]`), that the library load timeout overrides `robot.toml`, that exclude patterns use `.gitignore` syntax, and that switching Robocop off does not switch off formatting. The texts fix the mistakes in VS Code's descriptions, for example the swapped descriptions of the cache locations.
- The seven default exclude patterns become editable.
- Keep the analysis cache in a per-project folder of the IDE's system directory by default, as VS Code keeps it in its workspace storage. The save location "Project folder" stays selectable: then the cache stays in `<project>/.robotcode_cache`, the folder that `robotcode analyze` uses when it runs in the project.
- Send the language server initialization options, as VS Code does: the storage folder, the Robot Framework Python path and environment variables from the settings, and the complete settings tree. The server applies the Python path and environment before it checks Robot Framework.
- Show Information diagnostics as weak warnings, listed in the Problems view as in VS Code. Hint diagnostics keep the IDE's information level: they are not listed in the Problems view, and their message appears on hover.
- Applying several RobotCode settings pages at once restarts the language server once instead of once per page.

Behaviour that users notice, for the release notes (not breaking): the analysis cache leaves the project folder by default, so `.robotcode_cache` no longer appears in new projects, and an existing one is no longer written by the IDE (`robotcode analyze` in the project still uses it; otherwise it can be deleted). Information diagnostics now appear as weak warnings and in the Problems view.

Not part of this change: quick toggles for Robocop and workspace-wide diagnostics; the values of the Robot Framework Python path and environment variables (the initialization options carry them once they can be set); the cache folder for the IDE's terminal; excluding `.robotcode_cache` from indexing when the project folder is chosen; restarting only when a setting needs it.

## Capabilities

### New Capabilities

- `intellij-language-server`: the initialization options the plugin sends the language server, and where the server keeps its analysis cache.

### Modified Capabilities

- `intellij-settings`: adds the Analysis and Robocop pages to the Robot Framework settings node, how Information and Hint diagnostics are shown, and that the labels of the settings pages follow VS Code's setting titles.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/configuration/`: the stored project settings, the settings mapper and two new pages.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/lsp/RobotCodeLanguageServer.kt`: `getInitializationOptions`.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/lsp/features/RobotDiagnosticsFeature.kt`: the severity mapping.
- `intellij-client/src/main/resources/META-INF/plugin.xml`: the two pages as child configurables.
- `intellij-client/src/main/resources/messages/RobotCode.properties`: the page texts.
- New unit tests under `intellij-client/src/test/kotlin/`.
- No change to the language server, the VS Code extension or `robot.toml`.
