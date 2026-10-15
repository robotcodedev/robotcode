# Tasks

## 1. Keyword events in the debugger

- [ ] 1.1 Add the option `--keyword-events/--no-keyword-events` (default off) to `robotcode debug` in `packages/debugger/src/robotcode/debugger/cli.py`, pass it through `run.py` to a `keyword_events` flag on `Debugger.instance`, and map the launch attribute `keywordEvents` to the option in `launcher/server.py` next to `outputMessages`. Verify with a launcher test in `tests/robotcode/debugger/test_launcher.py`, in the style of the wrapper test, that `keywordEvents: true` adds `--keyword-events` and that a launch without it adds nothing.
- [ ] 1.2 In `listeners.py`, send `robotStarted`/`robotEnded` of type `keyword` from `start_keyword`/`end_keyword` when the flag is set: `synced=False`, skipped while `Debugger.instance.state == State.CallKeyword`, with the Robot Framework attributes (type, name, source, line, status, elapsed time on end) and an execution id `<source>;<lineno>;<name>;<counter>` that is unique per execution. Verify with a new `tests/robotcode/debugger/test_keyword_events.py` that runs suites in-process like `test_terminate.py` and collects the events: no keyword events without the flag; with the flag a `Log` call produces a start and an end with the same id, source, line, status and an elapsed time; a three-iteration `FOR` produces events for the loop, the iterations on the loop's line and the body; a recursive keyword gets distinct ids; every keyword event has `synced` false.
- [ ] 1.3 Verify with a test in the same file that a keyword evaluated through `Debugger.instance.evaluate` at a stop produces no keyword events while the paused keyword's own events are unchanged.

## 2. Setting and launch attribute in VS Code

- [ ] 2.1 Add the setting `robotcode.run.showExecutionInEditor` (boolean, default false, scope resource) to the "Run" category in `package.json` and the launch attribute `keywordEvents` to the `robotcode` debugger's launch attributes, both with descriptions that name the highlighted running keyword and the step durations. Regenerate the settings reference with `hatch run create-vscode-settings-docs` and verify that `package.json` is valid JSON and the reference shows the setting.
- [ ] 2.2 In `vscode-client/extension/debugmanager.ts`, fill `keywordEvents` from the setting when the launch configuration leaves it out, next to the `outputMessages` handling. Verify with `npx tsc --noEmit -p vscode-client/extension/tsconfig.json` and `npm run lint`, and in the VS Code harness that a Test Explorer run with the setting on starts `robotcode debug` with `--keyword-events` (visible in the RobotCode output channel) and without the setting does not.

## 3. Highlights and durations in the editor

- [ ] 3.1 In `vscode-client/extension/testcontrollermanager.ts`, replace the constant `showEditorRunDecorations` with the setting, keep `startedEvents` per run, add the durations model per workspace folder (source → line → count and total) filled from keyword `robotEnded` events, and a duration decoration type whose `after.contentText` shows the formatted duration (`36 ms`, `1.2 s`, `3 × 36 ms`) in the CodeLens colour. Verify with `tsc` and `npm run lint`.
- [ ] 3.2 Render in batches: one timer of about 100 ms that repaints the visible editors of the files changed since the last repaint, with the running highlight and the durations; repaint on `onDidChangeVisibleTextEditors`; compare paths as normalized `fsPath`. Verify in the harness with a suite whose test calls a resource keyword that sleeps two seconds: during the sleep the test line, the call line and the `Sleep` line are highlighted, an editor opened during the sleep shows the highlight at once, and after the run the `Sleep` line shows a duration of about two seconds while the highlights are gone.
- [ ] 3.3 Clear correctly: remove a run's highlights on `robotExited` and when the test run ends or is cancelled; remove a file's durations when the document changes, when a new run starts in the same workspace folder, and when the setting is turned off. Verify in the harness: stop a run during a sleep and see no highlight left; edit the resource file and see its durations disappear; start a second run and see the first run's durations disappear when it starts.
- [ ] 3.4 Verify the loop presentation in the harness with a three-iteration `FOR` over `Log`: the `Log` line shows three executions and the total time, and the `FOR` line shows one execution with the loop's time.

## 4. Documentation

- [ ] 4.1 Add a section "Watching a run in the editor" to `docs/src/content/docs/guides/vscode/running-and-debugging.mdx`: the setting, the highlighted lines, the durations and when they disappear, with a note that runs started in the terminal show nothing. Verify that `npm run docs:build` passes.

## 5. Verification

- [ ] 5.1 Run `hatch run test:test` and `hatch run lint:all` and verify that both pass.
- [ ] 5.2 Measure the overhead: run a suite with a ten-thousand-iteration `FOR` over `No Operation` through `robotcode debug --tcp` with a DAP client script, once with and once without `--keyword-events`, with the client reading but not synchronizing, and record both wall-clock times in design.md under Risks. If the difference exceeds a few percent, batch the end events per test before the next step, as the design foresees, and measure again.
