# Design

## Context

See proposal.md for the motivation. The state that shapes the approach:

- **Builds on a planned change.** The Robot Framework settings node, its Editing page and the settings mapper come from the planned change that introduced the `intellij-settings` capability; it is not implemented yet. This design builds on its planned design: a parent configurable with the id `dev.robotcode.robotcode4ij.projectsettings`, child pages registered with that `parentId`, a typed settings model with VS Code's key names and defaults, a pure mapper that `RobotCodeLanguageClient.createSettings()` returns, stored values copied into the tree only for settings that have a control, and the shared state `RobotCodeProjectConfiguration` (`@State(name = "ProjectSettings")`, storage `robotcodeSettings.xml`). Today the code still has the stub page.
- **Initialization options:** `RobotCodeLanguageServer` leaves `getInitializationOptions` commented out, so `initialize` carries none. LSP4IJ 0.21.0 calls `StreamConnectionProvider.getInitializationOptions(rootUri)`, a default method without API status annotations, when it builds the `initialize` request.
- **What the server does with them:** `RobotLanguageServerProtocol._on_initialize` writes `env` into `os.environ` and puts `pythonPath` on `sys.path` before it checks Robot Framework. The workspace part keeps `settings` as the store for configuration reads made on the server's own thread, and `workspace/didChangeConfiguration` replaces it. `DocumentsCachePart.calc_cache_path` uses `storageUri` as the cache base only when `robotcode.analysis.cache.saveLocation` is `workspaceStorage` (the default) and `storageUri` is present; otherwise it uses the workspace folder. The server then writes `.robotcode_cache/<python>/<robot>` below that base. This override ignores `ROBOTCODE_CACHE_DIR`. `robotcode analyze` uses `<root>/.robotcode_cache` unless `ROBOTCODE_CACHE_DIR` or `cache-dir` in `robot.toml` say otherwise, so today the IntelliJ server and `robotcode analyze` share that folder.
- **Combination with `robot.toml`:** the server appends the settings' library search order, cache lists, diagnostic modifiers and exclude patterns to those of `[tool.robotcode-analyze]`; a library load timeout from the settings wins over `robot.toml`; the semantic model is on when either side enables it. The server never reads the client value of `analysis.cache.cacheNamespaces`; only `robot.toml` controls it.
- **Robocop:** `enabled` gates only Robocop's lint diagnostics; formatting is registered independently. The server resolves `configFile` with `Path(...)` relative to its working directory and shows an error message when the file does not exist. The Robocop configuration is cached per workspace folder for the server's lifetime.
- **Diagnostic levels:** `RobotDiagnosticsFeature` maps both `DiagnosticSeverity.Information` and `Hint` to `HighlightSeverity.INFORMATION`, overriding LSP4IJ's default `WEAK_WARNING` for both. `LSPDiagnosticFeature` is `@ApiStatus.Experimental` in LSP4IJ 0.21.0 and already in use.
- **How PyCharm 2026.1 shows these levels** (read from the platform bytecode, question Q4 of the parity notes): the Problems view's file tab lists highlights whose severity is above `TEXT_ATTRIBUTES` (11), so `WEAK_WARNING` (200) is listed and `INFORMATION` (10) is not. The editor's hover popup looks up highlights from `INFORMATION - 2` on, so the message of an `INFORMATION` highlight appears on hover. The error-stripe mark of an `INFORMATION` highlight comes from the colour scheme's information attributes. LSP4IJ adds the highlight types for the Unnecessary and Deprecated tags at every level.
- **Restart on Apply:** the planned Editing page restarts the server on Apply with `langServerManager.restart()`. `restartAll()` already offers a debounced restart (500 ms) that restarts the server and refreshes discovery in the background; the config-file listener and the startup activity use it.
- **UI API:** in 2026.1, `Row.expandableTextField(parser, joiner)`, `comboBox`, `checkBox` and `intTextField` carry no API status annotations. Every `Row.textFieldWithBrowseButton` overload is `@ApiStatus.Experimental` except one that is deprecated at level ERROR; `TextFieldWithBrowseButton` with `addBrowseFolderListener(Project, FileChooserDescriptor)` and `FileChooserDescriptorFactory.singleFile()` are unannotated.

