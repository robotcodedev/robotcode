# Design: env-var-completion-keep-default

## Context

See proposal.md for the problem. Verified facts:

- **Language server.** Completion inside a variable is handled at the end of `complete_default` ([completion.py:1113](../../../packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py)). It looks at the last `{` before the cursor and continues only if no `}` lies between that brace and the cursor and a `$`, `@`, `&` or `%` precedes it. `variable_end` is the first `}` after the brace ([completion.py:1186](../../../packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py)). `contains_spezial` is true when a `+`, `-`, `*` or `/` lies between the brace and that `}` (or the end of the token). The edit range starts after the brace and ends at the cursor if `contains_spezial` is true or there is no `}`, and at `variable_end` otherwise. For `%` the range goes to `create_environment_variables_completion_items` ([completion.py:584](../../../packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py)), which builds one `TextEdit` per name in `imports_manager.environment`. None of this knows about `=`. `=` is also a trigger character ([completion.py:149](../../../packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py)), and VS Code closes `%{` automatically ([language-configuration.json](../../../language-configuration.json)), so typing `=` there requests completion at `%{NAME=|}`.
- **Observed** with the language server driven in-process (flag off and on give the same result), accepting `ENV_VAR`:

  | Cursor | Replaced text | Result |
  |---|---|---|
  | `%{NO\|PE_EMPTY_DEFAULT=}`, `%{NOPE_EMPTY_DEFAULT=\|}` | `NOPE_EMPTY_DEFAULT=` | `%{ENV_VAR}` |
  | `%{NO\|PE=abc}`, `%{NOPE\|=abc}`, `%{NOPE=\|abc}`, `%{NOPE=ab\|c}`, `%{NOPE=abc\|}` | `NOPE=abc` | `%{ENV_VAR}` |
  | `%{NO\|PE=/tmp}` | `NO` | `%{ENV_VARPE=/tmp}` |
  | `%{NE\|_UNSET=${S}}` | `NE_UNSET=${S` | `%{ENV_VAR}}` |
  | `%{NOPE=\|` (unclosed) | `NOPE=` | `%{ENV_VAR` |
  | `%{NO\|PE=` (unclosed) | `NO` | `%{ENV_VARPE=` |
  | `%{NO\|PE}`, `%{\|}` | `NOPE`, nothing | `%{ENV_VAR}` |
  | `%{MY-\|VAR}` | `MY-` | `%{ENV_VARVAR}` |
  | `%{NE\|_${S}=d}` | `NE_${S` | `%{ENV_VAR}=d}` |
  | `%{A\|_${B=x}}` | `A_${B=x` | `%{ENV_VAR}}` |
  | `x%{NO\|PE}y%{B=c}` | `NOPE` | `x%{ENV_VAR}y%{B=c}` |
  | `%{NE_UNSET=${\|S}}` | `S` (variable item `S`) | unchanged |

