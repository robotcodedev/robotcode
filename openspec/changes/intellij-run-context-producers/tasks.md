# Tasks

## 1. Caret

- [ ] 1.1 Add the pure function that maps a caret line to the enclosing test or task or to the file suite: the discovered test or task with the greatest start line at or above the caret, unless a section header row (first cell starts with `*`, space- or pipe-separated) lies in between. Use it in the producer for every element of a `RobotSuiteFile`, keeping the structure-view path. Verify with a JUnit 4 test on a fixture whose tests are followed by a `*** Keywords ***` section: caret on a test's name line, in its body, on an empty line between two tests, in the keyword after the tests, on line 1, on a header row, and in a `*** Testfälle ***` section of a file with `Language: de`.

## 2. Selections, fallback and results tree

- [ ] 2.1 Support multi-selection in the producer: read `PlatformCoreDataKeys.PSI_ELEMENT_ARRAY`, `CommonDataKeys.VIRTUAL_FILE_ARRAY` and `Location.DATA_KEYS` when `containsMultipleSelection()` is true, map each element to a discovered item or a path, drop duplicates and items whose parent is selected, and build a `SELECTION` or `PATHS` target as design.md says (no configuration for other mixes); compare the whole set in `isConfigurationFromContext`. Verify with a JUnit 4 test of the reduction (duplicates, a file inside a selected folder, a test inside a selected suite, order independence) and of the target choice.
- [ ] 2.2 Add the path fallback: a `RobotSuiteFile` or a folder with a `.robot` file at any depth that discovery does not know gets a `PATHS` target for its path; `__init__.robot` stands for its folder; reuse compares the path. Verify with a light platform test on a fixture with an undiscovered file and an undiscovered folder.
- [ ] 2.3 Return file and folder locations from `RobotSMTestLocator`: a `PsiDirectory` for a folder hint, the `PsiFile` for line 0, the file for a line beyond the end of the document, the leaf at the line start otherwise; keep the `robotcode://` URL. Verify with a light platform test of the four cases.

## 3. Ranking, names, templates

- [ ] 3.1 Return `true` from `isPreferredConfiguration`, and `true` from `shouldReplace` against configurations of other types when the context is a folder that discovery reports as a Robot Framework suite. Verify in task 5.2 that the Robot Framework configuration is listed first for `tests` and pytest's is still listed.
- [ ] 3.2 Store the item's own name in new selection entries, override `suggestedName()` with the names of design.md, call `setGeneratedName()` in the producer, and implement `RefactoringListenerProvider` so that renamed or moved paths of a `PATHS` target update the target and a generated name. Verify with a JUnit 4 test of the name for each target shape (including an entry without a stored name) and a light platform test that renaming a file of a `PATHS` target updates path and name, while a name the user set stays.
- [ ] 3.3 Keep producers to setting the target and the name only, for every new path in this change. Verify with a light platform test that a configuration created from context keeps an environment variable and the working directory set in the template.

## 4. Indexing

- [ ] 4.1 Make the line-marker contributor and the producer `DumbAware`, return `true` from `RobotCodeConfigurationType.isDumbAware()` and from the factory's `isEditableInDumbMode()`. Verify in task 5.2 with a queued dumb-mode task.

## 5. Verification

- [ ] 5.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation or internal-API findings.
- [ ] 5.2 Check the behaviour in the headless PyCharm harness (section 12 of the parity notes) with the process protocol, in the test project:
  - Ctrl+Shift+F10 in the body of "First Test Passes" runs only that test; in the body of "Build Greeting" and on line 1 it runs the file suite;
  - selecting `tests/sample.robot` and `tests/other.robot` and choosing Run starts one run with both, named "Robot: 2 items";
  - a folder-suite node and a file-suite node of the results tree offer Run and Jump to Source, and Run reruns that suite;
  - a `.robot` file outside the paths of `robot.toml` runs by path in "Robot <name>";
  - the run widget's "Current File" runs a Robot Framework configuration for the open suite file;
  - the Run submenu of `tests` lists the Robot Framework configuration first and still lists pytest's;
  - a Before launch task, "Allow multiple instances" and a working directory set in the template are present in a configuration created from the gutter;
  - while a dumb-mode task is queued, the run markers stay, a gutter run starts, and the run configuration dialog opens;
  - `idea.log` gets no new SEVERE entries from RobotCode.
