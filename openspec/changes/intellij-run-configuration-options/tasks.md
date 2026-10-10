# Tasks

## 1. Options

- [ ] 1.1 Add the properties of design.md to `RobotCodeRunConfigurationOptions`: robot arguments, variables, variable files, Robot Framework Python path, languages, include tags, exclude tags, output directory, mode (`INHERIT` default, `RPA`, `NORPA`) and dry run. Verify with a light platform test in `RobotCodeRunConfigurationPersistenceTest` that `writeExternal`/`readExternal` and `clone()` keep every property, and that a configuration without them writes none of the new options into its element.

## 2. Arguments

- [ ] 2.1 Add the pure function that turns the options into the arguments after `--`: `--language` per language, `--rpa` or `--norpa` unless the mode is `INHERIT`, `--dryrun`, `-d`, `-P` per entry, `-V` per file, `-v name:value` per variable, `-i` per include tag, `-e` per exclude tag, then the robot arguments split with `ParametersListUtil`. Verify with a JUnit 4 table test: each option alone, all options in the launcher's order, unset values pass nothing, a quoted robot argument stays one argument, a variable value with a colon, and a Windows path with a drive letter and spaces.
- [ ] 2.2 Place the function's output in `RobotCodeRunProfileState.buildPythonExecution` before `targetArguments`, so that it follows `--` and comes before the selection arguments and the target's paths, and `debugArguments` adds the separator also when only these options are set. Verify with JUnit 4 tests in `RobotCodeRunTargetTest` of the assembled arguments for each target kind with and without options.

## 3. Macros

- [ ] 3.1 Expand macros at the start of each run: the option-argument function and `targetArguments` take two expansions as parameters, one for paths (output directory, variable files, Robot Framework Python path entries and the target's paths) and one that expands and splits the robot arguments. `buildPythonExecution`, on the pooled thread of `startInBackground`, passes `ProgramParametersConfigurator().expandPathAndMacros(value, module, project)` and `ProgramParametersConfigurator.expandMacrosAndParseParameters`; the stored values stay unexpanded. Verify with JUnit 4 tests that pass simple replacements: the path values, and only those, go through the path expansion, the robot arguments through the other, and the options are unchanged afterwards. Task 5.2 checks PyCharm's expansion in real runs and that the run's data context reaches the pooled thread.

## 4. Editor

- [ ] 4.1 Add the fragments of design.md in `RobotCodeRunConfigurationEditor.customizeFragments`: "Robot arguments" shown by default below the target fragment, with placeholder and macro support; behind "Modify options" in a "Robot Framework" group the variables table, the variable-file and Python-path fields (`RawCommandLineEditor`, as in the target fragment) with an "Add Files or Folders..." button and macro support, the output-directory field with folder chooser and macro support, the mode combo box, the language, include-tag and exclude-tag fields, and the dry-run tag; macro support on the target's paths field; the comments on precedence and on the minimum Robot Framework version for languages; texts in `messages/RobotCode.properties`, no deprecated members. Verify in task 5.1 that the build reports no deprecation warning and no internal API use, and in task 5.2 that the fields work and are shown again.

## 5. Verification

- [ ] 5.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation or internal-API findings.
- [ ] 5.2 Check the behaviour in the headless PyCharm harness (section 12 of the parity notes) with the process protocol, in the test project where one test has the tag `smoke`:
  - a configuration with the robot arguments `--loglevel DEBUG`, the include tag `smoke` and the variable `NAME` with the value `x` has all three on its command line after `--`; `output.xml` contains only the `smoke` test, and `Log    ${NAME}` writes `x`;
  - with `output-dir = "results"` in the test project's `robot.toml`, the output directory `$ProjectFileDir$/out3` puts the output files into `out3`;
  - a run started from the Run action with the robot arguments `--metadata Dir:$ProjectFileDir$` passes the project folder in place of the macro;
  - dry run on passes `--dryrun`; mode "RPA" passes `--rpa`, "Inherit" passes neither flag;
  - reopening the editor shows the same values and the same fragments enabled through "Modify options";
  - `idea.log` gets no new SEVERE entries from RobotCode.
