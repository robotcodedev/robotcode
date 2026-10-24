# Tasks

## 1. Build setup (design D4)

- [ ] 1.1 Add `com.intellij.modules.json` and `org.intellij.plugins.markdown` to `platformBundledPlugins` in `intellij-client/gradle.properties`, and add two optional dependencies with their own config files (`META-INF/robotcode-json.xml`, `META-INF/robotcode-markdown.xml`) to `plugin.xml`; verify that `./gradlew compileKotlin` succeeds.

## 2. Schema for robot.toml (design D1, D2)

- [ ] 2.1 Check the API of `JsonSchemaProviderFactory` and `JsonSchemaFileProvider`, and how a remote schema file is made from a URL, in the platform sources at the tag of the minimum supported version; write a provider factory in `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/json/` whose provider is available for files named `robot.toml` and `.robot.toml`, is named `robot.toml` and points at `https://www.robotcode.io/schemas/robot.toml.json` as a remote schema, and register it in `robotcode-json.xml`; verify with a platform test that the IDE's JSON schema service finds that schema for `robot.toml` and `.robot.toml` and not for `pyproject.toml`.

## 3. Code blocks in Markdown (design D3)

- [ ] 3.1 Write a `CodeFenceLanguageProvider` in `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/markdown/` that returns the Robot Framework language when the first word of the info string is `robot` or `robotframework`, in any case, and register it in `robotcode-markdown.xml`; verify with a platform test that blocks marked `robot`, `Robot` and `robotframework` are injected as `robotframework`, a block marked `robot` with an attribute after the word too, and a block marked `python` is not.

## 4. Docs

- [ ] 4.1 Say that PyCharm completes `robot.toml` and `.robot.toml` from RobotCode's JSON schema without setup in `docs/src/content/docs/guides/pycharm/configuration.mdx` (where it introduces `robot.toml`), `getting-started/configuration.md` (next to the sentence on Even Better TOML) and `guides/robot-toml/index.mdx` (the "Writing the file" item); add rows for `robot.toml` completion and for Robot Framework code blocks in Markdown to `guides/pycharm/compared-with-vscode.mdx`; verify the pages in the docs dev server.

## 5. Verification

- [ ] 5.1 Run `(cd intellij-client && ./gradlew test)` and `./gradlew verifyPlugin`; verify both are green and that `verifyPlugin` reports no new experimental or internal API usages besides the known LSP4IJ ones, or note them for a decision.
- [ ] 5.2 Check in the UI-test PyCharm without a schema mapping by hand:
  - `robot.toml` shows "Schema: robot.toml" in the status bar and completes `lang` to `languages` and `extend-languages`;
  - a `.robot.toml` gets the schema too;
  - a Markdown file highlights blocks marked `robot` and `robotframework` in the editor and the preview.

  Verify with screenshots, then restore the sandbox.

## Workflow follow-up

- Tick D1 and D2 in `playground/pycharm-befunde.md` after the commit.
- Archive the change after review.