## Goals / Non-Goals

**Goals:**

- Every analysis, diagnostics, workspace, experimental and Robocop setting that VS Code offers and the server reads can be changed in IntelliJ, through the same mapper as the Editing settings.
- The server gets the initialization options VS Code sends that it uses, built from the same tree as the configuration answers.
- The four LSP severities map to IntelliJ levels that keep Information and Hint apart.

**Non-Goals:**

- A UI for `analysis.cache.cacheNamespaces`, which the server does not read from the client.
- Excluding `.robotcode_cache` from indexing when the project folder is chosen. The default location avoids the problem; users who share the cache with command-line runs can mark the folder as excluded.
- Setting `ROBOTCODE_CACHE_DIR` for the IDE's terminal, which needs the experimental terminal customizer API of 2026.1.
- Values for `robotcode.robot.pythonPath` and `robotcode.robot.env`; the initialization options pass on whatever the settings tree holds.

## Decisions

### Three child pages: Analysis, Diagnostics, Robocop

The settings go onto three child pages of the Robot Framework node, built like the Editing page with the Kotlin UI DSL and registered with `parentId="dev.robotcode.robotcode4ij.projectsettings"` and the ids `dev.robotcode.robotcode4ij.projectsettings.analysis`, `.diagnostics` and `.robocop`. They hold only shared settings, so they take the Editing page's `nonDefaultProject` value and its handling of the default project in `apply()`; the planned profiles change offers such pages under Settings for New Projects, and whichever of the two lands later follows the other.

- **Diagnostics:** group "Diagnostics" with diagnostic mode, progress mode and find unused references; group "Diagnostic modifiers" with the five lists and the text on how each level is shown.
- **Analysis:** group "References" with the references code lens; group "Libraries" with the global library search order and the library load timeout; group "Cache" with the cache location and the three cache lists, whose comment points to Tools | RobotCode | Clear Cache and Restart RobotCode Language Server for entries cached before a change; group "Workspace" with the exclude patterns; group "Experimental" with the semantic model.
- **Robocop:** the four Robocop settings.

Alternative: one Analysis page with all of these, as the parity notes first proposed. With seventeen settings it becomes as long as the single page the settings node was designed to avoid, and the diagnostic modifiers deserve their own place because their texts explain the IntelliJ levels.

### Stored in the shared project state, only when not default

The new values extend the shared state `RobotCodeProjectConfiguration` in `robotcodeSettings.xml`, as VS Code users commit these settings in `.vscode/settings.json`. `BaseState` writes only values that differ from their defaults, so untouched projects keep following VS Code's defaults.

- **Lists** are stored as lists of strings. The list fields are expandable text fields that show one entry per line when expanded; entries are trimmed, and blank entries are dropped before they are stored.
- **Exclude patterns** default to VS Code's seven patterns. An emptied list is stored as an empty list, so it differs from the default and stays empty after a reload.
- **Library load timeout** is stored as an integer where 0 means "not set"; the page accepts 1 to 3600 or an empty field.
- **Enums** (diagnostic mode, progress mode, cache location) are stored as their exact server strings.
- **Robocop configuration file** is stored as an absolute path; a relative input is resolved against the project folder. The page validates that the file exists.

Alternative: a separate state component per page. It adds storage names without a user-visible benefit; one shared file stays the place for the project's RobotCode settings.

### The mapper copies the new values

The mapper of the settings tree copies each new stored value into its section: `analysis` (diagnostic mode, progress mode, find unused references, references code lens), `analysis.diagnosticModifiers`, `analysis.robot` (search order; `loadLibraryTimeout` only when set), `analysis.cache` (save location and the three lists), `workspace.excludePatterns`, `experimental.semanticModel` and `robocop` (`configFile` only when set). The types follow the server's parser: integers, the exact enum strings `openFilesOnly`/`workspace`, `off`/`simple`/`detailed`, `workspaceStorage`/`workspaceFolder`, and lists without blank entries.

### Initialization options from the same tree

