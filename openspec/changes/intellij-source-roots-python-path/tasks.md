# Tasks

## 1. Settings, root collection and the Robot page

- [ ] 1.1 Add `robotAddContentRoots` and `robotAddSourceRoots` to `ProjectState`, each `property(defaultValue = true)`. Add the function that returns the root entries as the design describes:
  - `robotPythonModule` and its dependencies from `ModuleUtilCore.getDependencies`;
  - content roots before source roots, test source roots included;
  - local roots only, as absolute system-independent paths, each once;
  - computed in a read action, empty without a module or with both switches off.

  Verify with a new platform test class:
  - order for a module with a content root, a source root and a test source root;
  - a dependency's roots are included, those of an unrelated module are not;
  - each switch off removes its kind, and without a module the list is empty;
  - a root that is both content and source root appears once.

  Verify storage in the settings tests: with the defaults, `.idea/robotcodeSettings.xml` holds no entry for the switches; a switch turned off is stored as `false` and survives a reload.
- [ ] 1.2 Show both switches on `RobotCodeRobotConfigurable` right after "Python path", with the labels "Add content roots to the Python path" and "Add source roots to the Python path" and a row comment in `RobotCode.properties`. The comment says that they put the roots of the module whose interpreter RobotCode uses, and of the modules it depends on, on the Python path of the analysis, test discovery and runs, like PyCharm's Python run configurations, and points to `python-path` in `robot.toml` for runs on the command line. Verify with `RobotCodeSettingsPagesTest`:
  - the checkboxes follow "Python path" and are on by default;
  - Apply stores a switch that was turned off and publishes the settings change;
  - the comment contains the points above.
- [ ] 1.3 Mention the two switches in the "Robot" row of the settings table in `docs/src/content/docs/guides/pycharm/configuration.mdx`. That page comes from a parallel session; if it is not committed when this task starts, agree with the maintainer when to add the mention. Verify with `npm run docs:build`.

## 2. Roots in the analysis, discovery and runs

- [ ] 2.1 Append the root entries to `robot.pythonPath` in `toJsonTree(project)`, after the entries of "Python path", and leave `toJsonTree(state)` unchanged; the initialization options take them from the tree. Verify:
  - in `RobotCodeServerSettingsTest`: with "Python path" `libs`, a content root `/p` and a source root `/p/src`, the tree holds `["libs", "/p", "/p/src"]`; with both switches off it holds `["libs"]`;
  - in `RobotCodeInitializationOptionsTest`: a project whose only content root is the project folder carries `pythonPath` with that folder; with both switches off and no "Python path", `pythonPath` is empty.
- [ ] 2.2 Pass the root entries to `discoveryRobotArguments` for the full discovery and the discovery of a single suite file, as `-P` after the entries of "Python path". Verify in `RobotCodeRobotArgumentsTest`:
  - with both switches off, the arguments contain `--rpa -P libs --language de --exclude wip`;
  - with the defaults they contain `-P libs -P /p -P /p/src`.
- [ ] 2.3 Pass the root entries to `mergeRobotOptions` and build the run's Python path as page entries, roots, configuration entries. Leave `applyRobotCodeDefaults()` as it is. Verify:
  - in `RobotCodeRobotOptionsMergeTest`: "Python path" `libs`, the roots `/p` and `/p/src` and the configuration's `more_libs` give `-P libs -P /p -P /p/src -P more_libs`;
  - in the run configuration tests: a new configuration still has PyCharm's "Add content roots to PYTHONPATH" and "Add source roots to PYTHONPATH" off.

## 3. Root changes

- [ ] 3.1 Register a project listener on `ModuleRootListener.TOPIC` in `plugin.xml` whose `rootsChanged` calls `publishRobotCodeSettingsChanged()`. Verify with a platform test:
  - adding a source root to the interpreter module changes `serverSnapshot()` and `discoverySnapshot()`, and the restart decision asks for a restart and a discovery;
  - marking a folder inside a content root as excluded leaves both snapshots equal, and the decision asks for nothing.

## 4. Verification

- [ ] 4.1 Run `./gradlew test` and `./gradlew verifyPlugin` in `intellij-client/`; both pass. Check in the headless PyCharm (`reference_intellij_headless_harness`), with a project whose suite imports `mylib` from the folder `src` and `common.resource` from `tests/resources`:
  - with `src` unmarked, the import of `mylib` is unresolved;
  - after marking `src` as Sources Root, the language server restarts, discovery runs again, and the import resolves without an IDE restart;
  - after marking `tests/resources` as Test Sources, `common.resource` resolves;
  - a gutter run of a test passes `-P` with the roots;
  - turning off "Add source roots to the Python path" makes the import unresolved again;
  - marking a folder as Excluded restarts nothing.

## Workflow follow-up

- The implementation commit closes GitHub #430 with `Fixes #430`; the comment of 2026-10-17 already announced the option.
