# Tasks

## 1. VS Code prerequisite (#656)

- [ ] 1.1 Skip this task if `vscode-client/extension/debugmanager.ts` already passes `--runemptysuite`. Otherwise, in `DebugManager.runTests()`, add `--runemptysuite` in the branch that adds `-I` (parse-include support and at least one `relSource`). Verify that `npm run lint` and `npm run compile` pass, and that the argument list the changed function produces for a single test in a project with `paths = ["folder1", "folder2"]` runs that test with Robot Framework 7.5 on the command line (`robotcode -dp . debug --no-debug --no-wait-for-client --tcp <port> -- <arguments>`), exit code 0.

## 2. Selection-argument builder

- [ ] 2.1 Add the pure selection-argument builder in `execution/` with its two steps from design.md. Resolve: the selected discovery items plus the top-level items of the current model become entries (kind, full name, suite name and `relSource` for `-s` and `-I`, top-level suite name); for a test or task the suite is its file suite found by URI in the current model, for a suite the suite itself; an empty selection, the workspace item or the top-level suite resolve to nothing. Emit: `--runemptysuite` first whenever `-I` is emitted, `-I` per distinct `relSource` only with parse-include support, `-N` with the top-level suite, `-s` per distinct suite name, both `-I` and `-s` escaped with `escapeRobotGlob()`, and `-bl` per item, unescaped. Verify with a JUnit 4 table test on a discovery fixture: one test, one file suite, one folder suite, a test in a nested folder, items from two files, the workspace item and the top-level suite (no arguments), parse-include off (neither `-I` nor `--runemptysuite`).
- [ ] 2.2 Cover the edge cases with further JUnit 4 cases and verify they pass: glob characters in a file name; a test whose file suite is no longer in the model (`-I` from the test, no `-s`, `-bl` kept); the model of a project with several paths (top-level suite without `relSource`); a `relSource` outside the project root as an absolute Windows path with a drive letter and backslashes, passed unchanged apart from glob escaping.

## 3. Run command line

- [ ] 3.1 Use the builder in `RobotCodeRunProfileState.startProcess()`: keep `-dp .` and `--no-debug`, move `--tcp <port>` before the separator, and append `--` plus the builder's output only when the output is not empty. Extract the assembly of the arguments after `debug` into a pure function and verify with a JUnit 4 test that a Run of one test yields `debug --no-debug --tcp <port> -- --runemptysuite -I ... -N ... -s ... -bl ...`, that a Debug of the whole project yields no `--`, and that the default port 6612 yields no `--tcp`.

## 4. Verification

- [ ] 4.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation or internal-API findings.
- [ ] 4.2 Check the behaviour in the headless PyCharm harness (section 12 of the parity notes) with Robot Framework 7.5 from the hatch environment `test.rf75` and the process protocol recording every robotcode command line:
  - in the test project with an extra `tests/broken.robot` that sets `Test Template` twice, a gutter run of "First Test Passes" shows no error from `broken.robot`, and the protocol shows `--`, `--runemptysuite`, `-I tests/sample.robot`, `-N`, `-s` and `-bl`;
  - a Debug of the same test stops at a breakpoint inside it;
  - a Project-view run of the folder `tests` passes `-I tests` and runs only its tests;
  - a Project-view run of the project root folder passes no `--` and runs all tests;
  - in a copy of the #656 project (`paths = ["folder1", "folder2"]`), a gutter run of "My Amazing Testcase" passes;
  - `idea.log` gets no new SEVERE entries from RobotCode.