A function next to the mapper builds the initialization options, and `RobotCodeLanguageServer.getInitializationOptions` returns its result:

- `storageUri`: the file URI of `Project.getProjectDataPath("robotcode")`, the platform's per-project folder below the system directory (public and unannotated in 2026.1);
- `pythonPath` and `env`: `robotcode.robot.pythonPath` and `robotcode.robot.env` of the tree;
- `settings`: the tree itself.

`storageUri` is always sent, as VS Code does; the server chooses between it and the project folder by `saveLocation`. `documentationViewerLinks` is not sent, so the server keeps its default `false`, and `globalStorageUri` is not sent because the server does not use it. Keeping the function apart from the connection provider lets a light platform test check it without starting a process.

Alternatives:
- Sending `storageUri` only for `workspaceStorage` duplicates the server's decision.
- A hand-built folder such as `PathManager.getSystemDir()/robotcode/<location hash>` reimplements what `getProjectDataPath` provides; `getProjectDataPathRoot` is `@ApiStatus.Internal`.

### Information as weak warning, Hint as information

`RobotDiagnosticsFeature` maps `Information` to `HighlightSeverity.WEAK_WARNING`, LSP4IJ's default, and keeps `Hint` at `HighlightSeverity.INFORMATION`. With the thresholds read from the platform (see Context), Information diagnostics get the weak-warning look, an error-stripe mark and a Problems view entry, as VS Code's Information diagnostics get a squiggle and a Problems entry. Hints stay out of the Problems view, and their message appears on hover, close to VS Code's faint hint marks that the Problems panel does not list. The texts of the information and hint lists say this. The harness check confirms the rendering.

Alternatives:
- Both at `WEAK_WARNING`, LSP4IJ's default: the two levels look the same again.
- A RobotCode text-attributes key for hints: it needs default colours per scheme, and its error-stripe mark would make hints look like weak warnings.
- Both at `INFORMATION`, today's state: Information diagnostics stay out of the Problems view, so the information modifier means almost "ignore".

### One debounced restart per Apply

The Analysis, Diagnostics and Robocop pages, and the Editing page, request the restart through the existing debounced `restartAll()` instead of restarting synchronously in `apply()`. Pressing OK after changing several pages then restarts the server once. The debounced path also refreshes discovery, as a `robot.toml` change does today.

Alternative: each page restarts synchronously, as the Editing page was planned to. Two changed pages then restart the server twice in a row, and the second stop can reach a server that is still starting.

### Texts

The texts live in `messages/RobotCode.properties`, adapted from `package.json`, and fix the mistakes found there: the swapped descriptions of the two cache locations, the missing description for one of the three progress modes, the integer library load timeout, exclude patterns as `.gitignore`-style specs, and Robocop's `enabled` not affecting formatting.

## Risks / Trade-offs

- [`robotcode analyze` in a terminal no longer shares the server's cache by default] → The cache location text names the trade-off, and "Project folder" keeps the shared folder.
- [The first start after the update analyses the project with an empty cache] → A one-time cost, as after a cache clear; the old `<project>/.robotcode_cache` stays for command-line runs.
- [Information diagnostics become more visible: weak warnings and Problems view entries] → This matches VS Code and LSP4IJ's default; users can move codes to `hint` or `ignore`, and the texts say how.
- [The look of hints depends on the colour scheme's information attributes] → The spec and texts promise only what the platform decides: no Problems view entry, message on hover.
- [`LSPDiagnosticFeature` is `@ApiStatus.Experimental` in LSP4IJ] → The plugin already depends on it; a unit test pins the mapping, and `verifyPlugin` reports API changes.
- [A wrongly typed value breaks the whole `robotcode` section on the server] → Typed state, the timeout validation, blank-entry filtering and payload unit tests.
- [Refreshing discovery on every settings Apply runs one extra `discover`] → Accepted until restarts depend on what changed.

## Migration Plan

None. The new options are written only when they differ from their defaults, so existing `robotcodeSettings.xml` files keep working. Older plugin versions skip options they do not know (assumption: the XML serializer binds options by name, as for every `BaseState` component). Rollback means removing the new options; the defaults then apply again.
