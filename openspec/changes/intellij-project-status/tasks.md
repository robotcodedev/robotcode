# Tasks

## 1. Switch per project

- [ ] 1.1 Add `enabled` (default `true`) to `RobotCodePersonalConfiguration` and the checkbox "Enable RobotCode for this project" to the "General" group of the "Robot Framework" page, left out for the default project; put the texts into `messages/RobotCode.properties`. Verify with a JUnit 4 test that the value round-trips through the XML serializer of the workspace component and is not part of `RobotCodeProjectConfiguration`, and with a light platform test that the default project's page has no such row.
- [ ] 1.2 Make the factory's `isEnabled` "switch on, not disabled for this session, interpreter usable" without side effects; let `setEnabled(true)` turn the switch on and clear the session flag, and `setEnabled(false)` set only the session flag; clear the flag on Restart, Clear Cache and Restart and Retry; stop the server in the plugin with `StopOptions().setWillDisable(false)`. Verify with JUnit 4 tests over all combinations of switch, session flag and environment result, and that `setEnabled(false)` leaves the stored switch on.
- [ ] 1.3 Act on a change of the switch: off stops the server, cancels discovery, empties the model, restarts the daemon and refreshes banners and widget; on starts as at project opening. Let the producer and the banner provider return nothing while the switch is off. Verify with light platform tests that the producer creates no configuration and the banner provider returns no panel while off, and in task 5.2.

## 2. Banner

- [ ] 2.1 Add the banner's actions: "Configure Python Interpreter..." (opens the configurable `com.jetbrains.python.configuration.PyActiveSdkModuleConfigurable` through `ShowSettingsUtil.showSettingsDialog(project, predicate, null)`), "Retry" (resets the environment state and restarts), "Disable RobotCode for This Project", and a close action that hides the banner for the project until the IDE restarts; add the pip command with the interpreter path for a missing or old Robot Framework. Verify with light platform tests that the panel has the actions, that the text contains the pip command with the interpreter path for both results, and that a dismissed project gets no panel.

## 3. Status bar widget and actions

- [ ] 3.1 Declare `@JsonRequest("robot/projectInfo")` in `RobotCodeServerApi`, fetch it on a project service's injected scope when the server reaches `started`, keep it until the server stops, and refresh the widget. Verify with a JUnit 4 test that decodes a `projectInfo` answer with and without `robocopVersionString`, and in task 5.2.
- [ ] 3.2 Rework the widget: `getId()` equal to the `plugin.xml` id, `MultipleTextValuesPresentation` with the texts for running, unusable interpreter and switched off, the tooltip, `getPopup()` over the RobotCode action group, `isAvailable` from the "uses Robot Framework" mark with `StatusBarWidgetsManager.updateWidget(factory)` when it changes, and `StatusBar.updateWidget(id)` on changes of the state, the project information, the profile selection and the switch. Verify with JUnit 4 tests of the text and tooltip for each state (including "RF 7.5 · dev" and no profiles), and a test that the factory id equals the id in `plugin.xml`.
- [ ] 3.3 Add "Configure Python Interpreter...", "Show Language Server Log" (activates the "Language Servers" tool window) and "Enable RobotCode for This Project" (visible only while off) to the RobotCode group, with `update()` on the background thread. Verify with light platform tests of the actions' enablement and visibility.

## 4. Code action commands

- [ ] 4.1 Register an `LSPCommandAction` subclass under the id `_robotcode.codeActionShowDocumentSelectAndRename`: read URI, range and the optional `rename` flag (default `true`), and in `invokeLater` commit the documents, open the file, select the range from end to start, and start the Rename action through `ActionManager.tryToExecute` when `rename` is set. Verify with a JUnit 4 test of the argument parsing (three arguments, two arguments, a `false` flag), and in task 5.2.

## 5. Verification

- [ ] 5.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation or internal-API findings.
- [ ] 5.2 Check the behaviour in the headless PyCharm harness (section 12 of the analysis notes), with the process log:
  - unchecking "Enable RobotCode for this project" stops the server and removes markers and banner; after an IDE restart no robotcode process starts, `workspace.xml` holds the value, `robotcodeSettings.xml` does not, and the Language Servers tool window shows the server as disabled; enabling it there starts the server and checks the setting;
  - with an SDK without Robot Framework, the banner shows the pip command; "Configure Python Interpreter..." opens the Python Interpreter page; installing with pip and "Retry" starts the server; the close button hides the banner until the IDE restarts;
  - with the profile `dev` selected, the widget shows "RF 7.5 · dev"; with an invalid SDK it shows the error state; every popup action runs;
  - "Create Keyword" on an unknown keyword ends with the new keyword selected and no LSP4IJ error notification; "Extract keyword" starts the rename of the new keyword;
  - the intention list on a keyword call and on a library import offers no documentation action.
