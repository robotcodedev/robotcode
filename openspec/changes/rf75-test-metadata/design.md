# Design: rf75-test-metadata

## Context

See proposal.md. Verified facts:

- **RF 7.5.** `TestCase.metadata` (running and result models) is a `Metadata` `NormalizedDict`: keys keep their spelling, iteration is sorted by normalised key, values are strings; `to_dict` emits `metadata` when non-empty; `output.xml` gets `<meta name="…">` elements under `<test>`; the V2 listener `start_test`/`end_test` attributes gain `metadata` (empty dict when none); `${TEST_METADATA}` is set per test. RF 5.0–7.4 raise `Incompatible child element 'meta' for 'test'` when reading such an `output.xml`; for `output.json` only RF 7.2–7.4 fail with `'robot.result.TestCase' object does not have attribute 'metadata'` (RF 7.0/7.1 reject every RF 7.5 JSON file earlier, at the suite's `generator` attribute) — RobotCode's `results` wraps these into `failed to parse …` without a hint.
- **Discover.** `TestItem` (`runner/cli/discover/_models.py`) has `tags`, `description` (documented but never set), `error`, `rpa`; `Collector.visit_test` normalises tags and maps empty to `None` because `remove_defaults` only drops fields equal to their default (an empty dict would be emitted). `_render.py` prints `- _Tags:_` sub-bullets when `--tags`. `--search` (`_search.py` `SearchModifier._matches`) walks ancestor-suite doc and metadata but not test metadata; the module already holds import-time RF-version helpers.
- **Results.** `TestResultItem` (show, summary failed) has tags; `LogTest` has no doc/tags/metadata; `LogSuite.metadata` exists with `--suite-info`. Builders (`_make_test_item`, `LogCollector.end_test`) and renderers (`render_show`, `_test_header_md`, `_render_suite_header_md` for the suite pattern) are the extension points; version-conditional helpers are bound once at import in `results.py`.
- **Debugger.** `ListenerV2.start_test`/`end_test` forward the whole attribute dict, so DAP `robotStarted`/`robotEnded` already carry `metadata` on RF 7.5; nothing server-side to do.
- **VS Code.** `RobotTestItem` mirrors the discover JSON; `robotItemsEqual` and `snapshotChildren` compare/copy `description`, `error`, `tags`; the item description is rendered as `<type>  - <description>` (today always empty); tags become `vscode.TestTag`s. There is no tooltip API for test items.
- **IntelliJ.** `RobotCodeTestItem` (`testing/DataItems.kt`) is decoded with the default kotlinx `Json`, which rejects unknown keys (documented kotlinx behaviour; repo precedent commit `c76b1139` changed `_models.py`, `DataItems.kt`, `testcontrollermanager.ts` and the docs together). DAP attributes are decoded with Gson (ignores unknown keys).
- **Language server.** `hover_TestCase` renders name, documentation and tags from the test body; no setting line has a hover. Completion already offers `[Metadata]` (from RF's `TestCaseSettings`). Document symbols show no setting statements. The semantic analyzer's `visit_DocumentationOrMetadata` adds every `Metadata` node's key to `_metadata_references` regardless of scope, while `visit_Tags` routes by `_node_stack` into keyword vs test-case tag indexes; the legacy `NamespaceAnalyzer` does the same unscoped indexing and is still selectable; `metadata_references` is plumbed through `AnalyzerResult`, `NamespaceData` (cached, serialised as `Dict[str, Set[Location]]`), `Namespace` and `ProjectIndex`, and compared by `test_variable_pipeline_comparison.py`.
- **Tests.** Discover and results acceptance tests run an in-process `CliRunner` over fixture suites (`tests/robotcode/runner/cli/discover/suites`, `results/suites` executed once per session with the installed RF); RF gates live in `rf_markers.py` (`needs_rf_70`, `needs_rf_72`). Hover regtests compare only the first line. No unit-test infrastructure exists for the VS Code or IntelliJ clients beyond lint/compile/Gradle tests.

## Goals / Non-Goals

**Goals:**
- One JSON shape for test metadata across discover and results, identical to the existing suite shape, absent when not applicable.
- Visibility where users look: explorer, hover, text output, search.
- Correct scoping of the analyzer's metadata index.

**Non-Goals:**
- Suite-level `metadata`/`doc` on discover items (every RF version; own change).
- A `discover metadata` index and `results stats` by metadata.
- Run-output echo of metadata and an explorer opt-out setting (add if users ask).
- Filling the never-set discover `description` from `test.doc` (docs are corrected instead).

## Decisions

### D1: `metadata` object, author spelling, RF order, omitted when empty

`TestItem`, `TestResultItem` and `LogTest` gain `metadata: Optional[Dict[str, str]] = None`, filled by one import-time helper in `_search.py` — two `def test_metadata(test) -> Dict[str, str]` bodies under `if RF_VERSION >= (7, 5): … else: …`, the 7.5 body reading `test.metadata` with the `# type: ignore[attr-defined, unused-ignore]` the neighbouring `_for_assignments` helper uses, since the lint environment type-checks against RF 7.4 (a lambda assignment would also fail ruff's E731) — and mapped `or None` so `remove_defaults` drops it. Keys keep the author's spelling (as `LogSuite.metadata`, RF's `to_dict` and listener attributes do); normalising like tags was rejected because metadata is display data. Order is RF's (sorted by normalised key).

### D2: Search and text flags mirror tags

`SearchModifier._matches` gains literal matching over test metadata names and values (same matcher as suite metadata). `discover all/tests/tasks` and `results show` get `--metadata/--no-metadata` rendering `- _Metadata:_ name: value, …`, defaulting to off on all four commands (deliberately unlike `--tags`, which defaults to on for `discover all` only: metadata lines are longer than tag lists); `results log` renders bullets under the test header without a flag (the log view is verbose by design). Piggy-backing on `--tags` was rejected as conflating two settings.

### D3: Explorer description, no new setting

VS Code: `RobotTestItem.metadata`, included in `robotItemsEqual` and `snapshotChildren`, rendered into the item description via `truncateAndReplaceNewlines`; `RobotExecutionAttributes.metadata` typed for completeness. The description is the only secondary text VS Code offers; run-output echo shows metadata only during runs and a setting adds surface for little value. IntelliJ: `RobotCodeTestItem.metadata: Map<String, String>? = null` with `equals`/`hashCode`, mandatory for strict decoding; `RobotExecutionAttributes.metadata` optional (Gson ignores unknown keys).

### D4: Separate `testcase_metadata_references`

Both analyzers route `Metadata` nodes by whether a `TestCase` is on the node stack into `metadata_references` (suite) or the new `testcase_metadata_references`, exactly like the tag indexes; `AnalyzerResult`, `NamespaceData`, `Namespace`, `ProjectIndex.find_testcase_metadata_references` and the pipeline-comparison test are extended. Old cache entries are safe not because of the field default (pickle bypasses `__init__`) but because `Namespace.from_data` runs inside the `try/except` fallback of `document_cache_helper`, which re-analyses on failure, and because the store is keyed by `app_version`; `from_data` reads the new field with `getattr(data, "testcase_metadata_references", {})` so stale entries keep loading without the fallback. Tuple or prefixed keys were rejected (serialisation / ad-hoc encoding); leaving the index mixed contradicts `support-rf75`'s note. `NodeKind.SETTING_METADATA` stays shared for both scopes, as `SETTING_TAGS` is.

### D5: Hover block and reader hint

`hover_TestCase` collects `Metadata` statements from the test body (the class exists on every RF version; on < 7.5 a test body never contains one) and renders `*Metadata*:` lines through the same variable replacement as documentation. `_load_execution_result` appends a hint when RF's `DataError` contains `Incompatible child element 'meta' for 'test'` (XML, RF 5.0–7.4) or `'robot.result.TestCase' object does not have attribute 'metadata'` (JSON, RF 7.2–7.4 only) — narrowly matched and covered by a static XML fixture test gated `RF_VERSION < (7, 5)` (a JSON hint test would need `(7, 2) <= RF_VERSION < (7, 5)`).

## Risks / Trade-offs

- [IntelliJ strict JSON] → `DataItems.kt` changes in the same change; plugin and Python package release together.
- [`"metadata": {}` emitted by mistake] → `or None` mapping; test asserts absence for a test without metadata.
- [Explorer clutter for long metadata] → compact `name: value` pairs, truncated; opt-out setting deferred.
- [Legacy analyzer forgotten] → the pipeline-comparison test fails if only one analyzer is changed.
- [Results fixtures on RF < 7.5] → the fixture suite still runs (the test fails with the lexer error); assertions are `needs_rf_75`-gated; the session fixture ignores the exit status already.
- [Reader hint matches RF's message text] → narrow, tested; RF's wording is unchanged between 7.4 and 7.5.

## Migration Plan

Additive JSON fields and flags; no migration. IntelliJ and VS Code clients must ship together with the Python packages (as always).
