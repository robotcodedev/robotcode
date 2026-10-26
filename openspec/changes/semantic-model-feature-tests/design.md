# Design: semantic-model-feature-tests

## Context

See proposal.md for the motivation. The LSP features with a model branch read the `SemanticModel` of the namespace when the model is on and fall back to the legacy path otherwise:
- the semantic tokens (`collect_tokens_from_model`);
- inlay hints and signature help;
- the documentation actions, Create Keyword and Assign keyword result to variable;
- selection ranges, inline values and debug expressions, through the shared candidate extraction in `model_variables.py`.

What tests them today:
- the `test_*_model.py` suites, which compare the model branch with the legacy path on their own cases;
- `test_semantic_tokens_flag_parity.py`, which compares the tokens of the LSP test data on both paths;
- the regtest recordings, which run on the legacy path. The signature help and documentation action recordings never ran with the model on;
- a few tests with expectations of their own: `test_semantic_tokens_variables.py`, parts of `test_documentation_target.py` and `test_signature_help_documentation_links.py`.

The rules in the specs of this change come from a review of the model path:
- its code;
- probes with the language server on both paths, Robot Framework 5.0.1 to 7.5;
- the User Guides and the BuiltIn documentation of these versions.

The review also found the regressions of D4, the differences of D5 and the findings of D7.

The test session shares one language server on `tests/.../parts/data`. `open_temp_document` opens files outside its workspace, and tests switch the model on with `monkeypatch.setattr(protocol.documents_cache.analysis_config, "semantic_model", True)`. Inlay hints are produced only for documents in a workspace folder (`RobotInlayHintProtocolPart.get_config`), so a file outside the workspace gets none.

## Goals / Non-Goals

**Goals:**
- Every scenario of the specs of this change is a test on the model path.
- When the switchover flips the default, users get no regression from the review.
- The allowed differences are written down where the switchover and the cleanup look for them.

**Non-Goals:**
- No change to the legacy path: `NamespaceAnalyzer`, `ModelHelper`, `KeywordTokenAnalyzer` and the `else` branches keep their bugs.
- No fixes in code without a model branch. That code is Surround, Extract Keyword, Disable for this line, Create local and suite variable, Add argument, the UTF-16 conversion of code action ranges and the number of selection range results. Its fixes come as small changes of their own.
- No behavior that is decided to change after the cleanup, and no behavior that is still missing (D2).
- No Level-D fixture and no flip of the default; both are `semantic-model-switchover`.
- No tests of the legacy path.

## Decisions

### D1: One test per scenario, on the model path, through the handlers

- **Modules:** one module per feature next to the existing ones:
  - `test_semantic_tokens_rules.py`, `test_inlay_hint_rules.py`, `test_signature_help_rules.py`;
  - `test_selection_range_rules.py`, `test_inline_value_rules.py`, `test_debug_expressions_rules.py`;
  - `test_code_action_quick_fixes_rules.py`, `test_code_action_refactor_rules.py`;
  - `test_keywords_that_run_keywords_rules.py`, which reads the diagnostics of the namespace.

  The documentation actions get their new scenarios in `test_documentation_target.py`.
- **One test per scenario**, named after it. A Robot Framework version in a scenario becomes a skip marker on `RF_VERSION`, so `hatch run test:test` runs each test on every version where it applies.
- **Through the public handlers:**
  - `collect` of the protocol parts and `resolve` of the code actions;
  - `collect_full` of the semantic tokens, decoded per line as in `test_semantic_tokens_variables.py`;
  - the request `robot/debugging/getEvaluatableExpression`.

  The tests do not call `_collect_from_model` or other helpers of the model branch, so they stay unchanged when the cleanup collapses the branches.
- **A language server with the model on.** One session-scoped server runs on a temporary workspace, with the model switched on in the editor settings as in `test_semantic_tokens_variables.py`. A fixture writes the files of a test, its suite and any Python library or resource it needs, into a directory of the test's own inside that workspace. It opens the suite, checks that its namespace has a `SemanticModel` and closes the documents afterwards.
  - The files are inside the workspace because inlay hints need a workspace folder.
  - One server serves all modules, as with the shared `protocol` fixture, instead of one start per module.
  - The check that the model is on is the vacuity guard: without it, a test could pass on the legacy path.
