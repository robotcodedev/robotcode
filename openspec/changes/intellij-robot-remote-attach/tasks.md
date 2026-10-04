# Tasks

## 1. Precondition and configuration

- [ ] 1.1 Check that the detach fix of `debugger-dap-e2e-tests` (its task 2.4) has landed: its scenarios for a detached or vanished client pass with `hatch run test:test`. Do not ship this change before they do.
- [ ] 1.2 Add the attach options class (host `127.0.0.1`, port `6612`, a list of path mappings with local and remote folder), the attach configuration on `RunConfigurationBase` with `checkConfiguration()` (blank host, port outside 1 to 65535, mapping with an empty folder), and its factory (id `ROBOT_FRAMEWORK_ATTACH`, name "Robot Framework (Attach)") as a second factory of `RobotCodeConfigurationType`. Verify with JUnit tests: the options survive `writeExternal`/`readExternal` and `clone()`; each invalid value raises a configuration error, and valid values raise none.
- [ ] 1.3 Add the editor (host, port, `PathMappingsComponent`, a comment on starting a run with `robotcode debug --tcp <address>:<port>` and on its 15-second wait) with its texts in `messages/RobotCode.properties`. Verify in task 3.2 that the editor shows the defaults, that real input enables Apply, and that the values survive an IDE restart.
- [ ] 1.4 Let `RobotCodeRunConfigurationProducer.getConfigurationFactory()` return the factory with the id `ROBOT_FRAMEWORK_TEST`, let `RobotCodeDebugProgramRunner` accept the attach configuration, and keep `RobotCodeProgramRunner` limited to run configurations. Verify with JUnit tests of the producer's factory id and of `canRun` for both runners, executors and configuration kinds.

## 2. Attach sessions

- [ ] 2.1 Introduce the session interface that `RobotCodeDebugProcess` uses (DAP client, server proxy once connected, configuration hook, coroutine scope) and let the launch state provide it, without changing launched runs. Verify with the existing tests and a launched Debug session in task 3.2.
- [ ] 2.2 Add the attach state and its process handler without a process: background handshake with a connect wait of up to 15 s and `attach` with the path mappings; a console message and termination when no connection is made or the debugger closes it; detach sends `disconnect` without `terminateDebuggee`, closes the connection and then reports the detach; destroy goes through the stop policy with closing the connection as fallback; `terminated`, `exited` and a lost connection terminate the handler; the console prints the debugger's `output` events. Verify with JUnit tests against a fake DAP server: the `attach` arguments carry the configured mappings; detaching sends `disconnect` with `terminateDebuggee` false and never `terminate`; destroying sends `terminate`; a closed connection terminates the handler with the exit code of `exited`; without a listener the handler writes the message and terminates after the (injected, short) connect wait.
- [ ] 2.3 Register the "Terminate Run" action for attach sessions through `XDebugProcess.registerAdditionalActions`, calling `destroyProcess()` on the handler, with its text in `messages/RobotCode.properties`. Verify with the terminate harness check.

## 3. Verification

- [ ] 3.1 Run `./gradlew test buildPlugin verifyPlugin` in `intellij-client/` and verify that all three pass without new deprecation or internal-API findings.
- [ ] 3.2 Check the behaviour in the headless PyCharm harness, starting the run to attach to with the `test.rf75` interpreter and the bundled `robotcode` as `robotcode debug --tcp 6612 -- tests` in the project folder:
  - the attach configuration stops at a breakpoint in `sample.robot` and shows frames and variables;
  - Stop while paused ends the session, and the run finishes within a few seconds and writes `output.xml`;
  - with a new run, "Terminate Run" while paused ends it gracefully with `log.html` and `report.html` written, and the session ends;
  - with the run started in a copy of the project in another folder and a mapping from the project folder to that copy, a breakpoint in the local `sample.robot` stops the run and the top frame opens the local file;
  - with nothing listening on the port, the session ends after 15 seconds with a message in its console;
  - the run widget offers Debug but not Run for the attach configuration, a gutter run still creates a run configuration, and a launched Debug session still stops at its breakpoints;
  - the attach configuration's editor shows the defaults, and saved values survive an IDE restart;
  - `idea.log` gets no new SEVERE entries from RobotCode.
