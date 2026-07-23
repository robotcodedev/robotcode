## Context

The `SemanticModel` (`packages/robot/src/robotcode/robot/diagnostics/semantic_analyzer/model.py`) is a dual representation — block tree (`root`) plus flat statement list (`statements`) plus `file_scope: VariableScope` — built by `SemanticAnalyzer` during namespace analysis. Its content (token trees with `sub_tokens`, resolved `keyword_doc`/`lib_entry` references, per-`DefinitionBlock` `local_variables`) is currently only observable indirectly through LSP feature output or the parity test suites. There is no way to look at the model itself and check whether what the analyzer built is correct.

Relevant existing infrastructure:

- `packages/analyze` already builds *real* namespaces per file with full configuration (robot.toml profiles, python path, variables, imports): `CodeAnalyzer` (`code/code_analyzer.py`) takes a `WorkspaceAnalysisConfig`, and `WorkspaceAnalysisConfig.semantic_model: bool` already flows into `DocumentsCacheHelper._is_semantic_model_enabled` — forcing the model build requires no new plumbing.
- The analyze config (`packages/analyze/src/robotcode/analyze/config.py`) already exposes `semantic_model` as an experimental option.
- The root CLI already has a `show_hidden_arguments()` pattern for developer-only surface.
- `semantic_analyzer/serialization.py` exists but serves a different purpose (pickle-cache reference resolution for `data_cache`); it is not a JSON serializer.

Constraint from project conventions: no unrequested user-facing infrastructure — this is a developer/diagnostic tool and must stay hidden and undocumented on the docs site.

## Goals / Non-Goals

**Goals:**

- A pure, read-only serializer `model_to_dict(model)` that captures everything the model holds: tree structure, statements, complete token trees, resolved references, variable scopes.
- Deterministic output: two runs over the same file and config produce byte-identical JSON (stable key order, stable list order, no memory addresses, workspace-relative paths).
- A hidden CLI entry point `robotcode analyze dump-model <file> [-o <output>]` that produces the dump using the same configuration path as `robotcode analyze code`.
- Output readable enough for manual review and diffable enough for golden-file snapshot tests later (Phase 4 replacement for the parity suites).

**Non-Goals:**

- No round-trip: the JSON is not designed to be deserialized back into a `SemanticModel` (that is `data_cache`/pickle territory).
- No full `KeywordDoc`/`LibraryEntry` dumps: resolved references are serialized as compact reference stubs (name + source + line), not as complete libdoc trees.
- No user-facing documentation, no VS Code/IntelliJ surface, no stability guarantee for the JSON schema (developer tool; format may change with the model).
- No dump of the legacy path (`ScopeTree`, ModelHelper state) — the tool inspects the new model only.

## Decisions

### D1: Serializer lives in the `semantic_analyzer` package, CLI lives in `analyze`

`model_to_dict` goes into a new module `packages/robot/.../semantic_analyzer/json_dump.py`, next to the dataclasses it serializes. Rationale: the serializer needs to evolve in lockstep with `nodes.py` (new statement fields must show up in dumps); keeping it in the same package makes that one review surface. The CLI command goes into `packages/analyze` because only that package has the machinery to build a *real* namespace outside the language server. Alternative considered: everything in `packages/analyze` — rejected because the serializer would then be invisible to `packages/robot` unit tests and to a later snapshot-test harness in `tests/robotcode/robot/`.

Named `json_dump.py`, not `inspect.py` (shadows a stdlib module name) and not extending `serialization.py` (different concern — that module resolves pickle references).

### D2: Explicit per-class serialization, not generic `dataclasses.asdict`

The serializer walks the node classes explicitly (`SemanticBlock`, the `SemanticStatement` subclass hierarchy, `SemanticToken`) instead of using `dataclasses.asdict` or reflection. Rationale:

- `parent` back-pointers create cycles — `asdict` would recurse infinitely.
- `keyword_doc`/`lib_entry`/`VariableDefinition` must become compact reference stubs, not full object dumps.
- Enum fields (`NodeKind`, `TokenKind`, `TokenModifier`, …) serialize as their names, not reprs.
- Explicitness makes the dump format a deliberate, reviewable contract.

