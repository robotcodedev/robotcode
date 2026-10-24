# Design: intellij-robot-toml-and-code-blocks

## Context

See proposal.md for what PyCharm does today. Facts the approach rests on, from the check in the UI-test PyCharm 2026.1:

- PyCharm's TOML plugin uses JSON schemas (its module `intellij.toml.json`). The status bar shows the schema of the open TOML file, "No JSON schema" for `robot.toml` today.
- With RobotCode's schema mapped by hand under *Languages & Frameworks | Schemas and DTDs | JSON Schema Mappings*:
  - PyCharm downloaded `https://www.robotcode.io/schemas/robot.toml.json` (HTTP 200, 470 KB) into its HTTP file cache;
  - it showed "Schema: robot.toml";
  - it completed `lang` to `languages` and `extend-languages`, with their titles;
  - it did not mark `nonsense-key = 1` or `output-dir = 5`.
- The SchemaStore catalog (1542 entries) has no entry for `robot.toml`.
- VS Code: `package.json` contributes `tomlValidation` for the file names `robot.toml` and `.robot.toml`, with the URL above.
- Markdown:
  - PyCharm's Markdown plugin injected a block marked `robotframework` as the language `robotframework` (file type `ROBOT_FRAMEWORK_SUITE`) and highlighted it in the editor and the preview.
  - A block marked `robot` was not injected.
  - VS Code's code block grammar (`syntaxes/codeblock_robotframework.tmLanguage.json`) starts a Robot Framework block at the info string `(?i:(robot|robotframework)(\s+[^`~]*)?$)`.
- Extension points:
  - JSON: the platform's extension point list names `JavaScript.JsonSchema.ProviderFactory` in the module `intellij.json.backend`. Since 2024.3 a plugin needs an explicit dependency on `com.intellij.modules.json`, and the build needs it as a bundled plugin.
  - Markdown: the plugin descriptor of PyCharm 2026.1 declares `org.intellij.markdown.fenceLanguageProvider` with the interface `org.intellij.plugins.markdown.injection.CodeFenceLanguageProvider`. PlantUML and Mermaid register providers there.
- The plugin today depends on `com.intellij.modules.platform`, `com.intellij.modules.python`, `com.redhat.devtools.lsp4ij` and `org.jetbrains.plugins.textmate`, all required.

## Goals / Non-Goals

**Goals:**

- `robot.toml` and `.robot.toml` get RobotCode's schema with no setup, as in VS Code.
- Markdown code blocks marked `robot` or `robotframework`, in any case, are Robot Framework code, as in VS Code.
- RobotCode keeps working when a user switches PyCharm's JSON or Markdown support off.

**Non-Goals:**

- What PyCharm does with the schema beyond the association. Validation is PyCharm's, and it did not mark errors even with a mapping by hand.
- A SchemaStore entry for `robot.toml`. It would help other editors, but it is an outside contribution and not needed for PyCharm.
- The Markdown injection grammar of VS Code. The requirement "Robot Framework files are highlighted with the bundled grammar" keeps excluding it; the blocks are injected as the plugin's language, which brings its own highlighting.
- Completion of the info string after three backticks.

## Decisions

### D1: The schema comes from the URL VS Code uses

The provider points at `https://www.robotcode.io/schemas/robot.toml.json` as a remote schema. PyCharm downloads it once and keeps it in its HTTP file cache.
- It is the same schema as in VS Code and the one the `robot.toml` guide names for other editors.
- It needs no build step.

Alternative: bundle `docs/public/schemas/robot.toml.json` (470 KB) in the plugin. That works offline and matches the plugin version exactly. It needs a Gradle step that copies a generated file into the resources, and the plugin grows. The URL is enough, as it is for VS Code.

### D2: A JSON schema provider for the two file names

A `JsonSchemaProviderFactory` returns one provider:
- available for files named `robot.toml` or `.robot.toml`, by exact name;
- named `robot.toml`, which the status bar shows;
- with the remote schema file for the URL as its schema, of the remote schema type.

The method names (`isAvailable`, `getName`, `getSchemaFile`, `getSchemaType`, `getRemoteSource`) and how a remote file is made from a URL get checked against the platform sources at the tag of the minimum supported version when the provider is written.

### D3: A code fence language provider for `robot` and `robotframework`

A `CodeFenceLanguageProvider` returns the Robot Framework language when the first word of the info string is `robot` or `robotframework`, in any case, and nothing otherwise. `robotframework` already works through the Markdown plugin's own lookup by language id. The provider takes it too, so that both behave alike, also in another case. The completion variants for the info string stay empty (Non-Goals).

### D4: Optional dependencies with their own descriptors

`plugin.xml` gets two optional dependencies, each with its own config file that registers the provider:
- `com.intellij.modules.json`;
- `org.intellij.plugins.markdown`.

A required dependency would switch RobotCode off together with JSON or Markdown support. `gradle.properties` adds both to `platformBundledPlugins`, so that the code compiles against them and the tests run with them.

If `verifyPlugin` reports new experimental or internal API usages from the two providers, they are decided on then. The LSP4IJ usages it reports already are known and accepted.

## Risks / Trade-offs

- [Offline on first use, completion waits until the schema is downloaded] → Same as VS Code. PyCharm keeps the downloaded file.
- [The schema on the site follows the published documentation, not the installed plugin] → Same as VS Code. The site is published with each release, so a released plugin and the schema match.
- [Unit tests that complete from a remote schema would need the network] → The tests check the association: the schema the IDE finds for `robot.toml`, `.robot.toml` and `pyproject.toml`. Completion is checked once in the UI-test PyCharm.
- [The Markdown plugin may pass more than the language in the info string, such as attributes] → D3 compares only the first word. Blocks with attributes are part of the harness check.
