# Proposal: env-var-completion-keep-default

## Why

Completing an environment variable name inside `%{NAME=default}` removes the default. The edit range of the offered items runs from after `%{` to the first `}` ([completion.py:1186](../../../packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py)), so accepting `ENV_VAR` with the cursor at `%{NO|PE_EMPTY_DEFAULT=}` gives `%{ENV_VAR}`, and at `%{NO|PE=abc}` also `%{ENV_VAR}`: the `=` and the default are gone. Robot Framework takes everything after the first `=` as the default (`EnvironmentFinder` partitions the variable base at the first `=`, the same on RF 5.0 and 7.5), so accepting an item changes more than the name: the variable loses the value it falls back to when it is not set.

Two variants of the same cause: a default that contains `+`, `-`, `*` or `/` (`%{NOPE=/tmp}`) makes the range end at the cursor, so `%{NO|PE=/tmp}` becomes `%{ENV_VARPE=/tmp}`; a default that contains a variable (`%{NE_UNSET=${S}}`) makes the range end at the `}` of `${S}`, so the result is `%{ENV_VAR}}`. Observed by driving the language server in-process with the `semanticModel` flag off and on; both give the same ranges, because completion has no SemanticModel branch yet.

## What Changes

- When the content of `%{…}` has a `=`, completing an environment variable name replaces only the name between `%{` and the first `=`. The `=` and the default stay as they are. This holds for an empty default, a default with `+`, `-`, `*`, `/` or variables in it, and for `%{NAME=` whose closing brace is still missing. The range is the one the same position gets in `%{NAME}`.
- With the cursor after the first `=`, that is in the default, no environment variable names are offered. This includes the position right after `=` in an empty default (`%{NAME=|}`), where typing `=` inside an automatically closed `%{}` requests completion, the end of a default and a variable whose closing brace is still missing. An item's edit range has to contain the cursor position ([types.py:2559](../../../packages/core/src/robotcode/core/lsp/types.py)), and a range that covers only the name cannot. Variable completion for a variable written in the default, such as `${|S}` in `%{NE_UNSET=${S}}`, stays as it is.
- Unchanged: `%{NAME}` and `%{}` without a default, the items themselves (label, kind, sort text, new text), completion in `${…}`, `@{…}` and `&{…}`, and names with nested variables that have no `=` before the first `}` (`%{NE_${S}=d}`), whose range still ends at that `}`. When the nested part has a `=` before the first `}` (`%{A_${B=x}}`), that `=` now ends the range (see design.md, Risks).
- The REPL is not changed. It replaces only the text before the cursor, so it never removes a default (see design.md).

## Capabilities

### New Capabilities

- `environment-variable-completion`: Which part of `%{NAME=default}` an environment variable completion item replaces, and where inside `%{…}` environment variable names are offered.

### Modified Capabilities

<!-- none -->

## Impact

- `packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py`: the `%{` case in `complete_default`, nothing else.
- Tests: new `tests/robotcode/language_server/robotframework/parts/test_completion_environment_variables.py`. There are no completion regression baselines, so no `_regtest_outputs` change.
- No change to docs, the VS Code extension, the IntelliJ plugin or the REPL.
- Works with the open change `semantic-model-completion`, which requires the same completion items under both flag states: the fixed behavior is the one its model path has to reproduce. See design.md.