Cost: a new field added to a node class does not automatically appear in dumps. Mitigation: a unit test iterates `dataclasses.fields()` of every node class against an explicit allowlist of serialized/intentionally-skipped fields, so adding a field without touching the serializer fails the test with a clear message.

### D3: Dump shape mirrors the model's dual representation

Top-level JSON object:

- `source`: workspace-relative path of the dumped file
- `tree`: recursive dump of `root` — every block with `kind`, class name, line range, block-specific fields (`condition`, `flavor`, `loop_variables`, …), `header`, and `body` (statements inline, nested blocks recursive)
- `statements`: the flat list, in document order — each with `kind`, class name, line range, statement-specific fields, and full `tokens` including recursive `sub_tokens` (`kind`, `value`, `line`, `col_offset`, `length`, `modifiers` sorted by name)
- `file_scope`: the four `VariableScope` layers (`command_line`, `own`, `imported`, `builtin`) as lists of variable-definition stubs
- `local_scopes`: one entry per `DefinitionBlock` (name + range) with its `local_variables` as `(stub, visible_from_line)` pairs

Statements appearing both in the tree and the flat list are serialized twice — redundancy is acceptable for an inspection format and lets each view be read standalone. Reference stubs: variable definitions as `{class, name, type, range, source}`; keyword references as `{name, source, line}`; `lib_entry` as `{name, alias, source}`. All `source` paths workspace-relative with `/` separators (cross-platform diffability); sources outside the workspace (site-packages, RF installation) fall back to the basename prefixed with `<external>/`.

### D4: Determinism rules

- `json.dumps(..., indent=2, ensure_ascii=False)` with insertion-ordered keys (fixed by the serializer, no `sort_keys` — logical ordering beats alphabetical for readability).
- Lists keep model order (document order / precedence order), which is already deterministic per build; sets (`modifiers`) are sorted by name.
- No absolute paths, object ids, timestamps, or environment-dependent values in the output. Builtin-variable stubs carry no in-memory values.

### D5: Hidden subcommand `dump-model` in the `analyze` group

`robotcode analyze dump-model <file> [-o <output>]`, registered alongside `cache` and `code` in `packages/analyze/src/robotcode/analyze/cli.py`, hidden via `show_hidden_arguments()`. It reuses the `analyze code` configuration loading (robot.toml + profile + CLI overrides for `-v`/`-V`/`-P`), builds the `WorkspaceAnalysisConfig` with `semantic_model=True` forced, obtains the namespace for the single file through the same `DocumentsCacheHelper` path as `CodeAnalyzer`, runs analysis (the model is populated during `namespace.analyse()`), and serializes `namespace.semantic_model`. Output: `-o <file>` writes JSON to the file; without `-o` it prints to stdout (pipeable into `jq`/`diff`). Exit code non-zero if the file cannot be analyzed or no model was built.

Alternative considered: a dev script under `scripts/` — rejected: it would duplicate the entire configuration/namespace bootstrap that `analyze` already owns, and `scripts/` is for repo-maintenance tooling, not for tools operating on arbitrary user projects.

## Risks / Trade-offs

- **[Serializer drift]** New model fields silently missing from dumps → the `dataclasses.fields()` allowlist test (D2) turns silent drift into a test failure.
- **[Dump size]** Token trees for large files produce large JSON (very_big_file.robot ⇒ tens of MB) → acceptable for a dev tool; stdout mode allows `jq` filtering; no pagination complexity added.
- **[Schema perceived as stable]** Someone builds tooling against the JSON shape → the command is hidden and the dump carries no version marker on purpose; the spec states the format is unstable.
- **[External sources leak machine paths]** Library sources under site-packages would break diffability across machines → `<external>/<basename>` fallback (D3).
- **[Model built only with experimental flag]** A dump of a file whose project config disables the model would be empty → the command forces `semantic_model=True` regardless of robot.toml (D5).

## Migration Plan

Not applicable — purely additive developer tool; no existing behavior changes, nothing to roll back beyond reverting the change.

## Open Questions

- None blocking. Whether the serializer later also feeds golden-file snapshot tests (and where those live) is decided in `semantic-model-cleanup`, not here.
