# Tasks

## 1. Options

- [ ] 1.1 Add the properties of design.md to the RobotCode options class: robot arguments, variables, variable files, Robot Framework Python path, languages, include tags, exclude tags, output directory, mode (`INHERIT` default, `RPA`, `NORPA`) and dry run. Verify with a light platform test that `writeExternal`/`readExternal` and `clone()` keep every property, and that a configuration without them writes none of the new options into its element.

## 2. Arguments

- [ ] 2.1 Add the pure function that turns the options into the arguments after `--`: `--language` per language, `--rpa` or `--norpa` unless the mode is `INHERIT`, `--dryrun`, `-d`, `-P` per entry, `-V` per file, `-v name:value` per variable, `-i` per include tag, `-e` per exclude tag, then the robot arguments split with `ParametersListUtil`. Verify with a JUnit 4 table test: each option alone, all options in the launcher's order, unset values pass nothing, a quoted robot argument stays one argument, a variable value with a colon, and a Windows path with a drive letter and spaces.
- [ ] 2.2 Place the function's output in the run state after `--` and before the selection arguments and the target's paths, with the separator also when only these options are set. Verify with JUnit 4 tests of the assembled arguments for each target kind with and without options.

## 3. Macros

- [ ] 3.1 Expand macros at the start of each run in `buildPythonExecution`: the robot arguments with `ProgramParametersConfigurator.expandMacrosAndParseParameters`, and the output directory, variable files, Robot Framework Python path entries and the target's paths with `ProgramParametersConfigurator().expandPathAndMacros(value, module, project)`; keep the stored values unexpanded. Verify with a light platform test that `$ProjectFileDir$/out3` expands to the fixture project's folder plus `out3`, and that the stored value still contains the macro afterwards.

## 4. Editor

- [ ] 4.1 Add the fragments of design.md: "Robot arguments" shown by default with placeholder and macro support; behind "Modify options" in a "Robot Framework" group the variables table, the variable-file and Python-path lists with browse button and macro support, the output-directory field with macro support, the mode combo box, the language, include-tag and exclude-tag lists, and the dry-run tag; macro support on the target's paths; the comments on precedence and on the minimum Robot Framework version for languages; texts in `messages/RobotCode.properties`, no deprecated members. Verify that the compiler reports no deprecation warning for the new fragments and `./gradlew verifyPlugin` no internal API use, and in task 5.2 that the fields work and are shown again.

## 5. Verification

- [ ] 5.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation or internal-API findings.
- [ ] 5.2 Check the behaviour in the headless PyCharm harness (section 12 of the parity notes) with the process protocol, in the test project where one test has the tag `smoke`:
  - a configuration with the robot arguments `--loglevel DEBUG`, the include tag `smoke` and the variable `NAME:x` has all three on its command line after `--`; `output.xml` contains only the `smoke` test, and `Log    ${NAME}` writes `x`;
  - with the user's global `robot.toml` setting `output-dir = "results"`, the output directory `$ProjectFileDir$/out3` puts the output files into `out3`;
  - dry run on passes `--dryrun`; mode "RPA" passes `--rpa`, "Inherit" passes neither flag;
  - reopening the editor shows the same values and the same fragments enabled through "Modify options";
  - `idea.log` gets no new SEVERE entries from RobotCode.
