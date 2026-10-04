# Design

## Context

See proposal.md for the motivation.

**Builds on a planned change.** This change builds on `intellij-run-configuration-target`, which is planned but not implemented. From its design it takes the stored target (`NONE`, `PATHS` with paths, `SELECTION` with entries of kind, full name below the top-level suite, `relSource` and suite), the producer that writes `SELECTION` entries and compares targets by kind and name, the run configuration on `AbstractPythonRunConfiguration`, and the factory with its options class.

**Current plugin code** (checked on 2026-10-03):

- `RobotCodeRunConfigurationProducer` (a `LazyRunConfigurationProducer`) resolves only `context.psiLocation` or the source element through `RobotCodeTestManager.findTestItem(PsiElement)`. That maps a `PsiDirectory` and a `RobotSuiteFile` by URI, and any other element only if it starts at column 0 of a line on which a discovered test starts; line 0 is rejected. The Robot Framework PSI is flat (the file plus lexer leaves), so a caret inside a test body maps to nothing. `isPreferredConfiguration` returns `false`. Without a discovered item the producer creates nothing.
- `RobotCodeRunLineMarkerContributor`, the producer and `RobotCodeConfigurationType` do not declare themselves dumb-aware, and the factory keeps the default `isEditableInDumbMode() = false`.
- `RobotSMTestLocator` parses the `robotcode://` location hint, finds the file with `PsiManager.findFile` and returns the leaf at the start of the hinted line, without a bounds check. The converter builds the hint with line `lineno - 1`; suite events carry no `lineno`, so suites get line 0, and folder suites carry the folder as source, which `findFile` cannot resolve.
- Discovery items of tests carry only their start line (`range.start` equals `range.end`).

**Platform facts** (javap against PyCharm 2026.1):

- `ConfigurationContext.containsMultipleSelection()` and `getDataContext()` are public. The selection is in `PlatformCoreDataKeys.PSI_ELEMENT_ARRAY` and `CommonDataKeys.VIRTUAL_FILE_ARRAY` for the Project view and in `Location.DATA_KEYS` for the results tree; `getPsiLocation()` returns only the lead element.
- `PreferredProducerFind` sorts the configurations of a context with `ConfigurationFromContext.COMPARATOR`. A configuration whose producer's `isPreferredConfiguration` returns `false` ranks after one whose producer returns `true`; `shouldReplace` breaks ties between two preferred ones. In the strict lookup that context actions use to pick one configuration, configurations ranked after the first are dropped; the context menu lists all of them. With today's `false`, pytest's configuration ranks first for folders.
- `LocatableConfigurationBase.setGeneratedName()` sets the name to `suggestedName()`, which returns `null` unless the configuration overrides it.
- `RunLineMarkerContributor`, `RunConfigurationProducer` and `ConfigurationType` are `PossiblyDumbAware`; `RefactoringListenerProvider` and `RefactoringElementListener` are unannotated. PyCharm's own `PythonConfigurationFactoryBase` overrides `isEditableInDumbMode()`.
- Robot Framework treats every row whose first cell starts with `*` as a section header, whatever the language of the header.

## Goals / Non-Goals

**Goals:**

- Context runs from every place where IntelliJ users expect them, without waiting for the language server or for indexes.
- One target per context, built from the same stored model that saved configurations use.

**Non-Goals:**

- Rerunning failed tests, and running with a chosen profile.
- Run markers for tasks, and gutter states keyed by names instead of lines.
- A test explorer tool window.

## Decisions

### The caret maps to a test through discovery and section header rows

A pure function takes the document's lines, the start lines of the file's discovered tests and tasks, and the caret line. It returns the test or task with the greatest start line at or above the caret, unless a section header row lies between that line and the caret; otherwise it returns the file's suite. A header row is a line whose first cell starts with `*`, in the space-separated and in the pipe-separated format. The producer applies it to any element inside a `RobotSuiteFile`. Structure-view symbols keep their current path.