- **Inline values:** the tests send the stopped location that VS Code sends for RobotCode's stack frames: an empty range at the start of the stopped line, because the frames have a line and column 1 and no end. The scenarios stop on statements that begin at the start of their line. Values for statements that begin later on the stopped line, such as inline IF branches, change after the cleanup.

*Alternative considered:* extend the `test_*_model.py` suites with expectations. Rejected: they test the helpers of the model branch with hand-built libraries, and the cleanup removes their comparisons (`semantic-model-cleanup` D4).

### D2: Only what is right today or after D4 is pinned

The specs pin the behavior that is right today or after the fixes of D4. The scenarios avoid what changes later, and the tests assert nothing about it:

- **Rules decided to change after the cleanup:**
  - parameter names: positional-only parameters, variable-length parameters, and named arguments of Run Keyword variants in hints and signature help;
  - the separator width in signature help;
  - selection ranges: the steps between name and cell, merged steps, and the scan after `${}`;
  - inline values: which occurrences get values, with what label, and how the stopped line is cut;
  - debug expressions: definitions in `[Arguments]`, environment variables with defaults, and names that cannot be resolved statically;
  - the documentation target of a selected call name, of a prefix and of an alias;
  - semantic tokens: variable tokens in option values, keyword names from variables, the BDD lookup on Robot Framework 7.0, `AS` in `EXCEPT … AS`, and embedded arguments with their own pattern (Robot Framework 7.3 and newer) together with the character after an embedded value.
- **Behavior that is still missing:**
  - hints and signatures in template rows and for the arguments of inner calls;
  - `Import Library` with the parameters of the library;
  - `$var` in BuiltIn expressions, and item and attribute access;
  - variables with a scope other than local.
- **Token rendering that `semantic-model-token-rendering` changes:** the BDD separator token, documentation and metadata, comments, the text of template rows, and escapes.
- **Work of other changes:**
  - `Variables` imports, which belong to `variables-import-signature`;
  - Disable for this line, which belongs to `disable-diagnostic-for-line`;
  - the code without a model branch.

Where a rule touches one of these, the scenario uses a case that does not. For example, the inlay hint scenarios use keywords without positional-only parameters, and the inline value scenarios stop on single-line statements.

### D3: Specs by feature, not by analysis path

The tokens other than variable names extend `semantic-highlighting`, which already holds the variable tokens of both paths. Each other feature gets a capability named after it: `inlay-hints`, `signature-help`, `selection-ranges`, `inline-values`, `debug-expressions`, `code-action-quick-fixes` and `code-action-refactorings`. Which arguments the analysis takes as keyword names gets `keywords-that-run-keywords`; `semantic-model-keyword-arguments` extends it later. The documentation actions stay in `vscode-documentation-viewer` and `semantic-model-hover`. Each spec states that its rules hold for the semantic-model path. Where the model path answers differently from the legacy path, a requirement "Differences from the legacy path" names each case (D5).

*Alternative considered:* one capability for all features on the model path. Rejected: after the cleanup the model path is the only one, and the rules belong to the features.

### D4: The 29 regressions are fixed in the model path only

Each fix changes the analyzer (`semantic_analyzer/`) or the model branch of a feature, never the legacy path, and comes with the scenario tests that pass with the fix and fail without it. Afterwards the model path answers like the legacy path at these places, except for QF3, QF4 and ST26, which go beyond it (D5), so the comparison tests stay green. The labels are used in tasks.md.

Shared causes:

| Cause | Fix | Labels |
|---|---|---|
| The analyzer drops arguments with an empty value, so the following arguments slip to the wrong parameter. | Keep empty argument tokens in the model. | IH5 (inlay hints), SH4 (signature help) |
| `statement_at` returns the first statement of a line, also where an inline IF holds a call or a keyword header holds a step. | Take the call at the column (`keyword_call_at`), or the header of the enclosing definition. | SH2 (signature help in inline IF), CD1 (documentation target on a header with a step on the same line), QF2 (Create Keyword in inline IF) |
| The candidate extraction returns after the `$var` references of inline Python. | Also scan `${var}` inside `${{ }}`. | SR3, IV2, DE3 |
| The scan of a cell stops at an empty variable `${}`. | Inline values and debug expressions scan on. Selection ranges keep stopping until the cleanup, as on the legacy path. | IV3, DE4 |
| The analyzer returns before it adds a definition with a dynamic name (`${${x}}`) or a `VAR` line that Robot Framework rejects, and the defining cell is not scanned like an assignment. | Always add the statement; scan the defining cell like an assignment. | SR10, IV12, DE9, ST25 (tokens of rejected `VAR` lines) |

