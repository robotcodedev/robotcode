# Design

## Context

See proposal.md for the motivation. The current state that shapes the approach:

- **The settings page:** one project configurable, `RobotCodeProjectSettingsConfigurable`, a `BoundConfigurable("RobotCode")`. It is registered through a `ConfigurableProvider` under `language` (Languages & Frameworks) with the id `dev.robotcode.robotcode4ij.projectsettings`, the display name "Robot Framework" and `nonDefaultProject="true"`.
- **The stored state:** `RobotCodeProjectConfiguration` (`@State(name = "ProjectSettings")`, storage `robotcodeSettings.xml`) stores four values: filter default language, header style, and the two inlay hint flags with default `false`. Its `asJson()` builds a Gson tree that holds only `completion` (with data-class defaults, so the stored completion values are lost) and `inlayHints`.
- **How LSP4IJ answers:** `RobotCodeLanguageClient.createSettings()` returns that tree. LSP4IJ calls `createSettings()` on a pool thread for every item of a `workspace/configuration` request and walks the dotted section name through the returned tree; it never reads `scopeUri`. LSP4J's Gson drops `null` members of objects but writes `null` inside arrays.
- **How the server parses:** the server parses every section non-strictly: unknown keys are ignored and missing keys take its dataclass defaults. It rejects wrong types, unknown enum strings and non-string map values, though, and the `robotcode` root section is parsed into the whole `RobotCodeConfig`. So one bad value below `robot`, `workspace`, `analysis`, `documentationServer` or `inlayHints` breaks workspace loading.
- **Server defaults:** the server's defaults differ from VS Code's for `workspace.excludePatterns` (`[]` against seven patterns). The plugin overrides the inlay hint flags with `false`. `documentationServer.startOnDemand=false` makes the server start its HTTP server at initialization.
- **Apply:** applying the page calls `RobotCodeLanguageServerManager.restart()` directly. Config-file changes use the debounced `Project.restartAll()` instead, which restarts the server and runs discovery again.
- **Tests:** the plugin's tests are JUnit 4 tests under `intellij-client/src/test/kotlin/`.

## Goals / Non-Goals

**Goals:**

- One place in the plugin knows the keys, types and defaults of the settings the server receives.
- A page tree that later changes extend with their own sub-pages, without moving existing settings.
- Values stored by earlier versions keep working without a migration step.

**Non-Goals:**

