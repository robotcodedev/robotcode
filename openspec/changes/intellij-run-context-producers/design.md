# Design

## Context

See proposal.md for the motivation.

**Builds on implemented changes.** `intellij-run-configuration-target` and `intellij-run-configuration-options` are implemented. This change builds on their code: the run configuration on `AbstractPythonRunConfiguration` with the options class `RobotCodeRunConfigurationOptions`; its target of two kinds, `PATHS` (given files and folders; an empty list runs the paths of `robot.toml` or the project folder) and `SELECTION` (entries with kind, full name, suite and paths as discovery reports them, plus the top-level suite); `setContextTarget`, which writes the target of a gutter or context run, and `targetKey`, which compares targets by kind and full name or by path; `pathRelativeTo`, with which the editor's add buttons store paths relative to the working directory; and the Robot Framework options of a configuration, which the template carries like every other value.

**Current plugin code** (checked on 2026-10-03, re-checked on 2026-10-11):

- `RobotCodeRunConfigurationProducer` (a `LazyRunConfigurationProducer`) resolves only `context.psiLocation` or the source element through `RobotCodeTestManager.findTestItem(PsiElement)`. That maps a `PsiDirectory` and a `RobotSuiteFile` by URI, and any other element only if it starts at column 0 of a line on which a discovered test starts; line 0 is rejected. The Robot Framework PSI is flat (the file plus lexer leaves), so a caret inside a test body maps to nothing. `isPreferredConfiguration` returns `false`. Without a discovered item the producer creates nothing. It also creates nothing while RobotCode is switched off for the project (`isRobotCodeDisabled`), maps structure-view symbols (`DocumentSymbolData`) to their element, names the configuration "<Type> <name>" from the item's type and own name, and writes the target with `setContextTarget`.
- `RobotCodeRunLineMarkerContributor`, `RobotCodeDiscoveryProblemLineMarkerProvider` (the error marker on line 1 of a file with discovery problems), the producer and `RobotCodeConfigurationType` do not declare themselves dumb-aware, and the factory keeps the default `isEditableInDumbMode() = false`.
- `RobotSMTestLocator` parses the `robotcode://` location hint, finds the file with `PsiManager.findFile` and returns the leaf at the start of the hinted line, without a bounds check. The converter builds the hint with line `lineno - 1`; suite events carry no `lineno`, so suites get line 0, and folder suites carry the folder as source, which `findFile` cannot resolve.
- Discovery items of tests carry only their start line (`range.start` equals `range.end`).