Single fixes:

| Label | Fix |
|---|---|
| SH1 | After the last argument of a line, the next parameter becomes active from the second space or a tab on, as between arguments. |
| SH3 | A keyword or library `__init__` without parameters gets the empty signature `()` with `activeParameter` -1. |
| SH5 | `${name}=value` for a keyword with free named arguments activates the free named parameter. |
| SH7 | No signature with the cursor in a comment at the end of the line. |
| QF1 | Create Keyword removes a BDD prefix before it determines the import prefix, so the name, the target file and the library check are right. |
| QF3 | Create Keyword for template keywords, with `[Arguments]` from the first data row. |
| QF4 | Create Keyword for the inner keyword of a Run Keyword variant, not for the variant, with only the inner keyword's arguments. |
| ST7 | `NONE` in setup and teardown gets one `argument` token. |
| ST12 | Continuation markers and comments inside a multi-line inner Run Keyword call keep their tokens; the renderer covers only the inner call's own token positions. |
| ST13 | `ELSE` and `ELSE IF` of an incomplete `Run Keyword If` get `controlFlow`. |
| ST14 | The own arguments of Run Keyword variants, such as `repeat=2`, are not split into named arguments. |
| ST22 | `start=`, `mode=` and `fill=` of FOR and `on_limit=` and `on_limit_message=` of WHILE get the option token only where Robot Framework reads them as options; before 6.1, RF rejects the two WHILE options. |
| ST23 | An invalid section header gets one `header` token from Robot Framework 6.1 on. |
| ST26 | `${a}=` without a keyword gets one `variable` token. |
| RK1 | BuiltIn keywords that Robot Framework registers in its run-keyword register only to pass their arguments unresolved run no keyword for the analysis. Today `_analyze_run_keyword` (strategy REGISTERED) looks up their argument at `args_to_process` as a keyword. The result is a false `KeywordNotFound` for `Log Many    hello`, `Comment`, `Create Dictionary    a=1`, `Set Variable If`, `Pass Execution If`, `Return From Keyword`, `Import Library` and the variable keywords with an escaped name, on every version; the LSP test data has one case (`variables.robot`, `Pass Execution If    $asd    hello`). For BuiltIn, the list of its Run Keyword variants decides; the register stays the source for other libraries. |

*Alternative considered:* ship the regressions as known differences and fix them after the cleanup. Rejected: the switchover would give them to every user, and the fixes are small.

### D5: Allowed differences are written down in the specs

Where the model path is right and the legacy path is not, the model path keeps its behavior; nothing changes on the legacy path. Each case is a scenario of the requirement "Differences from the legacy path" of its spec, or for the documentation viewer the exception in "Documentation actions in the editor":

| Spec | Model path | Legacy path |
|---|---|---|
| `semantic-highlighting` | `[Return]` is a `setting` | `controlFlow` |
| | a setup keyword that does not resolve, or from a variable, is one `keywordCall` | `argument` |
| | `Given` before a keyword that does not resolve stays part of one `keywordCall` | `bddPrefix` split off |
| | from Robot Framework 7.1 on, the BDD prefix is removed first, as Robot Framework does | full name first |
| | on Robot Framework 6.1, the content of an invalid section is `comment` | nothing before 7.0 |
| | comments of imports and template settings, none in documentation | the opposite |
| | an import name with escapes is one `namespace` token | `escape` tokens |
| | `${a}=` without a keyword: one `variable` token (fix ST26) | the same token twice from 6.0 on |
| | before 6.1, the WHILE option `limit=` is one `controlFlow` token | none |
| `inlay-hints` | `ELSE`, `ELSE IF` and `AND` get no hint | the hint of the variable-length parameter |
| `signature-help` | a signature at a continuation marker | none |
| | `AS` ends the arguments of a Library import (6.0 and newer) | only `WITH NAME` |
| `vscode-documentation-viewer` | a target for the inner keyword of a keyword-typed argument (7.4 and newer) | none |
| `code-action-quick-fixes` | inner keywords: only their own arguments (fix QF4) | the condition and the keyword name count too |
| | template keywords: `[Arguments]` from the first data row (fix QF3) | no `[Arguments]` |
| `code-action-refactorings` | no Assign result in an inline IF branch | an assignment that Robot Framework rejects |

