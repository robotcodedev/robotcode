# Tasks

## 1. Plugin

- [ ] 1.1 In `RobotCodeRunLineMarkerContributor`, drop every `ExecutorAction` whose executor is neither Run nor Debug from the gutter actions before `withProfileActions` places the profile actions. Add a platform test, with test items set through `setTestItemsForTests` as in `RobotCodeDiscoveryProblemMarkersTest`, that the run marker of a test and of a suite offers no executor action besides Run and Debug while the profile actions and the platform's extra actions stay; register a further executor for the test so that the check does not depend on the executors of the test IDE. Verify that the new test fails without the change, and run the full `./gradlew test` and `./gradlew verifyPlugin` (no new usages apart from LSP4IJ's experimental API).
- [ ] 1.2 Let `RobotCodeProfileRunner` take the executor `ConcurrencyExecutor` besides `Profiler` for Robot Framework run configurations, and reject a run with the message of its executor; add `run.concurrencyDiagram.notSupported` = "Robot Framework runs have no concurrency diagram." to `RobotCode.properties`. Add a platform test that the runner takes both executors for a Robot Framework run configuration and no other executor, and that `execute` rejects each with its message. Verify with the full `./gradlew test`.

## 2. Documentation

- [ ] 2.1 In `docs/src/content/docs/guides/pycharm/running-tests.mdx`, name the run marker's entries without PyCharm's Profile. Take the picture `running-gutter-menu` again in light and dark with its part of `playground/robotcode-demo/pycharm/guide-running.sh`, and let its alt text name the entries the menu shows. Mark finding J5 in `playground/pycharm-befunde.md` as resolved by this change. Verify that `npm run docs:build` passes.

## 3. Verification

- [ ] 3.1 In the UI-test PyCharm, before (plugin from HEAD) and after the change, on the test "Order Coffee" and on line 1 of its suite file: the run marker's menu, "Profile" and "Concurrency Diagram" under "More Run/Debug" in the editor's context menu, and `idea.log`. After the change, the menu shows Run, Debug, Run with Profile..., Debug with Profile... and Modify Run Configuration…; both entries of the context menu end with their message without a process and without an "IDE error occurred" notification. Record the results in design.md under a Verification section.

## Workflow follow-up

- Archive the change with `/opsx:archive` once it is implemented and committed.