Alternatives:
- The last test whose start line is at or above the caret: it picks the last test while the caret is in a `*** Keywords ***` section that follows the tests.
- The language server's document symbols, which carry full ranges: an asynchronous request from the producer, and nothing without a running server.
- The TextMate scopes of the lexer leaves (`meta.section.testcases.robotframework`): they depend on the grammar knowing every translated header.

### Multi-selection becomes one target

When `containsMultipleSelection()` is true, the producer reads the selected elements from the data keys above, maps each to a discovered item, or to its path when discovery does not know it, and reduces the set: no duplicates, and no item whose parent folder or suite is also selected. If discovery knows every item, the target is `SELECTION`. If every item is a file or folder, the target is `PATHS`, with the paths of discovered files too. Any other mix creates no configuration. `isConfigurationFromContext` compares the whole set, independent of order.

### Results-tree suite nodes get file and folder locations

For a hint whose path is a folder, the locator returns a `PsiLocation` of the `PsiDirectory`. For line 0, which only suites get because a test cannot start on the first line of a suite file, it returns the `PsiFile`. For a line beyond the end of the document, it returns the file. The producer's folder and file branches then apply. The `robotcode://` URL stays unchanged, so the gutter states keep their keys.

Alternative: mapping a leaf at offset 0 to the file's suite in `findTestItem`. It covers file suites but not folder suites, and it also changes what the gutter marker of line 1 resolves to.

### Files that discovery does not know run by path

When `findTestItem` finds nothing for a `RobotSuiteFile`, or for a folder with a `.robot` file at any depth (found by walking the folder until the first match), the producer sets a `PATHS` target with that path. An `__init__.robot` file stands for its folder. Such a run passes the path to Robot Framework, which then ignores the paths of `robot.toml`, as VS Code's "Run Current File" does.

### Ranking against pytest

`isPreferredConfiguration` returns `true`, the platform default. `shouldReplace` returns `true` against configurations of other types when the context is a folder that discovery reports as a Robot Framework suite. The context menu still lists pytest's configuration; context actions that pick one configuration pick the Robot Framework one.

Alternative: keeping `false`. Folders then run as pytest tests by default, although discovery found Robot Framework suites in them.

### Names and renamed paths

`RobotCodeRunConfiguration.suggestedName()` derives the name from the target:
- "<Type> <name>" for one entry, where the type comes from the entry's kind and the name from the item's own name, which the entry now stores; older entries fall back to the last part of the full name;
- "Robot <name>" for one path;
- "Robot: <n> items" for several items;
- "Workspace <project>" for the project folder, as the producer names it today.

The producer calls `setGeneratedName()`; a name the user changed is kept. The configuration implements `RefactoringListenerProvider`: when a file or folder of a `PATHS` target is renamed or moved, the listener updates the path, and the name too if it was generated.

### Templates

Producers start from a copy of the template, which the platform makes, and set only the target and the name. Every other value comes from the template: interpreter, environment, working directory, Before launch tasks and "Allow multiple instances". The template stored as a project file is the IntelliJ counterpart of a committed VS Code launch configuration with purpose `default`.

### Availability while indexing

The marker contributor and the producer implement `DumbAware`, the configuration type returns `true` from `isDumbAware()`, and the factory returns `true` from `isEditableInDumbMode()`. None of them uses indexes: they read the discovery model, the document and the VFS.

## Risks / Trade-offs

- [Discovery lags behind edits by its debounce, about a second] → Right after an edit the caret may map to a neighbouring test or to the file suite; the next discovery fixes it, and the run's command line shows what was selected.
- [A selection that mixes results-tree tests with files that discovery does not know] → No configuration is created for it, and each part can be run on its own; a run combining paths and selections would need a target kind of its own.
- [Walking large folders for the fallback] → The walk stops at the first `.robot` file and runs only when discovery has no item for the folder.
- [Preferring Robot Framework configurations hides pytest's from context actions that pick one configuration] → Only for folders that discovery reports as Robot Framework suites; the context menu keeps both.
- [The Python base class's editor fragments while indexing] → PyCharm marks its own Python configurations editable while indexing; the harness checks the editor during indexing.

## Migration Plan

None. Existing configurations keep their target. Names generated by earlier versions stay; the platform treats them as generated only when they equal the new suggestion.