The comparison tests that run today meet none of these cases. The Level-D fixture may meet some of them in the signature help and documentation action recordings, which never ran with the model (D7). A comparison test that meets one gets an exception that names the case and points to the scenario. `test_semantic_tokens_flag_parity.py` already documents two exceptions. The one for a fixture without a name stays as it is. The one for WHILE options before Robot Framework 6.1 stays too, because its file also has `limit=`, but its reason becomes that row of the table (ST22). The tests of the difference scenarios are grouped per module, so that `semantic-model-cleanup` deletes them together with the requirements. Where a rule of the same spec pins the behavior, its own test stays.

The setup keyword from a variable stays a `keywordCall`: the model renders it like an inner keyword from a variable, which both paths render as one `keywordCallInner`. A `variable` token for the variable name in both places is an improvement over both paths. It comes after the cleanup, like the variable tokens in option values.

### D6: Order and gate

1. The fixture.
2. RK1, because its false errors reach every user with the model on.
3. The features that the cleanup leaves without any test: inlay hints, selection ranges, inline values and debug expressions.
4. Signature help and the code actions.
5. The semantic tokens, which already have recordings and the variable tests.

Within a feature, the tests of the rules that hold today come first and pass at once; then each fix follows with its scenario tests. This change is a hard prerequisite of `semantic-model-switchover` and `semantic-model-cleanup` (D7).

### D7: What other plans need to know

- **`semantic-model-switchover`:**
  - Its gate (task 1.1) also requires this change.
  - The Level-D fixture accepts the differences of D5 where its suites meet them. Its signature help and documentation action recordings run with the model on for the first time there.
  - The Level-D fixture also compares the diagnostics of every file of the LSP test data on both paths. No test compares them today, which is how RK1 went unseen.
- **`semantic-model-cleanup`:**
  - Its gate (task 1.1) also requires this change.
  - The list of main specs it changes gets `inlay-hints`, `signature-help`, `code-action-quick-fixes` and `code-action-refactorings`. Their "Differences from the legacy path" requirements are removed together with the tests of D5. `semantic-highlighting` and `vscode-documentation-viewer` are on the list already.
  - The fixture of D1 stops setting the flag.
- **`semantic-model-token-rendering`** also has to decide two cases:
  - An import name with escapes, such as `.\\res.resource`, is one `namespace` token on the model path. The legacy path sends `escape` tokens.
  - Variables in documentation get no token, although Robot Framework resolves them; in metadata they get one.
- **`variables-import-signature`:** before Robot Framework 7.0, `b=2` in `Variables    vars.py    a    b=2` gets a `namedArgument` token on both paths, although variable files take named arguments only from 7.0 on.
- **`semantic-model-keyword-arguments`:** a keyword in Robot Framework's run-keyword register does not always run keywords. For BuiltIn, only its Run Keyword variants do (RK1). Every keyword in the register still gets its arguments without named-argument resolution.
- **`disable-diagnostic-for-line`:** besides `robotcode.discover`, the diagnostics `KeywordNotUsed` and `VariableNotUsed` also have a source that starts with `robotcode.`, namely `robotcode.diagnostics`.

## Risks / Trade-offs

- **[Rules from probes are wrong on a version or format that was not probed]** Not probed were Robot Framework 7.1 and 7.4 for some features, the tab and pipe formats, CRLF, characters outside the BMP, and `.resource` and `__init__.robot` files. → Every test runs on all versions in `hatch run test:test`. A scenario that fails on one version is checked against Robot Framework itself before the test or the spec changes; unclear cases are decided with the user.
- **[A fix in the analyzer changes other features]** For example, empty argument tokens (IH5, SH4) are also seen by the semantic tokens, hover and the argument checks. → After each fix, the full matrix and the comparison suites run.
- **[The handler tests are slower than unit tests]** → One server for all modules, small files, no workspace scan per test.
- **[Level-D finds more differences in recordings that never ran with the model]** → The switchover decides them like the cases of D5. The tests of this change show which rule each one touches.

## Migration Plan

Nothing is deployed differently: the legacy path and the default of the flag stay as they are. Each fix can be reverted on its own, and its tests with it.
