# Tasks

## 1. Settings tree for the language server

- [ ] 1.1 Add the typed settings model in `configuration/`: one data class per section the server reads, with VS Code's key names and defaults (`robot`, `completion`, `inlayHints`, `analysis` with `cache`, `robot` and `diagnosticModifiers`, `robocop`, `workspace`, `documentationServer`, `experimental`), `documentationServer.startOnDemand` fixed to `true`, and no client-only settings. Add a mapper that builds the `robotcode` tree with Gson without `serializeNulls`. Verify with a JUnit test that the tree for default settings equals `src/test/resources/settings/default-settings.json` (integers, exact enum strings, the seven exclude patterns, inlay hints `true`, `startOnDemand` `true`, no `headerStyle`, `loadLibraryTimeout` or `configFile`). The test names `package.json` as the source of the values.
- [ ] 1.2 Copy the stored completion and inlay hint values into the tree; copy the header style only when it is not blank. Verify with unit tests: stored values arrive; a blank or whitespace-only header style is left out; no list in the tree contains `null` or empty entries.
- [ ] 1.3 Change the defaults of the stored inlay hint flags in `RobotCodeProjectConfiguration` to `true`, and let `RobotCodeLanguageClient.createSettings()` return the mapper's tree instead of `asJson()`. Remove `asJson()` and its data classes once nothing uses them. Verify with a unit test that a state read from a `robotcodeSettings.xml` fragment of an earlier version keeps its header style and "Filter default language", and that a state without inlay hint entries yields `true` for both flags.

## 2. Settings pages

- [ ] 2.1 Turn the "Robot Framework" page into a `BoundSearchableConfigurable` with the existing id `dev.robotcode.robotcode4ij.projectsettings`. Its page holds a short description of what the RobotCode settings cover and that most project configuration lives in `robot.toml`; remove the work-in-progress row and the "Arguments" and "Mode" fields. Verify that the plugin builds (`./gradlew buildPlugin`) and, in task 3.2, that the page shows only the description.
- [ ] 2.2 Add the "Editing" page as a child `projectConfigurable` (`parentId` set to the parent's id, id `dev.robotcode.robotcode4ij.projectsettings.editing`, `nonDefaultProject="true"`): group "Completion" with "Filter default language" and "Header style", and group "Inlay Hints" with "Parameter names" and "Namespaces" plus a comment that points to Settings | Editor | Inlay Hints. Applying the page restarts the language server through the debounced `Project.restartAll()`. Verify in task 3.2 that the page appears below "Robot Framework" and that Apply restarts the server once.
- [ ] 2.3 Put the display names, labels and comments of both pages into `messages/RobotCode.properties` and read them through `RobotCodeBundle`, as plain text or HTML without markdown syntax. The header style comment names both defaults (`*** {name} ***` from Robot Framework 6 on, `*** {name}s ***` before). Verify that every new key is used and that no page text contains backticks or underscores used as markdown.

## 3. Verification

- [ ] 3.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation or internal-API findings.
- [ ] 3.2 Check the behaviour in the headless PyCharm harness, in one session, with a test project that has `.venv/other.robot` calling a keyword from the project:
  - with an LSP trace, `workspace/configuration` answers `robotcode`, `robotcode.robot`, `robotcode.analysis`, `robotcode.analysis.cache`, `robotcode.analysis.robot`, `robotcode.analysis.diagnosticModifiers`, `robotcode.completion`, `robotcode.inlayHints`, `robotcode.robocop`, `robotcode.documentationServer` and `robotcode.experimental` with objects;
  - searching "Header Style" in the settings dialog finds the Editing page, and no page shows a work-in-progress notice or the "Arguments" and "Mode" fields;
  - in a project without stored RobotCode settings, `Should Be Equal    ${a}    ${b}` shows parameter name hints; after switching "Parameter names" off and applying, they are gone and namespace hints stay;
  - header style `*** {name}` plus Apply restarts the server, and a completed section header follows the style; after clearing the field, completion uses the default again;
  - with "Filter default language" on and `Language: German`, section header completion offers no English headers;
  - a project with a `robotcodeSettings.xml` from the current release keeps its values on the Editing page and in the payload;
  - Find Usages of the project keyword does not list `.venv/other.robot`, and no robotcode process listens on ports 3100-3199 after the server started;
  - `idea.log` gets no new SEVERE entries from RobotCode.
