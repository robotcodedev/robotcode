# Proposal: rf75-test-metadata

## Why

Robot Framework 7.5 lets tests and tasks carry `[Metadata]` name/value pairs (#4409), shown in the log like documentation. RobotCode accepts the setting (after `support-rf75`) but nowhere shows or uses the data: `robotcode discover` and `robotcode results` JSON have no test metadata, `--search` ignores it, the VS Code test explorer cannot show it, the hover on a test name lists documentation and tags but not metadata, and the semantic analyzer files test-level metadata keys into the suite-level metadata index. A user who adds `[Metadata]    Issue    4409` to a test cannot see it anywhere in RobotCode.

## What Changes

- **Discover and results JSON**: test/task items in `discover all/tests/tasks`, `results show`/`summary --failed` and `results log` carry `metadata` as a name → value object (names in the author's spelling, values verbatim, multi-line values with `\n`), omitted when empty and absent on RF < 7.5 — the same shape `results log --suite-info` already uses for suites.
- **Search**: `--search` in `discover` and `results` matches test metadata names and values, like it already matches ancestor-suite metadata.
- **Text output**: `discover all/tests/tasks` and `results show` gain `--show-metadata/--no-show-metadata` (same defaults as the tags flag: on for `discover all`, off for the others; only listed in `--help` on Robot Framework ≥ 7.5) printing `- _Metadata:_ name: value, …`. The flag cannot be called `--metadata`: that is Robot's own `--metadata name:value` option, which `discover` passes through. For a consistent naming the tags flag is renamed from `--tags/--no-tags` to `--show-tags/--no-show-tags`; the old name is gone (maintainer decision); `results log` prints the same metadata line under a test header whenever present.
- **VS Code test explorer**: planned and implemented first (metadata in the item description), then dropped by maintainer decision — the explorer does not show metadata and the extension is unchanged; it ignores the additional `metadata` field of the discover output.
- **IntelliJ**: the discover item model accepts the new key (mandatory: the plugin's strict JSON decoding would otherwise fail on RF 7.5 projects that use test metadata).
- **Hover**: the test-name hover shows a Metadata block next to Documentation and Tags.
- **Analyzer**: test-level metadata references are indexed separately from suite-level ones (`testcase_metadata_references`, mirroring the tag indexes) in both analyzers, the namespace data and the project index.
- **Older Robot Framework**: `robotcode results` explains that an `output.xml`/`output.json` with test metadata was written by RF ≥ 7.5 and needs RF ≥ 7.5 to be read, instead of RF's bare "Incompatible child element 'meta'" error.
- Documentation: discover/results references (JSON shapes, flags, search targets; the never-set `description` example is corrected), regenerated `cli.md`.

Depends on `support-rf75` (`[Metadata]` accepted without diagnostics, `${TEST_METADATA}`). Left out: suite-level metadata/doc in discover items, a `discover metadata` index and `results stats` by metadata, run-output echo of metadata, an opt-out setting for the explorer description.

## Capabilities

### New Capabilities

- `test-metadata`: How test/task-level metadata from Robot Framework ≥ 7.5 is represented and shown across RobotCode — discover and results JSON and text output, search, the discover models of the editor clients and the test hover — and how files with test metadata are handled on older Robot Framework versions.

### Modified Capabilities

<!-- none -->

## Impact

- `packages/runner/src/robotcode/runner/cli/_search.py`: import-time `get_test_metadata()` helper, search matching; `cli/_markdown.py`: shared `metadata_md`.
- `packages/runner/src/robotcode/runner/cli/discover/_models.py`, `discover.py`, `_render.py`: `metadata` field, collector, `--show-metadata` flag, `--show-tags` rename, text rendering.
- `packages/runner/src/robotcode/runner/cli/results/_models.py`, `results.py`, `_render.py`: `metadata` on `TestResultItem` and `LogTest`, `--show-metadata` flag and `--show-tags` rename for `show`, log rendering, reader hint.
- `packages/robot/src/robotcode/robot/diagnostics/semantic_analyzer/analyzer.py`, `namespace_analyzer.py`, `analyzer_result.py`, `namespace.py`, `project_index.py`, `semantic_analyzer/enums.py`: separate test metadata index.
- `packages/language_server/.../parts/hover.py`: Metadata block in the test-case hover.
- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/testing/DataItems.kt` and `debugging/RobotCodeDebugProtocolClient.kt` (`metadata` on the item and attribute models).
- Docs: `docs/03_reference/discovering-tests.md`, `docs/03_reference/analyzing-results.md`, `docs/03_reference/cli.md` (regenerated).
- Tests: new discover/results fixture suites (tests and tasks) and RF-gated tests (`needs_rf_75`, shared with `rebot-console-options`), analyzer/project-index/namespace-data tests, a hover test, a Kotlin unit test that the discover model decodes items with `metadata`.
- No change to the debugger (attributes already carry `metadata` on RF 7.5), completion, semantic tokens or document symbols.
