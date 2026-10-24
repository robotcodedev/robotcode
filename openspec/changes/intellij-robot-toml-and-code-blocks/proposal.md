# Proposal: intellij-robot-toml-and-code-blocks

## Why

Two things that work in VS Code do not work in PyCharm, checked in the UI-test PyCharm 2026.1 on the demo project:

- **`robot.toml`:** PyCharm neither completes nor checks it; its status bar shows "No JSON schema" for the file. The SchemaStore catalog that PyCharm consults has no entry for `robot.toml`, and the plugin registers no schema. VS Code gets RobotCode's schema through the extension's `tomlValidation` contribution for `robot.toml` and `.robot.toml`. PyCharm can use JSON schemas for TOML files: with the schema mapped by hand, it completes the settings, for example `languages` and `extend-languages` after `lang`, with their titles.
- **Robot Framework code blocks in Markdown:** PyCharm highlights a block marked `robotframework`, in the editor and in the Markdown preview, but not one marked `robot`, which stays plain text. VS Code highlights both.

## What Changes

- The plugin associates RobotCode's JSON schema for `robot.toml`, the one VS Code uses, with files named `robot.toml` and `.robot.toml`, so that PyCharm completes their settings without a mapping by the user. It does so only while PyCharm's JSON support is enabled; without it the plugin works as before.
- The plugin treats Markdown code blocks marked `robot` as Robot Framework code, like those marked `robotframework`, so that the editor and the preview highlight them. It does so only while PyCharm's Markdown support is enabled.
- The PyCharm guide and the getting-started and `robot.toml` pages say that PyCharm completes `robot.toml`, and the comparison with VS Code gets rows for `robot.toml` and for code blocks in Markdown.
- Not part of it: marking unknown settings or wrong value types in `robot.toml`. PyCharm did not do that even with the schema mapped by hand; whatever it does with the schema stays PyCharm's.

## Capabilities

### New Capabilities

- `intellij-robot-toml-editing`: What the IntelliJ plugin provides when `robot.toml` and `.robot.toml` are edited: the IDE's completion from RobotCode's JSON schema.

### Modified Capabilities

- `intellij-syntax-highlighting`: A new requirement for Robot Framework code blocks in Markdown files, marked `robotframework` or `robot`. The bundled grammar stays without the Markdown injection grammar of VS Code.

## Impact

- `intellij-client/src/main/resources/META-INF/plugin.xml` and two new optional plugin descriptors, one for PyCharm's JSON support (`com.intellij.modules.json`) and one for its Markdown support (`org.intellij.plugins.markdown`).
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/`: a JSON schema provider for `robot.toml` and a code fence language provider for Markdown.
- `intellij-client/gradle.properties`: both plugins as bundled plugins of the build, so that the code compiles and the tests run with them.
- Tests in `intellij-client/src/test/kotlin/`.
- Docs: `guides/pycharm/configuration.mdx`, `guides/pycharm/compared-with-vscode.mdx`, `getting-started/configuration.md`, `guides/robot-toml/index.mdx`.