**Platform facts** (javap against PyCharm 2026.1; the data keys, `containsMultipleSelection`, `suggestedName`/`setGeneratedName`/`isGeneratedName`, `RefactoringListenerProvider`, `isPreferredConfiguration`/`shouldReplace` and `isEditableInDumbMode` re-checked against 263 on 2026-10-11; the strict lookup, the Run action, PyCharm's pytest producer and how results ask their locator checked against PyCharm 2026.1.5 and the 271 sources on 2026-10-11):

- `ConfigurationContext.containsMultipleSelection()` and `getDataContext()` are public. The selection is in `PlatformCoreDataKeys.PSI_ELEMENT_ARRAY` and `CommonDataKeys.VIRTUAL_FILE_ARRAY` for the Project view and in `Location.DATA_KEYS` for the results tree; `getPsiLocation()` returns only the lead element.
- `PreferredProducerFind` sorts the configurations of a context with `ConfigurationFromContext.COMPARATOR`. Two configurations whose producers' `isPreferredConfiguration` both return `false` count as equal; otherwise one whose producer returns `false` ranks after the other, and `shouldReplace` decides between two preferred ones. The strict lookup, which the context menu's Run, Ctrl+Shift+F10 and the gutter use, then drops every configuration that ranks after the one before it; equal ones stay, in the order in which the producers are registered. With several configurations left, the context menu shows them in a Run submenu and Ctrl+Shift+F10 runs the first. PyCharm's `PyTestsConfigurationProducer` prefers its configurations only to plain Python run configurations. With today's `false`, pytest's configuration comes first for folders, because PyCharm registers its producer earlier.
- `LocatableConfigurationBase.setGeneratedName()` sets the name to `suggestedName()`, which returns `null` unless the configuration overrides it, and sets a stored flag. `isGeneratedName()` is true while that flag is on and `suggestedName()` is not `null`; it does not compare the current name with the suggestion.
- `RunLineMarkerContributor`, `RunConfigurationProducer` and `ConfigurationType` are `PossiblyDumbAware`; `RefactoringListenerProvider` and `RefactoringElementListener` are unannotated. PyCharm's own `PythonConfigurationFactoryBase` overrides `isEditableInDumbMode()`.
- A results-tree node asks its locator for its location with the location hint and the metainfo of its test event; the metainfo arrives in the `getLocation` overload that takes it. While the IDE indexes, the node asks only a `DumbAware` locator, and it keeps a location until the locator's `getLocationCacheModificationTracker` changes, by default the PSI modification count.
- Robot Framework treats every row whose first cell starts with `*` as a section header, whatever the language of the header.

## Goals / Non-Goals

**Goals:**

- Context runs from every place where IntelliJ users expect them, without waiting for the language server or for indexes.
- One target per context, built from the same stored model that saved configurations use.

**Non-Goals:**

- Rerunning failed tests, and running with a chosen profile.
- Gutter states keyed by names instead of lines.
- A test explorer tool window.

## Decisions

### The caret maps to a test through discovery and section header rows

A pure function takes the document's lines, the start lines of the file's discovered tests and tasks, and the caret line. It returns the test or task with the greatest start line at or above the caret, unless a section header row lies between that line and the caret; otherwise it returns the file's suite. A header row is a line whose first cell starts with `*`, in the space-separated and in the pipe-separated format. The producer applies it to any element inside a `RobotSuiteFile`. Structure-view symbols keep their current path.

Alternatives:
- The last test whose start line is at or above the caret: it picks the last test while the caret is in a `*** Keywords ***` section that follows the tests.
- The language server's document symbols, which carry full ranges: an asynchronous request from the producer, and nothing without a running server.
- The TextMate scopes of the lexer leaves (`meta.section.testcases.robotframework`): they depend on the grammar knowing every translated header.

### Multi-selection becomes one target

When `containsMultipleSelection()` is true, the producer reads the selected elements from the data keys above, maps each to a discovered item, or to its path when discovery does not know it, and reduces the set: no duplicates, and no item whose parent folder or suite is also selected. If discovery knows every item, the target is `SELECTION`. If every item is a file or folder, the target is `PATHS`, with the paths of discovered files too, stored relative to the working directory like the fallback below. Any other mix creates no configuration. `isConfigurationFromContext` compares the whole set, independent of order.

### Results-tree nodes get file, folder and test locations

For a hint whose path is a folder, the locator returns a `PsiLocation` of the `PsiDirectory`. For line 0, which only suites get because a test cannot start on the first line of a suite file, it returns the `PsiFile`. For a line beyond the end of the document, it returns the file. The producer's folder and file branches then apply. The `robotcode://` URL stays unchanged, so the gutter states keep their keys.

A result keeps the line of its run, and the producer runs the test whose body holds a line, so after lines were added or removed above a test, a result would run the test that now holds its old line (review of 2026-10-11, reproduced in the harness). The test events converter therefore sends the full name of each test, task and suite as metainfo, and the locator takes the line on which discovery now sees the test or task with that name in the file; the line of the run counts only when discovery does not know the name, for example after a run of explicit paths. The locator implements `DumbAware`, since it reads only files, documents and the discovery result, and returns `ModificationTracker.EVER_CHANGED` as its cache tracker, since the location also depends on the discovery result, which changes after an edit without a PSI change.

Alternatives:
- Mapping a leaf at offset 0 to the file's suite in `findTestItem`: it covers file suites but not folder suites, and it also changes what the gutter marker of line 1 resolves to.
- Using the line of the run only while a discovered test still starts on it, and the file otherwise: no other test runs, but the whole suite runs instead of the moved test.

### Files that discovery does not know run by path

When `findTestItem` finds nothing for a `RobotSuiteFile`, or for a folder with a `.robot` file at any depth (found by walking the folder until the first match, past hidden, ignored and excluded folders), the producer sets a `PATHS` target with that path. An `__init__.robot` file stands for its folder. Such a run passes the path to Robot Framework, which then ignores the paths of `robot.toml`, as VS Code's "Run Current File" does. The path is stored relative to the working directory of the template with `pathRelativeTo`, as the editor's add buttons store chosen paths (request of 2026-10-10); a path outside it stays absolute. The platform evaluates a context once for every existing configuration, so the result of the walk is cached per folder until files or folders are added, removed or renamed or the project's roots change.

### Ranking against pytest

`isPreferredConfiguration` keeps returning `false`, and `shouldReplace` keeps the platform default `false`, so a Robot Framework configuration and pytest's count as equal and both stay. `plugin.xml` registers the producer with `order="first"`, so the Robot Framework configuration comes first: the Run submenu lists it first, and Ctrl+Shift+F10 on the folder runs it. The order holds for every folder for which the producer creates a configuration, including folders outside the paths of `robot.toml` that hold `.robot` files.

Alternatives:
- `shouldReplace` returning `true` for folders that discovery reports, or `isPreferredConfiguration` returning `true`: the Robot Framework configuration ranks above pytest's, and the strict lookup drops pytest's from the context menu, as the harness showed on 2026-10-11.
- Keeping `false` without the order: folders run as pytest tests by default, although discovery found Robot Framework suites in them.

### Names and renamed paths

`RobotCodeRunConfiguration.suggestedName()` derives the name from the target:
- "<Type> <name>" for one entry, where the type comes from the entry's kind and the name from the item's own name, which the entry now stores; older entries fall back to the last part of the full name;
- "Robot <name>" for one path;
- "Robot: <n> items" for several items;
- "Workspace <project>" for the project folder, as the producer names it today.

The producer calls `setGeneratedName()`; a name the user changed is kept. The configuration implements `RefactoringListenerProvider`: when a file or folder of a `PATHS` target is renamed or moved, the listener updates the path, and the name too if it was generated.

### Templates

Producers start from a copy of the template, which the platform makes, and set only the target and the name. Every other value comes from the template: interpreter, environment, working directory, Before launch tasks and "Allow multiple instances". This includes the Robot Framework options of the template, such as robot arguments, variables, variable files and tags, which then apply to every gutter and context run. The template stored as a project file is the IntelliJ counterpart of a committed VS Code launch configuration with purpose `default`.

### Availability while indexing

The marker contributor, the marker of discovery problems, the producer and the locator of results implement `DumbAware`, the configuration type returns `true` from `isDumbAware()`, and the factory returns `true` from `isEditableInDumbMode()`. None of them uses indexes: they read the discovery model, the document and the VFS.

## Risks / Trade-offs

- [Discovery lags behind edits by its debounce, about a second] → Right after an edit the caret may map to a neighbouring test or to the file suite; the next discovery fixes it, and the run's command line shows what was selected.
- [A selection that mixes results-tree tests with files that discovery does not know] → No configuration is created for it, and each part can be run on its own; a run combining paths and selections would need a target kind of its own.
- [Walking large folders for the fallback] → The walk stops at the first `.robot` file, skips hidden, ignored and excluded folders and runs only when discovery has no item for the folder; its result is cached until files, folders or the project's roots change.
- [The registration order puts Robot Framework first for every folder that gets a Robot Framework configuration] → A folder outside the paths of `robot.toml` with `.robot` files next to pytest tests also runs as Robot Framework suites with Ctrl+Shift+F10; pytest's configuration stays in the Run submenu. Ranking first only for folders that discovery reports would drop pytest's from the menu.
- [With `false`, a producer that prefers its configurations to all others ranks above the Robot Framework configuration, which the strict lookup then drops] → As before this change; PyCharm's pytest producer does not prefer its configurations to ours.
- [The Python base class's editor fragments while indexing] → PyCharm marks its own Python configurations editable while indexing; the harness checks the editor during indexing.

## Migration Plan

None. Existing configurations keep their target. Names that earlier versions set stay: they lack the stored flag that `setGeneratedName()` sets, so the platform treats them as chosen by the user.