- **Robot Framework.** `EnvironmentFinder.find` partitions the variable base at the first `=` into name and default (RF 5.0 and 7.5 sources); a suite run on RF 5.0, 6.1, 7.0 and 7.5 confirms `%{NOPE_EMPTY_DEFAULT=}` → empty string, `%{NOPE==x}` → `=x`, `%{NE_UNSET=${S}}` → the value of `${S}`. Extended variable syntax (`ExtendedFinder`) applies only to `$`, `@` and `&`, not to `%`.
- **LSP.** The text edit's range of a completion item must be a single line and must contain the position at which completion was requested ([types.py:2559](../../../packages/core/src/robotcode/core/lsp/types.py)).
- **SemanticModel.** The variable tokenizer splits `%{NAME=default}` into `VARIABLE_BASE`, `VARIABLE_DEFAULT_SEPARATOR` and `VARIABLE_DEFAULT_VALUE` at the first `=` outside nested variables ([variable_tokenizer.py:469](../../../packages/robot/src/robotcode/robot/diagnostics/semantic_analyzer/variable_tokenizer.py)). The innermost token of `token_path_at()` (a token contains `col_offset <= col < col_offset + length`, [model.py:155](../../../packages/robot/src/robotcode/robot/diagnostics/semantic_analyzer/model.py)) is `VARIABLE_BASE` with the cursor in the name, `VARIABLE_DEFAULT_SEPARATOR` with the cursor directly before the `=`, `VARIABLE_DEFAULT_VALUE` with the cursor at or inside a non-empty default (`%{NOPE=|abc}`), and `VARIABLE_CLOSE_BRACE` with the cursor directly before the `}`: at `%{NOPE|}`, `%{NOPE=|}` and `%{NOPE=abc|}` alike. An unclosed variable has no `VARIABLE` sub-tokens: the path is only the `ARGUMENT` at `%{NO|PE=` and the `EOL` at `%{NOPE=|` (observed). `completion.py` does not use the SemanticModel today.
- **REPL.** `tokenize` classifies only the text before the cursor ([completion.py:212](../../../packages/repl/src/robotcode/repl/_pt/completion.py)), `_RobotCompleter` replaces from `replace_start` to the cursor ([components.py:162](../../../packages/repl/src/robotcode/repl/_pt/components.py)), and every `%{` candidate is the complete `%{NAME}` ([completion.py:389](../../../packages/repl/src/robotcode/repl/_pt/completion.py)). Applied through prompt_toolkit's `Buffer.apply_completion`, `Log  %{EN|=abc}` becomes `Log  %{ENV_VAR}=abc}`, and with the cursor after the `=` nothing matches. The default is never removed; the stray `}` comes from completing in the middle of a closed variable and happens the same way for `${OUT|PUT_DIR}` → `${OUTPUT_DIR}PUT_DIR}`. So the REPL does not have this defect.
- **Tests.** There is no completion regression test and no completion baseline in `_regtest_outputs`. Focused completion tests (`test_completion_builtin_variables.py`, `test_completion_argument_docs.py`) open a suite written to `tmp_path` through the session `protocol` fixture, whose `robot.env` contains `ENV_VAR=1` ([conftest.py](../../../tests/robotcode/language_server/robotframework/parts/conftest.py)); that name is offered for such documents as well.

## Goals / Non-Goals

**Goals:**
- Choosing a name in `%{NAME=default}` changes only the name.
- No environment variable names where accepting one would have to overwrite the default.

**Non-Goals:**
- Names with nested variables (`%{NE_${S}=d}`): the range still ends at the first `}`, as for `${A_${S}}`. Resolving or delimiting nested names is not pursued here.
- The `+-*/` rule for the name itself (`%{MY-|VAR}` → `%{ENV_VARVAR}`), see Open Questions.
- The REPL (see Context), including its behavior when completing in the middle of a closed variable.
- Completion inside the default (e.g. offering values), `InsertReplaceEdit`, changes to the items themselves.

## Decisions

### D1: The first `=` ends the name, within the variable at the cursor

For a variable opened with `%{`, the language server looks for the first `=` between the brace and `variable_end`, or the end of the token when there is no `}`. If there is one, that index is used as the end of the name in place of `variable_end`: the `+-*/` scan runs only over the name, and the range ends at the `=` unless that scan finds one of the characters, in which case it ends at the cursor as for `%{NAME}` today. Without a `=`, and for `$`, `@` and `&`, nothing changes. This is what the spec requires ("the range the same position gets in `%{NAME}`").

For names without nested variables the first `=` is where Robot Framework splits the base and where the SemanticModel ends `VARIABLE_BASE`. Bounding the search by `variable_end` keeps a `=` in a later variable of the same argument (`x%{NO|PE}y%{B=c}`) out of it and leaves nested names on today's range as long as there is no `=` before the first `}`. For `%{A_${B=x}}` the `=` of the nested variable lies before that `}` and now ends the range (Risks).

Alternatives considered:
- Robot Framework's `search_variable` on the token to find the variable at the cursor and split `match.base`: a second way of locating the variable next to the brace scan that all sigils use, for one sigil.
- The SemanticModel's `VARIABLE_BASE` via `token_path_at()`: exists only with the flag on and is the subject of `semantic-model-completion`; using it here would make the two flag states differ.
- An `InsertReplaceEdit`: depends on a client capability and changes the shape of every item, while the problem is only the end of the range.