- Answering `workspace/configuration` per section or per folder (no override of LSP4IJ's `configuration()`).
- Restarting the server only when a setting it needs a restart for changed.
- Generating the page texts from `package.json`, or checking the defaults against `package.json` automatically.

## Decisions

### One complete tree, built by a pure mapper

`createSettings()` returns the complete `robotcode` tree, built by a function of the stored settings that has no other inputs. The same tree serves `workspace/configuration` and `workspace/didChangeConfiguration`, as in VS Code, where the language client answers from the full configuration including the defaults.

Alternatives:
- Overriding LSP4IJ's `configuration()` or `findSettings()` to answer per section couples the plugin to LSP4IJ internals and gains nothing at project level.
- Sending only values that differ from the defaults falls into the default trap: the server's defaults are not VS Code's, as `workspace.excludePatterns` shows.

### A typed model with VS Code's defaults

The mapper uses one Kotlin data class per section, with VS Code's defaults as the property defaults and with VS Code's key names. Gson serializes it without `serializeNulls`, so optional values that are not set, such as `headerStyle`, `loadLibraryTimeout` and `robocop.configFile`, are left out.

- **Enums** are plain strings with the exact values the server parses: `openFilesOnly`, `off`, `workspaceStorage`, `default`.
- **Covered sections:** the model covers every setting VS Code offers in the sections the server reads: `robot`, `completion`, `inlayHints`, `analysis` with `cache`, `robot` and `diagnosticModifiers`, `robocop`, `workspace`, `documentationServer` and `experimental`.
- **Client-only settings** are not modelled: `debug`, `run`, `profiles`, `extraArgs`, `languageServer`, `testExplorer`, `python`, `disableExtension`, `editor` and `ai`.
- **Stored values** are copied in only for settings that have a control: completion and inlay hints. Every other key keeps its default until the change that adds its control.
- **Header style** is copied only when it is not blank. The stored value becomes `""` after the field is cleared, and the server would use `""` literally.
- **`documentationServer.startOnDemand`** is always `true`. IntelliJ has no documentation viewer, and the server still starts its HTTP server lazily when something needs a documentation URL.

Alternatives:
- A hand-built `JsonObject` is verbose and has no type safety.
- kotlinx.serialization, which the plugin uses for discovery results, would need a conversion, because LSP4IJ walks the object `createSettings()` returns with Gson.

### The stored inlay hint flags default to `true`

`BaseState` writes only values that differ from the default. Projects that never touched the flags therefore follow the new default, and a stored `true` stays `true`. Before, the default was `false`, so no project can have an explicit `false` stored. No migration step is needed.

### A parent node and an Editing page

The parent configurable keeps the id `dev.robotcode.robotcode4ij.projectsettings` under Languages & Frameworks and becomes a `BoundSearchableConfigurable`, an API without `ApiStatus` annotations in 2026.1. Its page holds a short description and no settings. The Editing page is a child `projectConfigurable` with `parentId` set to the parent's id and its own id `dev.robotcode.robotcode4ij.projectsettings.editing`. Both pages are built with the Kotlin UI DSL (`panel`, `group`, `row`, `rowComment`), without subclassing `Panel` or `Row`, which are `@NonExtendable`.

Later changes add their pages as further children: Analysis, Robocop, Run & Debug and Language Server. Settings that apply to the whole project, such as the profile selection, go onto the parent page.

Alternative: one page with collapsible groups for all VS Code categories becomes too long once all settings exist.

### Texts in the message bundle

The display names, labels and comments are hand-written in `messages/RobotCode.properties`, adapted from `package.json`, and use plain text or HTML instead of markdown. The header style comment names both server defaults.

Alternative: generating the texts from `package.json` at build time needs a markdown-to-HTML step, for a handful of texts per page.

### Apply keeps restarting the language server, through the debounced restart

The Editing page restarts the server on apply, as the page does today, but through the existing debounced `Project.restartAll()` instead of calling `RobotCodeLanguageServerManager.restart()` directly. That is the path that config-file changes already use: it restarts the server and runs discovery again. When several RobotCode pages are applied together, the debounce turns them into one restart. Later pages use the same call.

For completion and inlay hints, a `didChangeConfiguration` would be enough. Restarting only when it is needed belongs to a later change that knows every input of the server's command line.

## Risks / Trade-offs

- [VS Code changes a default later, and IntelliJ keeps the old one] → The test with the expected default tree names `package.json` as the source of its values, so a change to a default there has an obvious second place to update.
- [One wrongly typed value breaks the whole `robotcode` section on the server] → The typed model and the default-tree test pin the types. No free-text input reaches a typed field in this change.
- [Users who relied on having no inlay hints see them after the update] → A line in the release notes; they can be switched off on the Editing page or hidden in Settings | Editor | Inlay Hints.
- [The exclude patterns change which files the server loads] → This matches VS Code and goes into the release notes. The patterns become editable with the analysis settings.
- [A restart after every Apply also runs discovery again] → That is what config-file changes already do. Restarting only when needed comes later.

## Migration Plan

None. The format of `robotcodeSettings.xml` stays the same, and only the defaults of two values change (see the decision on the inlay hint flags). An older plugin version reads the file unchanged.

## Open Questions

- Does the settings search find the Editing page in a sandbox IDE that has no prebuilt searchable options? If it does not, check it with the built plugin, whose `buildSearchableOptions` step indexes the pages. That would change neither the approach nor the tasks.
