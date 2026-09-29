# Proposal: env-var-check-nested-names

## Why

Robot Framework resolves the variables inside the name of an environment variable before it looks the name up: `%{NE_${S}}` with `${S}` = `suffix` reads `NE_suffix`, `%{%{N}}` reads the environment variable named by `N`. The `NamespaceAnalyzer` (the default analysis path) checks the existence of the environment variable on the unresolved name as written instead: [`_find_variable`](../../../packages/robot/src/robotcode/robot/diagnostics/namespace_analyzer.py) returns an `EnvironmentVariableDefinition` named `%{<raw name>}` for every `%{...}`, and [`_handle_find_variable_result`](../../../packages/robot/src/robotcode/robot/diagnostics/namespace_analyzer.py) looks up `os.environ.get("NE_${S}")`, a name that never exists. Checked against `robot` on Robot Framework 5.0.1, 6.1.1, 7.0.1 and 7.5, this produces `EnvironmentVariableNotFound` errors that Robot Framework never raises:

- `%{NE_${S}}` with `NE_suffix` set, `%{%{N}}` with `N` naming a set variable, and `%{NE_${EQ}}` where `${EQ}` is `X=fallback` (after resolution the `=` makes `fallback` a default) all pass in Robot Framework and get an error in RobotCode.
- `%{NE_${UNDEF}}` gets the correct `Variable '${UNDEF}' not found.` plus an error for `'%{NE_${UNDEF}}'`, and `%{%{UNSET}}` gets an error for the outer and for the inner variable; Robot Framework reports only the nested one.
- Where Robot Framework does fail for the resolved name (`%{NE_${S2}}` with `NE_other` unset), the message names the unresolved `%{NE_${S2}}` instead of `%{NE_other}`.

In documentation and metadata, where the analyzer reports hints, the same names get an `EnvironmentVariableNotReplaced` hint next to the correct `VariableNotReplaced` hint for the nested variable.

## What Changes

- The `NamespaceAnalyzer` no longer checks the existence of an environment variable whose name, as written, contains a variable (`%{NE_${S}}`, `%{%{N}}`, `%{NE_@{L}}`, `%{NE_${{expr}}}`): no `EnvironmentVariableNotFound` and no `EnvironmentVariableNotReplaced` for it. The analyzer does not try to resolve the name (see design: static resolution is not extended).
- The variables nested in such a name are analyzed as today: an undefined one gets `VariableNotFound` (or `VariableNotReplaced` in documentation and metadata), an unset nested environment variable without default gets `EnvironmentVariableNotFound` with its own name, and references to the nested variables are recorded as before.
- `%{NAME}`, `%{NAME=}` and `%{NAME=default}` without nested variables behave exactly as before; an unset `%{NAME}` without default stays an error. A name with an escaped variable (`%{NE_\${x}}`) contains no variable and keeps its current check (design, Non-Goals).
- The `SemanticAnalyzer` (semantic-model path) is not changed. It already never checks an unresolved nested name; on Robot Framework 7.0 and newer it checks a statically resolved name instead. For a scalar such as `%{NE_${S2}}` that is the name Robot Framework looks up (error for `'%{NE_other}'`), but the resolution ignores item access: `%{NE_${L}[0]}` with `@{L}` = `a b` is checked as `NE_a b` and gets an error although the test passes in Robot Framework, and `%{NE_${D}[k]}` with `&{D}` = `k=v` becomes the name `NE_k` with the default `v`. Whether that resolution-based check should stay or be aligned with the `NamespaceAnalyzer` is left to the maintainer (design, Open Questions); the spec states only what both paths share and the default path.

## Capabilities

### New Capabilities

- `environment-variable-diagnostics`: The existence check RobotCode performs for environment variables (`%{...}`) while analyzing a file, for names with and without nested variables.

### Modified Capabilities

<!-- none -->

## Impact

- `packages/robot/src/robotcode/robot/diagnostics/namespace_analyzer.py`: one additional condition in `_handle_find_variable_result`.
- Tests: `tests/robotcode/robot/diagnostics/test_environment_variable_diagnostics.py` — the three cases that currently run only the `SemanticAnalyzer` because of this gap run both analyzers; new cases for a resolvable name, a resolved value with `=`, list, dictionary and inline Python variables in the name, and documentation. No `_regtest_outputs` baseline changes: no `.robot` file in the LSP test data has an environment variable name with a nested variable.
- No change to the `SemanticAnalyzer`, the semantic model, hover, completion, the VS Code extension, the IntelliJ plugin or the documentation (no page documents the environment variable diagnostic codes).
- Related open changes (no ordering required): `variable-name-resolution-errors` edits another method of `namespace_analyzer.py` and its tests do not look at `EnvironmentVariableNotFound`; `semantic-tokenizer-escapes` keeps the lookup names this change relies on for the `SemanticAnalyzer`. Deciding the Open Question for aligning the `SemanticAnalyzer` changes one scenario of `variable-name-resolution-errors` (design, Open Questions).
