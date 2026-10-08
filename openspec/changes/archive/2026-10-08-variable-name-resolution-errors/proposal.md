# Proposal: variable-name-resolution-errors

## Why

On Robot Framework 7.0 and newer both analyzers try to resolve variable names with nested variables statically ([`_try_resolve_nested_variable_base`](../../../packages/robot/src/robotcode/robot/diagnostics/namespace_analyzer.py)), so that `${NESTED ${A}}` with `${A}` = `1` defines `${NESTED 1}`. For an environment variable inside such a name, [`_resolve_variable_to_string`](../../../packages/robot/src/robotcode/robot/diagnostics/namespace_analyzer.py) takes the text between `%{` and `}` as written: it splits it at the first `=`, looks the unresolved name up in the environment and, if it is not set, returns the unresolved default. Robot Framework first replaces the variables in the whole `%{...}` text and only then splits it and looks the name up. Checked with `robot` on Robot Framework 7.0.1 and 7.5, this produces errors and wrongly named variables where Robot Framework passes:

- `${X_%{NE_A_${S}}}    v` in `*** Variables ***`, with `${S}` = `suffix` and `NE_A_suffix` set, passes in Robot Framework and defines `${X_1}`. Both analyzers report the error `VariableNameNotResolvable` ("Setting variable '${X_%{NE_A_${S}}}' failed: Variable '%{NE_A_${S}}' not found."). The same happens in a `VAR` statement and in an assignment (`${Q_%{NE_A_${S}}}=    Set Variable    q`), and for a variable whose value contains such an environment variable (`${A}    %{NE_A_${S}}`, then `${V_${A}}    v` reports "Variable '${A}' not found.").
- `${Y_%{NE_X=${S}}}    v` with `NE_X` unset defines `${Y_suffix}` in Robot Framework. The analyzers define a variable named `${Y_${S}}` and report it as not used.
- The reference `${NAME_%{NE_X=${S}}}` is looked up as `${NAME_${S}}`, which never exists, and is dropped without a diagnostic, so `${NAME_suffix}` is reported as not used.

Resolving variable names statically is limited on purpose, and this change does not extend it. Where the analyzer cannot know the result, it reports the existing hint for names it cannot resolve instead of an error or a variable under a name with unresolved text. A default without variables behind an environment variable name with a variable (`%{NE_${S}=fb}`) keeps today's result, the default, since the hint there would add errors on the uses of the name where Robot Framework passes when the resolved environment variable is not set (see design, D1).

## What Changes

- On Robot Framework 7.0 and newer, an environment variable inside a variable name, directly or through the value of another variable, counts as not statically resolvable when its name contains a variable and it has no default or a default with a variable (`%{NE_A_${S}}`, `%{%{NE_N}}`, `%{NE_${S}=${T}}`), or when it is not set and its default contains a variable (`%{NE_X=${S}}`).
- An environment variable whose name contains a variable and whose default contains none (`${N_%{NE_${S}=fb}}`, `${USED_%{NE_${S}=fb}}`) still resolves to its default, as today, also when the resolved environment variable (`NE_suffix`) is set; see design, Risks and Open Questions.
- A declaration with such a name (`*** Variables ***`, `VAR`, assignment of a keyword call or an inline `IF`) gets the existing hint `VariableNameNotStaticallyResolvable` instead of the error `VariableNameNotResolvable` or a definition under a wrong name. No variable is defined for it, as for every other name that cannot be resolved statically.
- A reference with such a name gets the existing hint `VariableReferenceNotStaticallyResolvable`. Before, it was dropped without a diagnostic.
- Unchanged: an environment variable whose name contains no variable is resolved as today (set: its value, unset with a default without variables: the default, unset without default: the error stays). Variables nested in the environment variable keep their own diagnostics (`VariableNotFound`, `EnvironmentVariableNotFound`). An undefined variable nested directly in a name stays an error. An escaped `\${S}` is not a variable. Nothing changes on Robot Framework older than 7.0.
- Uses of the name Robot Framework defines at run time (`${X_1}`) still get `VariableNotFound`, and variables used only through such names are still reported as not used, as today for every name that cannot be resolved statically (for example `${X_${{1}}}`); see design, Open Questions.
- Both analysis paths (the legacy `NamespaceAnalyzer` and the `SemanticAnalyzer` of the semantic model) behave identically, except for references whose outer variable is `%{...}`: for `%{%{NE_N_${S}}=x}` only the `SemanticAnalyzer` reports the hint, as it already does for other `%{...}` references with a nested value it cannot resolve (`%{NE_${{1}}=x}`).

## Capabilities

### New Capabilities

- `variable-name-resolution`: Which diagnostics RobotCode reports for variable names and references with nested variables that it resolves statically on Robot Framework 7.0 and newer, here for environment variables inside such names: the existing hint instead of an error or a name with unresolved text where the analyzer cannot know the result, today's result otherwise.

### Modified Capabilities

<!-- none -->

## Impact

- `packages/robot/src/robotcode/robot/diagnostics/namespace_analyzer.py` and `semantic_analyzer/analyzer.py`: the branch for `%{...}` in `_resolve_variable_to_string`. No caller changes.
- Tests: `tests/robotcode/robot/diagnostics/test_semantic_analyzer/test_nested_variable_resolution.py`, new cases for both analyzers on Robot Framework 7.0 and newer and one for older versions. No `_regtest_outputs` baseline changes: no `.robot` file in the LSP test data has an environment variable with a nested variable inside a variable name, and a prototype of the change passed `tests/robotcode/robot/diagnostics` and `tests/robotcode/language_server` unchanged on Robot Framework 7.5.
- No change to the documentation (no page in `docs/` documents these codes), the semantic model, hover, completion, the VS Code extension or the IntelliJ plugin.
- Related open changes (no ordering required): `env-var-check-nested-names` removes the `NamespaceAnalyzer`'s `EnvironmentVariableNotFound` for the unresolved nested name, which the tests of this change filter out; if it decides its Open Question for aligning the `SemanticAnalyzer`, the scenario for `%{...}` references here changes with it (design, D3).
