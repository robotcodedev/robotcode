# Spec: semantic-model-inspection

## Purpose

Serialize the complete `SemanticModel` of a Robot Framework file to
deterministic, diffable JSON for manual verification, diffing between changes
during the SemanticModel migration, and as the basis for future
snapshot/golden-file regression tests. Exposed through a hidden
developer/diagnostic CLI command; not a user-facing feature.

## Requirements

### Requirement: SemanticModel JSON serializer
The `semantic_analyzer` package SHALL provide a read-only serializer that converts a built `SemanticModel` into a JSON-compatible dict containing the complete model content: the block tree (every block with kind, class name, line range, block-specific fields, header, and body), the flat statement list in document order (every statement with kind, class name, statement-specific fields, and its full token tree including recursive sub-tokens with kind, value, position, length, and modifiers), the file-level `VariableScope` layers (command-line, own, imported, builtin), and per-`DefinitionBlock` local variables with their visibility lines. Resolved references (keyword docs, library entries, variable definitions) SHALL be serialized as compact stubs (name, type/class, source, position), not as full object dumps. Serialization SHALL NOT mutate the model.

#### Scenario: Complete statement and token content
- **WHEN** `model_to_dict` is called on the `SemanticModel` of an analyzed file containing keyword calls with argument cells that embed variables
- **THEN** the dump contains each statement with its kind and all tokens, and each token's `sub_tokens` (e.g. variable sub-tokens inside an ARGUMENT cell, `PYTHON_VARIABLE_REF` sub-tokens inside a CONDITION cell) appear recursively with their kind, value, line, column offset, and length

#### Scenario: Tree and scopes present
- **WHEN** `model_to_dict` is called on the model of a file with a test case and a keyword that defines local variables
- **THEN** the dump's tree mirrors the block hierarchy (file → sections → definition blocks → control-flow blocks), the file scope lists variable-definition stubs per precedence layer, and each definition block's local variables appear with their `visible_from_line`

#### Scenario: No serializer drift
- **WHEN** a dataclass field is added to a node class in `nodes.py` without updating the serializer
- **THEN** a unit test that compares `dataclasses.fields()` of every node class against the serializer's explicit allowlist of serialized and intentionally-skipped fields fails

### Requirement: Deterministic, diffable output
The serialized dump SHALL be deterministic: serializing the same file with the same configuration twice SHALL produce identical output. The dump SHALL contain no absolute paths, object identities, timestamps, or environment-dependent values. Source paths SHALL be workspace-relative with `/` separators; sources outside the workspace SHALL be rendered as `<external>/<basename>`. Unordered collections (e.g. token modifiers) SHALL be sorted.

#### Scenario: Repeated dump is identical
- **WHEN** the same file is dumped twice in the same environment
- **THEN** the two JSON outputs are byte-identical

#### Scenario: External library source
- **WHEN** the dump contains a stub whose source is a library installed outside the workspace (e.g. under site-packages)
- **THEN** the stub's source is `<external>/<basename>` and contains no machine-specific path

### Requirement: Hidden dump-model CLI command
The `robotcode analyze` command group SHALL provide a subcommand `dump-model <file>` that is hidden from help output via the existing `show_hidden_arguments` pattern. The command SHALL build the namespace for the given file using the same configuration path as `robotcode analyze code` (robot.toml, profiles, `-v`/`-V`/`-P` overrides), SHALL force the semantic-model build regardless of the experimental flag's configured value, SHALL run analysis, and SHALL emit the JSON dump to stdout or, with `-o <output>`, to the given file. The command SHALL exit non-zero when the file cannot be analyzed or no semantic model was built. The JSON format is a developer/diagnostic surface without stability guarantees.

#### Scenario: Dump to stdout
- **WHEN** `robotcode analyze dump-model path/to/suite.robot` is run in a project where the experimental semantic-model flag is not enabled
- **THEN** the command prints the JSON dump of the file's `SemanticModel` to stdout and exits with code 0

#### Scenario: Dump to file
- **WHEN** `robotcode analyze dump-model path/to/suite.robot -o model.json` is run
- **THEN** the JSON dump is written to `model.json`

#### Scenario: File cannot be analyzed
- **WHEN** `robotcode analyze dump-model` is invoked with a path that does not exist or is not an analyzable Robot Framework file
- **THEN** the command reports an error and exits with a non-zero code
