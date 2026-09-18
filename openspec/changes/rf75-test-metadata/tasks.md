# Tasks: rf75-test-metadata

## 1. Prerequisites and shared helper

- [ ] 1.1 Confirm `support-rf75` is applied (`[Metadata]` in tests analyzes without diagnostics on RF 7.5, `rf75` env exists); add `needs_rf_75` to `tests/robotcode/runner/cli/rf_markers.py` unless `rebot-console-options` already added it; verify `hatch run test.rf75:test -- tests/robotcode/runner/cli` is green
- [ ] 1.2 Add an import-time helper `test_metadata(test) -> Dict[str, str]` in `packages/runner/src/robotcode/runner/cli/_search.py` (`dict(test.metadata)` on RF ≥ 7.5, `{}` otherwise) and extend `SearchModifier._matches` to match test metadata names and values literally; verify with discover and results search tests (task 2.3 / 3.3) and update the class docstring

## 2. Discover

- [ ] 2.1 Add `metadata: Optional[Dict[str, str]] = None` to `TestItem` in `runner/cli/discover/_models.py` and fill it in `Collector.visit_test` with `test_metadata(test) or None`; verify with new fixture suites `tests/robotcode/runner/cli/discover/suites/metadata.robot` (tests with single-line, multi-line and spaced-key metadata, one test without) and `metadata_tasks.robot` (`*** Tasks ***`, run with `--root` like the existing `tasks.robot` fixture) and `discover/test_metadata.py` (`needs_rf_75`) parametrised over `discover all`, `tests` and `tasks` that `items[].metadata` has the author's spelling and `\n`-joined values, that the test without metadata has no `metadata` key, and (inverse gate) that on RF < 7.5 no item has the key
- [ ] 2.2 Add `--metadata/--no-metadata` (default off on all three commands) to `discover all/tests/tasks` next to `--tags`, thread `show_metadata` into `render_all`/`render_tests_or_tasks`/`_emit_tree` in `discover/_render.py` printing `- _Metadata:_ name: value, …`; verify with text-output tests for `discover all`, `discover tests` and `discover tasks` that the line appears only with the flag and that JSON output is unaffected
- [ ] 2.3 Verify with a test that `discover tests --search <metadata value>` lists only the matching test on RF 7.5

## 3. Results

- [ ] 3.1 Add `metadata` to `TestResultItem` and `LogTest` in `runner/cli/results/_models.py`, fill them in `_make_test_item` and `LogCollector.end_test`; verify with a session fixture `tests/robotcode/runner/cli/results/suites/test_metadata.robot` and `needs_rf_75` tests in `test_show.py`, `test_summary.py` and `test_log.py` that `tests[].metadata`, `failed[].metadata` and the log test `metadata` match and are absent for tests without metadata
- [ ] 3.2 Add `--metadata/--no-metadata` to `results show` (rendering `- _Metadata:_ …` like tags) and render metadata bullets under the test header in `results log` whenever present (pattern of `_render_suite_header_md`); verify with text-output tests
- [ ] 3.3 Verify with a test that `results show --search <metadata value>` matches on RF 7.5
- [ ] 3.4 In `_load_execution_result` append a hint to the `ClickException` when RF's error contains `Incompatible child element 'meta' for 'test'` (XML) or `'robot.result.TestCase' object does not have attribute 'metadata'` (JSON, RF 7.2–7.4): the file was written by RF ≥ 7.5 with test metadata and needs RF ≥ 7.5; verify with a static `output.xml` fixture containing `<meta>` under `<test>` and a test gated `RF_VERSION < (7, 5)` asserting the hint, a JSON fixture test gated `(7, 2) <= RF_VERSION < (7, 5)`, plus a `needs_rf_75` test that both files parse

## 4. Analyzer and hover

- [ ] 4.1 Split the metadata index: `SemanticAnalyzer.visit_DocumentationOrMetadata` and `NamespaceAnalyzer` route `Metadata` nodes inside a `TestCase` into a new `testcase_metadata_references`; add the field to `AnalyzerResult`, `NamespaceData` (defaulted), `Namespace`, `ProjectIndex` (`find_testcase_metadata_references`, merge/subtract/clear) and fix the `NodeKind.SETTING_METADATA` comment; verify with a `skipif RF_VERSION < (7, 5)` analyzer test (suite `Metadata    A    1` + test `[Metadata]    B    2` → `metadata_references == {"A"}`, `testcase_metadata_references == {"B"}`), an all-versions test that suite keys never land in the test index, and extended `test_variable_pipeline_comparison.py`, `test_project_index.py` and `test_namespace_data.py` round-trips
- [ ] 4.2 Extend `hover_TestCase` in `packages/language_server/.../parts/hover.py` with a `*Metadata*:` block (`name: value` lines) built from `Metadata` statements in the test body, with variable replacement like documentation; verify with a plain test (skipped below RF 7.5) that the test-name hover contains `Issue: 4409` and that hover regtests produce no baseline diff

## 5. Clients

- [ ] 5.1 VS Code: add `metadata?: { [key: string]: string }` to `RobotTestItem` and `RobotExecutionAttributes` in `vscode-client/extension/testcontrollermanager.ts`, include it in `robotItemsEqual` and `snapshotChildren`, and render it into the item description as `Key: value, …` via `truncateAndReplaceNewlines`; verify with `npm run lint`, `npm run compile` and a manual check on RF 7.5 that the explorer shows `Issue: 4409` and updates after a metadata-only edit
- [ ] 5.2 IntelliJ: add `val metadata: Map<String, String>? = null` to `RobotCodeTestItem` in `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/testing/DataItems.kt` (extend `equals`/`hashCode`) and `var metadata: Map<String, String>? = null` to `RobotExecutionAttributes` in `debugging/RobotCodeDebugProtocolClient.kt`, and add a Kotlin unit test under `intellij-client/src/test/kotlin/` that `Json.decodeFromString<RobotCodeDiscoverResult>` succeeds on a fixture item carrying `"metadata": {"Issue": "4409"}` (documenting that the default strict `Json` would otherwise fail); verify with `(cd intellij-client && ./gradlew test && ./gradlew verifyPlugin)` and a manual discovery on an RF 7.5 project with test metadata

## 6. Documentation and verification

- [ ] 6.1 Update `docs/03_reference/discovering-tests.md` (TestItem shape, `--metadata` flag, search targets; correct the never-set `description` example) and `docs/03_reference/analyzing-results.md` (show/summary/log JSON, `--metadata` flag, search targets; extend the RF < 7.5 note from `support-rf75` with the new hint), regenerate `docs/03_reference/cli.md` with `hatch run create-cmd-line-docs` keeping only the new-option hunks; verify with `npm run docs:build`
- [ ] 6.2 Run `hatch run lint:all` and `hatch run test:test` (full matrix) and confirm both pass