### D2: No environment variable names after the `=`

With the cursor after the first `=`, the `%{` case returns no items. A range that ends at the `=` would not contain the cursor, which LSP does not allow, and a range from the name to the cursor would overwrite part of the default. A variable written in the default has its own brace, which is then the last `{` before the cursor, so it is completed as that variable and `%{NE_UNSET=${|S}}` still gets variable items.

Alternative considered: keep offering names with today's range — this is the defect.

### D3: A focused test module

`tests/robotcode/language_server/robotframework/parts/test_completion_environment_variables.py` writes one suite per case to `tmp_path`, requests completion through the session `protocol` fixture, applies the text edit of the `ENV_VAR` item to the line and compares the line with the spec scenario (or asserts that no `ENV_VAR` item is offered). `ENV_VAR` comes from the fixture's `robot.env`, so the test does not depend on the process environment or the platform. Nothing is added to the LSP data files, so no regression baseline moves.

### D4: Flag parity and `semantic-model-completion`

`semantic-model-completion` requires identical completion items under both flag states (labels, kinds, sort text, insert text and edit ranges). Because `completion.py` has no SemanticModel branch today, the fix in `complete_default` applies under both flag states and parity holds without further work. The fixed behavior is the reference the later model path has to match.

The innermost token of `token_path_at()` cannot tell the name from the default (Context): `VARIABLE_CLOSE_BRACE` is the innermost token at `%{NOPE|}`, where names are offered, and at `%{NOPE=|}` and `%{NOPE=abc|}`, where they are not. A model branch therefore has to decide by position within the variable token these sub-tokens belong to: a cursor column less than or equal to the `col_offset` of its `VARIABLE_DEFAULT_SEPARATOR` (the cursor directly before the `=`) is in the name, a greater one is in the default, whatever the innermost token is. The edit range has to be the one D1 computes. An unclosed variable (`%{NO|PE=`, `%{NOPE=|`) has no `VARIABLE` sub-tokens, so the model branch has to handle it separately or leave it on the legacy computation; which of the two is for `semantic-model-completion` to decide. For nested names the model's `VARIABLE_BASE` (`NE_${S}`) and the legacy range (`NE_${S`) differ already today; this change does not touch that, and whether it becomes a reasoned deviation is also for `semantic-model-completion` to decide.

`semantic-model-completion` compares both flag states over "all existing completion test positions". If it is implemented after this change, its flag-on run has to include `test_completion_environment_variables.py`; otherwise nothing checks its model path against the behavior fixed here. If it is implemented first, the rule goes into its model branch and the new module also runs against a flag-on protocol (task 3.1).

## Risks / Trade-offs

- [Positions in the default, including the one right after typing `=` (a trigger character), no longer get environment variable names] → intended: accepting one of them would have replaced the default.
- [A `=` inside a nested variable before the first `}` of a nested name, such as `%{A_${B=x}}`, is taken as the end of the name] → the range now ends at that `=` (`%{ENV_VAR=x}}`), where today it ends at the first `}` (`%{ENV_VAR}}`); either way a stray `}` remains. Nested names are out of scope (Open Questions).
- [The model path of `semantic-model-completion` decides by the innermost token and offers names at `%{NOPE=|}` or `%{NOPE=abc|}`, or mishandles the unclosed variable] → D4 describes the tokens and the position rule; the new test module is the check once it runs with the flag on.

## Migration Plan

No data or setting changes. Rollback is reverting the change.

## Open Questions

- Should the `+-*/` rule apply to environment variable names at all? Robot Framework's extended variable syntax does not apply to `%{…}`, and the rule makes `%{MY-|VAR}` become `%{ENV_VARVAR}`. Changing it would alter completion for names without a default, which is outside this change.
- Nested names (`%{NE_${S}=d}`, and `${A_${S}}` alike) get a range that ends at the first `}` and leave a stray `}` after completion. Whether and how completion should delimit a nested name is open.
- The REPL leaves the text after the cursor untouched and inserts a complete `%{NAME}` / `${NAME}`, so completing in the middle of a closed variable leaves the old tail and a stray `}` for every sigil. Whether that is worth a change of its own is open.
