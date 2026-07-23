# Tasks — semantic-model-dump-tool

## 1. Serializer

- [x] 1.1 Create `packages/robot/src/robotcode/robot/diagnostics/semantic_analyzer/json_dump.py` with `model_to_dict(model, workspace_root)`: explicit per-class walkers for `SemanticToken` (recursive `sub_tokens`, sorted `modifiers`), the `SemanticStatement` subclass hierarchy (statement-specific fields incl. `inner_calls`, `assign_variables`, import/setting/definition fields), and the `SemanticBlock` hierarchy (block-specific fields, `header`, recursive `body`)
- [x] 1.2 Add reference-stub helpers: variable definitions as `{class, name, type, range, source}`, keyword docs as `{name, source, line}`, library entries as `{name, alias, source}`; source paths workspace-relative with `/` separators, `<external>/<basename>` fallback for sources outside the workspace
- [x] 1.3 Serialize `file_scope` (four `VariableScope` layers) and `local_scopes` (per `DefinitionBlock`: name, range, `local_variables` with `visible_from_line`) into the top-level dump shape from design D3

## 2. CLI command

- [x] 2.1 Add hidden `dump-model` subcommand in `packages/analyze`: click command registered in `analyze` group (`cli.py`), hidden via `show_hidden_arguments()`, options `<file>` argument, `-o/--output`, and the `-v`/`-V`/`-P` overrides shared with `analyze code`
- [x] 2.2 Wire namespace construction: reuse the `analyze code` config loading, force `semantic_model=True` in the `WorkspaceAnalysisConfig`, build the namespace for the single file via the `DocumentsCacheHelper` path, run analysis, serialize `namespace.semantic_model` with `json.dumps(..., indent=2, ensure_ascii=False)` to stdout or `-o` file; non-zero exit on unanalyzable file or missing model

## 3. Tests

- [x] 3.1 Serializer unit tests under `tests/robotcode/robot/diagnostics/test_semantic_analyzer/`: representative fixture (keyword calls with variable sub-tokens, CONDITION cell with `PYTHON_VARIABLE_REF` subs, FOR/IF blocks, local variables, imports) — assert dump completeness per the spec scenarios
- [x] 3.2 Determinism test: dump the same parsed file twice, assert byte-identical JSON; assert no absolute paths in the output
- [x] 3.3 Serializer-drift guard: iterate `dataclasses.fields()` of every class in `nodes.py` against the serializer's allowlist of serialized/intentionally-skipped fields
- [x] 3.4 CLI test: run `dump-model` against a small test project (click runner), assert valid JSON on stdout, `-o` file writing, and non-zero exit for a nonexistent file

## 4. Verification

- [x] 4.1 `hatch run test:test` (full RF matrix, default Python) green
- [x] 4.2 `hatch run lint:all` green
