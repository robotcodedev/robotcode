# Design: semantic-tokenizer-escapes

## Context

See proposal.md for the observed effects. Verified facts:

- **Robot Framework.** `_search_variable` in `robot.variables.search` (RF 7.5; the same rule in `VariableSearcher` of RF 5.0.1 and in RF 6.1.1 and 7.0.1) counts a `{`/`}`, and inside items a `[`/`]`, only when it is not escaped: an `escaped` flag flips on every backslash and is cleared by any other character. `_find_variable_start` skips an identifier preceded by an odd number of backslashes (`_not_escaped`). RF's `contains_variable` and RobotCode's `tokenize_variables` (built on RF's search) follow this rule. `contains_variable` is `search_variable(..., ignore_errors=True)`: for text in which a variable is directly followed by an item that is not closed (`cfg_${x}[`, ` ${x}[ `) it finds no variable (RF 5.0.1, 6.1.1, 7.0.1 and 7.5).
- **Where the outer variable comes from.** The `SemanticAnalyzer` finds the variables of a token with `iter_variable_tokens_with_index_access` ([variable_tokenizer.py:115](../../../packages/robot/src/robotcode/robot/diagnostics/semantic_analyzer/variable_tokenizer.py)), that is with RF's tokenizer, and splits item access off with the escape-aware `split_variable_token_index_access` (variable_tokenizer.py:68). So `${A\}${U}}` arrives as one variable. The defect is in how it is split afterwards: `build_variable_occurrence` (variable_tokenizer.py:53) calls `build_variable_sub_tokens` and `normalize_variable_lookup_name`, and nested variables are analyzed only if they appear in the sub-tokens (`iter_related_occurrences`, variable_tokenizer.py:148). The lookup name is used only for the outermost variable: [`_resolve_variable_occurrence`](../../../packages/robot/src/robotcode/robot/diagnostics/semantic_analyzer/analyzer.py) (L4540) looks it up (for a `%{...}` it passes the whole value to `_find_variable`), and `_handle_find_variable_result` (L1925) checks an environment variable found this way when it has no default. With the lookup name `None` nothing is looked up for a non-empty name, except that on RF ≥ 7.0 a name with a nested variable is resolved statically and the result is looked up (from L4559).
- **The spots in variable_tokenizer.py that ignore escapes:**
  - `build_variable_sub_tokens`, closing-brace loop at L371-386: `\}` ends the variable early and the rest after it is dropped (it is neither `=` nor `[`, L389-442); `\{` leaves the variable unclosed and the function returns `[]`.
  - `normalize_variable_lookup_name`, the same loop at L231-244 (left as it is, D4).
  - `_decompose_nested_variable` (L637-727): `str.find` for `${`, `@{`, `&{`, `%{` and the same brace loop. Called from `_decompose_variable_inner` (L524), for inline Python (L342-348) and from `build_index_sub_tokens` (L817-818), each behind a substring check such as `"${" in inner`.
  - `build_index_sub_tokens`, bracket loop at L787-801. Reached only for a value that still carries its items: the REPL passes Robot Framework's whole variable token (`${D}[a\]b]`), the analyzer never does, because items are split off before.
  - `_decompose_env_variable_part` (L730-771, added with 2da6565d for `%{NAME=default}`) already finds nested variables with `iter_variable_tokens_with_index_access`; `test_env_variable_escaped_nested_variable_stays_text` pins that `\${y}` stays text there.
- **Legacy path.** `NamespaceAnalyzer._iter_variables_token` ([namespace_analyzer.py:2163](../../../packages/robot/src/robotcode/robot/diagnostics/namespace_analyzer.py)) re-tokenizes the base of every variable with RF's tokenizer (L2175) and `contains_variable` (L2206), so it follows the escape rule and finds no nested variable in front of an item that is not closed either. `dev-docs/semantic-model.md` expects identical output of both paths while the `semanticModel` flag exists.
- **Consumers.** The language server renders a `VARIABLE` as one semantic token (`_ATOMIC_KINDS`, [semantic_tokens.py:1126](../../../packages/language_server/src/robotcode/language_server/robotframework/parts/semantic_tokens.py)); the decoded variable tokens of the probe file were identical before and after a prototype of this design, with the flag on and off. References and hover in semantic-model mode read the analyzer's references. The REPL lexer ([lexer.py:138](../../../packages/repl/src/robotcode/repl/_pt/lexer.py)) colours the leaves of `build_variable_sub_tokens` and pads a line that came out short with spaces (lexer.py:262-266); it does not use lookup names.
- **Probe results.** `robot` and `robotcode analyze code` on RF 5.0.1, 6.0.2, 6.1.1, 7.0.1, 7.1.1, 7.2.2, 7.3.2, 7.4.2 and 7.5, the same on every version unless noted. "After" is a monkeypatched prototype of D1-D3 with `normalize_variable_lookup_name` unchanged (D4), not project code.

  | Case | Robot Framework | NamespaceAnalyzer | SemanticAnalyzer now | SemanticAnalyzer after |
  |---|---|---|---|---|
  | `%{NE_UNSET=\}${U}}`, `%{NE_UNSET=\{${U}}`, `%{NE_SET=a\}${U}}`, `%{NE_\}${U}=d}`, `${A\}${U}}`, `${A\{${U}}`, `@{A\{${U}}`, a `*** Variables ***` value `%{NE_UNSET=\}${U}}` | fails, "Variable '${U}' not found." | `VariableNotFound` for `${U}` | nothing | `VariableNotFound` for `${U}` |
  | `${ONLY}` used only in `%{NE_UNSET=\}${ONLY}}` | passes | reference | `VariableNotUsed` for `${ONLY}`, no reference | reference |
  | `${A_\${U}}` | fails, "Resolving variable '${A_${U}}' failed: Variable '${A_}' not found." | `${A_}` and `${A_\${U}}` not found | the same plus `${U}` not found | the same as NamespaceAnalyzer |
  | `${{ '\${U}' }}` | passes | nothing | `${U}` not found | nothing |
  | `${A_\\${U}}` | fails, "Variable '${U}' not found." | `${U}` not found | `${U}` not found | `${U}` not found |
  | `${A\}%{NE_UNSET}}`, `%{NE_X=\}%{NE_UNSET}}` ¹ | fails, "Environment variable '%{NE_UNSET}' not found." | `EnvironmentVariableNotFound` for `%{NE_UNSET}` | nothing | `EnvironmentVariableNotFound` for `%{NE_UNSET}` |
  | `${A_\%{NE_UNSET}}`, `${{ '\%{NE_UNSET}' }}` ¹ | the first fails for `${A_}`, the second passes | the first `${A_}` and `${A_\%{NE_UNSET}}` not found, the second nothing | the same plus `EnvironmentVariableNotFound` for `%{NE_UNSET}` | the same as NamespaceAnalyzer |
  | `${cfg_${X}[}`, `${{ ${X}[ }}` ² | fails, "Variable item '${X}[' was not closed properly." (the second `'${X}[ }'`) | the first `${cfg_}` and `${cfg_${X}[}` not found, the second nothing | `${X}` not found | nothing |
  | `${S}` used only in `${cfg_${S}[}` ² | fails, "Variable item '${S}[' was not closed properly." | `VariableNotUsed` for `${S}`, `${cfg_}` and `${cfg_${S}[}` not found | reference | `VariableNotUsed` for `${S}` |
  | `%{NE_\{B}`, `%{NE_\{${S}}` ¹ | passes with `NE_{B` or `NE_{s` set | `EnvironmentVariableNotFound` for the name as written, also when set (for the second no longer with `env-var-check-nested-names`, whose check skips names that contain a variable) | nothing; on RF 7.5 `'%{NE_\{s}'` not found for the second | unchanged |
  | `${ESC_\${U}}` defined in `*** Variables ***` | fails on 5.0.1-7.4.2, passes on 7.5 | nothing | `${ESC_}`, `${ESC_\${U}}` and `${U}` not found | `${ESC_}` and `${ESC_\${U}}` not found |
  | `${B\}}` defined in `*** Variables ***` | fails on 5.0.1-7.4.2 ("Variable '${B}}' not found."), passes on 7.5 | nothing | "Variable '${B\}' not found." and `${B\}}` not found | unchanged |
  | `%{NE_UNSET=a\}b}`, `${S\\}${U}}`, `${S}[\}${U}]`, `${{ '\}' + ${U} }}`, `${A\}${S}}` | the first passes, the others fail | the same as SemanticAnalyzer | already equal to NamespaceAnalyzer | unchanged |

  ¹ Checked on RF 5.0.1 and 7.5. ² Checked on RF 5.0.1, 6.1.1, 7.0.1 and 7.5 (`robot` on 5.0.1 and 7.5).

  The language server in semantic-model mode (RF 7.5, driven in-process) finds references and hover for `${ONLY}` at its use and for `${S}` in `${A\}${S}}` only with the prototype, as the legacy path does without it. The REPL (RF 5.0.1 and 7.5) renders `Log    ${A\}${U}}`, `Log    %{X=a\}b}` and `Log    ${D}[a\]b]` completely only with the prototype.
- **Tests.** No existing test covers an escaped brace or bracket in these functions. With the prototype, `tests/robotcode/robot/diagnostics`, `tests/robotcode/repl/test_lexer.py`, `test_semantic_tokens.py` and `test_semantic_tokens_flag_parity.py` passed on RF 5.0.1, 6.1.1, 7.0.1 and 7.5, and all of `tests/robotcode/language_server` and `tests/robotcode/repl` on RF 7.5, without a `_regtest_outputs` change. The escape values planned for the pipeline comparison (task 2.2) give different results for the two analyzers today and equal ones with the prototype, on RF 5.0.1 and 7.5.

## Goals / Non-Goals

**Goals:**
- Variable ends, item ends and nested variables in the tokenizer's split of a variable match Robot Framework's for escaped braces, brackets and identifiers.
- For these inputs, nested-variable diagnostics and references of the semantic-model path equal the legacy path's.

**Non-Goals:**
- The lookup name of a variable. `normalize_variable_lookup_name` does not change (D4), so neither does how a variable whose own name contains an escape is looked up (`${B\}}`, `${ESC_\${U}}`), nor whether and under which name an outermost `%{...}` is checked for existence. See Open Questions.
- Static resolution of variable names (`_try_resolve_nested_variable_base`): not touched and not extended.
- Any change to the `NamespaceAnalyzer` or to semantic highlighting.
- Finding a nested variable in front of an item that is not closed (`${cfg_${X}[}`); see D3 and Open Questions.

## Decisions

### D1: One helper for the closing brace or bracket, with Robot Framework's escape rule

`variable_tokenizer.py` gets a private `_find_closing_delimiter(value, start, open_char, close_char) -> int`. It scans from `start` with a depth counter and an `escaped` flag as `_search_variable` does, and returns the index of the delimiter that closes the one opened before `start`, or `-1`. `build_variable_sub_tokens` calls it with `{`/`}` from index 2 and returns `[]` on `-1`, as it does today when no closing brace is found; `build_index_sub_tokens` calls it with `[`/`]` from `pos + 1` and stops on `-1`, as today. `normalize_variable_lookup_name` does not use it (D4).

Alternatives considered:
- Adding the escape flag to both loops: two copies of the same rule that can drift apart.
- Robot Framework's `search_variable` for the end of the variable: right for valid variables, but it returns no match for an unclosed item such as `${a}[`, for which the current code still yields the sub-tokens of `${a}` (checked on RF 5.0.1 and 7.5), and it returns items as strings, so `build_index_sub_tokens` would still need its own loop. It changes more than the escape handling.

### D2: Nested variables with Robot Framework's tokenizer

`_decompose_nested_variable` returns the result of `_decompose_env_variable_part(inner, line, col_offset, TokenKind.TEXT_FRAGMENT)` instead of scanning with `str.find` and its own brace loop. That function also yields text fragments and `VARIABLE` tokens with their sub-tokens whose leaves cover every character, but takes the start and end of each nested variable from RF's tokenizer, so `\${x}` stays text and escaped braces inside a nested variable are handled as in Robot Framework. Because RF's tokenizer splits an item after a nested variable off the following text, that text can come out as two fragments where the loop made one: `[0]` and ` ` in `${{ ${a}[0] }}`, before `[0] ` (checked with the prototype); both are `TEXT_FRAGMENT`s and are coloured alike in the REPL. `_decompose_nested_variable` keeps its name and signature for its three callers. `_decompose_env_variable_part` returns `None` only for text without a variable, which D3 rules out for these callers; the empty list covers that case for the type checker.

Alternatives considered:
- An escape check in the `str.find` loop: a second implementation of RF's `_not_escaped` next to a function in the same file that already uses RF's tokenizer.
- Renaming `_decompose_env_variable_part` to a neutral name: not needed for the fix.

### D3: "Contains a variable" checks with Robot Framework's `contains_variable`

The three substring checks that decide whether text is split into nested variables, for the variable name in `_decompose_variable_inner` (L524), the inline Python expression (L342) and the item content in `build_index_sub_tokens` (L817), use `contains_variable` (already imported from `robotcode.robot.utils.variables`) with the identifiers each check uses today (`$@&%`, `$@&%`, `$@&`). `${A_\${U}}` then takes the extended-syntax path, as its lookup name `${A_}` already does (base `A_`, extended part `\${U}`); `${A_}` is also the variable Robot Framework reports for it. `${{ '\${U}' }}` gets no nested variable, and `[\${x}]` stays item content. An item whose content holds only an environment variable (`[%{E}]`) stays item content, and `[${i}%{E}]` still yields both nested variables, as today (checked with the prototype).

The result changes for escaped variables and for one more kind of text: a nested variable directly followed by an item that is not closed (`cfg_${x}[` in `${cfg_${x}[}`, ` ${x}[ ` in `${{ ${x}[ }}`). `contains_variable` finds no variable there (see Context), and D2 would find none either. On the semantic-model path an undefined `${X}` there is no longer reported, a defined `${S}` used only in `${cfg_${S}[}` is no longer recorded as a reference and is reported as not used, and references and hover lose that use; the REPL colours `${cfg_${x}[}` as the base `cfg_` with the extended part `${x}[`, and ` ${x}[ ` as plain expression text. This is the legacy path's result for the nested variable (Context, probe results), and Robot Framework rejects these lines ("Variable item '${X}[' was not closed properly.").

D1 rejects `search_variable` for a different question: there it would change what `build_variable_sub_tokens` returns for a value it is given, such as `${a}[`. D2 and D3 decide whether text inside a variable contains a nested variable, and the goal there is the legacy path's answer, which comes from the same Robot Framework functions. Keeping today's result for an unclosed item would need an own escape-aware scanner (the first alternative of D2) that differs from the legacy path; see Open Questions.

Alternative considered: keeping the substring checks and relying on D2 alone. No `${U}` would be reported either, but the name `A_\${U}` and the whole inline Python expression would each become one text fragment, the latter next to the expression's `$var` references.

### D4: Lookup names unchanged

`normalize_variable_lookup_name` keeps its brace loop, which ignores escapes, so the lookup names stay as they are: `${A\}` for `${A\}${U}}`, `${B\}` for `${B\}}`, `None` for `${A\{${U}}`, `%{X=\{${U}}` and `%{NE_\{B}`. They are used only for the outermost variable (Context); nested variables come from the sub-tokens. For the inputs of the spec the outermost variable gets no diagnostic, as today: `${A\}` is not found and the name contains a variable, so nothing is reported ([analyzer.py:4608](../../../packages/robot/src/robotcode/robot/diagnostics/semantic_analyzer/analyzer.py)); with `None` and an undefined nested variable nothing is reported either, on RF ≥ 7.0 because the static resolution stops at the variable that is not found. Sub-tokens and lookup name can so disagree about where a variable with an escaped brace ends.

Alternative considered: applying D1 in `normalize_variable_lookup_name` too. Checked with a prototype on RF 5.0.1 and 7.5, it changes the lookup names of names that contain an escape, partly through the existing extended-syntax split, which takes the backslash for an operator:
- `%{NE_\{B}` and `%{NE_\{${S}}` get the lookup name `%{NE_}` instead of `None`, so the semantic-model path checks the environment variable under the escaped name as written and reports `EnvironmentVariableNotFound` as the legacy path does: correct when `NE_{B` is not set, false when it is, where Robot Framework passes. It would also end what the open change `env-var-check-nested-names` relies on: that the `SemanticAnalyzer` never checks a name with an unresolved nested variable.
- `${name\}}` with `${name}` defined: both `VariableNotFound` errors disappear and a reference to `${name}` is recorded, although Robot Framework fails with "Variable '${name}}' not found." and does not try `${name}`.
- `${A\{B}` gets two new `VariableNotFound` errors, for `${A}` and `${A\{B}` (Robot Framework: "Resolving variable '${A{B}' failed: Variable '${A}' not found."), and `${A\}B}` is reported as `${A}` instead of `${A\}`.
- In exchange, `${name\}${S}}` and `%{X=\{${S}}` would record references to `${name}` and `%{X}`, as the legacy path does.
That is name resolution rather than tokenization; see Open Questions.

### D5: Tests

- Unit tests for the tokenizer in `test_variable_tokenizer.py`: sub-tokens and positions, nested occurrences present or absent, odd and even backslash counts, the unclosed-item result of D3, and lookup names that stay as they are (D4).
- Analyzer tests in a new focused module `tests/robotcode/robot/diagnostics/test_variable_escapes.py`, parametrized over both analyzers as `test_environment_variable_diagnostics.py` is: the spec scenarios with diagnostic codes, messages and positions, and the references of a defined variable. Environment variables are set and removed with `monkeypatch`.
- The escape values whose outermost variable both analyzers already treat alike as new entries of `test_semantic_and_namespace_variable_pipeline_match` in `test_variable_pipeline_comparison.py`. That test compares all references, including the outermost variable's, so `${name\}${idx}}`, `${name\}}` and `%{HOME=\{${idx}}` stay out: their outermost lookups differ between the paths before and after this change (D4, Open Questions).
- REPL: `_split_variable` and `lex_document` cases in `tests/robotcode/repl/test_lexer.py`.
- No new lines in the LSP test data, so no regression baseline changes. References and hover read the analyzer's references, which the analyzer tests cover.

## Risks / Trade-offs

- [New `VariableNotFound` and `EnvironmentVariableNotFound` errors on the semantic-model path for nested variables that were silent] → only where Robot Framework fails with the same message and the legacy path already reports it (probe results); suppressible with the diagnostics modifiers.
- [Nested variables in front of an item that is not closed are no longer found on the semantic-model path (`${cfg_${X}[}`)] → Robot Framework rejects these lines, and the legacy path does not report or record the nested variable either; pinned by a tokenizer test (task 1.2); see Open Questions.
- [Sub-tokens and lookup name disagree about where a variable with an escaped brace ends] → only the outermost variable's lookup uses the lookup name, and its result stays as today (D4).
- [RobotCode's own copy of the escape rule (D1) could drift from Robot Framework's] → the rule is the same from RF 5.0.1 to 7.5; D2 and D3 use Robot Framework's functions; the tests pin odd and even backslash counts.
- [The false errors for names that contain an escape stay on RF 7.5] → out of scope, see Open Questions.

## Migration Plan

Bug fix without data or configuration changes; rollback by reverting the commit.

## Open Questions

- Names that contain an escape (`${B\}}`, `${ESC_\${U}}` defined in `*** Variables ***` and used as written): RF 7.5 finds them, RF 5.0.1 to 7.4.2 fail, the legacy path reports nothing on every version (it looks the full name up first, namespace_analyzer.py:2232), and the semantic-model path reports two `VariableNotFound` errors on every version, before and after this change, and reports the definitions as not used. Aligning the semantic-model lookup with the legacy path, and whether that should depend on the Robot Framework version, is name resolution rather than tokenization and is left for a follow-up.
- Should `normalize_variable_lookup_name` follow the escape rule as well (the alternative of D4)? It would record the references of the legacy path for `${name\}${S}}` and `%{X=\{${S}}`, but needs decisions this change does not make: whether an environment variable name with an escaped `{` is checked, and under the escaped name as the legacy path does (false errors when the unescaped name is set) or not at all as today; how the extended-syntax split should treat a backslash (`${name\}}`); and how it fits `env-var-check-nested-names`, whose design relies on the lookup name `None` for an environment variable name with an unresolved nested variable.
- Nested variables in front of an item that is not closed: keep this change's result, which is the legacy path's and gives no diagnostic where Robot Framework fails with a syntax error, or keep today's semantic-model result (`${X}` reported, `${S}` recorded) with an own escape-aware scanner that differs from the legacy path?
