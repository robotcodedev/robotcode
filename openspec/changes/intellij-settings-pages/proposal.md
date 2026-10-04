# Proposal

## Why

In PyCharm and IntelliJ IDEA, RobotCode's settings page is a stub. It shows "!!!! ATTENTION !!! this is work in progress", two fields that do nothing (Arguments, Mode) and comments with raw markdown. Behind it, the plugin sends the language server only two of the settings the server reads: the inlay hint flags, and with `false` as their default. So the server, which defaults them to `true`, shows no inlay hints out of the box. The completion settings are stored but never sent. Every other section the server asks for (`robotcode.analysis`, `robotcode.robot`, `robotcode.workspace` and so on) is answered with `null`, so the server falls back to its own defaults, which differ from VS Code's. For example, VS Code's default exclude patterns never arrive, so the server also loads the Robot Framework files below `.venv/` or `node_modules/`.

This is the first step towards settings that match VS Code, and the one users see first (issue #417).

## What Changes

- Replace the stub with a "Robot Framework" node under Settings | Languages & Frameworks:
  - the node's own page says what the RobotCode settings cover and that most project configuration lives in `robot.toml`;
  - an "Editing" sub-page holds the completion and inlay hint settings.
  Later changes add more sub-pages.
- Remove the work-in-progress notice and the "Arguments" and "Mode" fields, which are bound to nothing.
- Write the texts in the plugin's message bundle instead of copying markdown from VS Code's `package.json`. The header style text names both defaults: `*** {name} ***` from Robot Framework 6 on, and `*** {name}s ***` before.
- Send the language server the complete `robotcode` settings tree, both as the answers to `workspace/configuration` and with `workspace/didChangeConfiguration`. It contains every key the server reads: the value from the settings pages where the plugin offers one, VS Code's default otherwise. Values have the types the server parses. That includes VS Code's seven default exclude patterns.
- Turn the inlay hints for parameter names and namespaces on by default, as in VS Code and on the server. Users can switch them off on the Editing page or hide them in Settings | Editor | Inlay Hints.
- Make the completion settings take effect: "Filter default language" and "Header style". The header style is sent only when it is not blank.
- Let the documentation server start on demand, because IntelliJ has no documentation viewer. The server still starts it when something needs a documentation URL.
- Keep the values that existing `.idea/robotcodeSettings.xml` files store. Applying changes still restarts the language server.

Behaviour that users notice, for the release notes (not breaking): inlay hints appear in projects that never changed the setting, and the server skips the folders VS Code excludes by default.

Not part of this change: analysis, diagnostics, Robocop and cache settings; the `robotcode.robot` settings; profiles and extra arguments; personal versus shared storage and settings for new projects; Run & Debug settings; restarts that depend on what changed; settings below project level.

## Capabilities

### New Capabilities

- `intellij-settings`: the Robot Framework settings pages of the IntelliJ plugin, and the settings the language server receives from the plugin.

### Modified Capabilities

_None._

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/configuration/RobotCodeProjectSettingsConfigurableProvider.kt`: the page tree, the Editing page and the new defaults of the stored inlay hint flags.
- A new settings mapper in `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/configuration/`, used by `lsp/RobotCodeLanguageClient.createSettings()`.
- `intellij-client/src/main/resources/META-INF/plugin.xml`: the Editing page as a child configurable.
- `intellij-client/src/main/resources/messages/RobotCode.properties`: the page texts.
- New unit tests under `intellij-client/src/test/kotlin/`, with the expected default settings as a JSON file under `intellij-client/src/test/resources/`.
- No change to the language server, the VS Code extension or `robot.toml`.
