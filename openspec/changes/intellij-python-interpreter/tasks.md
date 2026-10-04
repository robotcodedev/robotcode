# Tasks

## 1. One interpreter for the project

- [ ] 1.1 Add the interpreter choice: the module of the project folder when it has a `robot.toml` or `.robot.toml`; otherwise the module that contains Robot Framework suite or resource files (the one with the project folder among several, otherwise the first by module name); a module counts only with a Python SDK from `PythonSdkUtil.findPythonSdk`; then the project SDK, then the first module with a Python SDK. The result names the interpreter, the module if any, and the step. Verify with light platform tests on fixtures: two modules with Robot Framework files only in the second; a robot.toml in the project folder of the first module; Robot Framework files in two modules; no module SDK but a Python project SDK; no Python SDK at all.
- [ ] 1.2 Let the environment service compute the choice in a `smartReadAction`, keep it with the interpreter identity, compute it again on the workspace model changes it watches and when the project is marked as using Robot Framework, and log the interpreter and the step; replace `robotPythonSdk` with the cached choice. Verify with a light platform test that changing which module contains Robot Framework files and opening the first one changes the choice, and that `robotPythonSdk` has no callers left.
- [ ] 1.3 Use the choice as the default of the template that `RobotCodeRunConfigurationFactory` creates and of configurations from earlier versions: the chosen module with "use module SDK", or the project SDK as interpreter when the choice came from it. Verify with light platform tests that a new configuration in the two-module fixture gets the second module, and that a configuration that stores another module keeps it after a write and read.

## 2. Validation before a run

- [ ] 2.1 Override `checkConfiguration()` in `RobotCodeRunConfiguration`: call `super` first, then read the state of `getSdk()` from the environment service; no result requests a check and reports nothing; an unusable result gives a `RuntimeConfigurationError` with the result's text and a `Runnable` fix that opens the configurable `com.jetbrains.python.configuration.PyActiveSdkModuleConfigurable`; a remote interpreter gives an error without a fix; a failed check gives a `RuntimeConfigurationWarning`. Verify with light platform tests that use a fake environment state: one test per result, a test that no process starts during validation, and a test that a configuration without an SDK yields only PyCharm's error.
- [ ] 2.2 Check the target in `checkConfiguration()`: an error naming each missing path of a "Files and folders" target after macro expansion relative to the project folder, and a warning naming the "Tests and suites" items that the current discovery model does not contain, only when discovery has a result. Put all validation texts into `messages/RobotCode.properties`. Verify with light platform tests for a missing path, an existing path, a stale item, a known item, and no discovery result.

## 3. Verification

- [ ] 3.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation or internal-API findings.
- [ ] 3.2 Check the behaviour in the headless PyCharm harness (section 12 of the analysis notes), with the process log:
  - in a project with a second module that holds the Robot Framework files and an interpreter with Robot Framework, while the first module's interpreter has none, the language server and discovery start with the second module's interpreter, and idea.log names it and the step;
  - a new Robot Framework run configuration in that project shows the second module's interpreter;
  - a configuration whose interpreter has no Robot Framework does not start; the dialog shows the error, and its fix opens the Python Interpreter page;
  - a "Files and folders" target with `tests/gone.robot` shows an error naming it and does not start;
  - after renaming a test that a saved configuration selects and waiting for discovery, the editor warns about the item, and the configuration still starts;
  - opening a configuration whose interpreter was never checked shows the editor without delay, and the process log shows one check of that interpreter.
