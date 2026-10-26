# Design: semantic-model-keyword-arguments

## Context

See proposal.md for the motivation. This change runs after `semantic-model-cleanup`, so the semantic-model path is the only one. The rules modules and specs of `semantic-model-feature-tests` exist by then. The names below are those of today's code; the cleanup removes the legacy branches around them.

Three places decide today which argument of a call goes to which parameter:
- **Inlay hints** (`_get_inlay_hint_from_semantic_tokens` in `parts/inlay_hint.py`) call `ArgumentSpec.resolve(..., resolve_named=not kw_doc.is_any_run_keyword(), validate=False)` (`library_doc.py`):
  - without validation, that method uses its subclass of Robot Framework's `NamedArgumentResolver` directly and ignores `resolve_named`;
  - `is_any_run_keyword()` knows only BuiltIn's variants;
  - no variables are passed, so `${NAME}=WARN` stays positional;
  - a list expansion counts as one argument.
- **Semantic tokens**: `_named_argument_split` in `semantic_analyzer/analyzer.py` splits `name=value` when the name is any parameter, positional-only ones included.
- **Signature help** reads those `NAMED_ARGUMENT_NAME` sub-tokens (`_is_named_arg` and `_named_arg_name` in `parts/signature_help.py`). Its own `_is_dict_or_list_spread` lets `@{…}` force named arguments and misses item access such as `&{d}[k]`.

Robot Framework's resolver (`NamedArgumentResolver` in `running/arguments/argumentresolver.py`) handles positional-only parameters itself:
- up to 7.0, a name counts as named only if it is a positional-or-named or a named-only parameter;
- from 7.1 on, the first arguments, as many as there are positional-only parameters, are taken positionally.

Robot Framework passes the arguments of a keyword registered as a run keyword as they are: `resolve_named=False` in 6.1 (`_RunKeywordHandler`), `resolve_named=resolve_args_until is None` in 7.5 (`LibraryKeyword.resolve_arguments`). That covers BuiltIn's variants and libraries that call `register_run_keyword`.

Other places this change touches:
- **Inner calls**: the analyzer builds `RunKeywordCallStatement.inner_calls`, each with its own keyword documentation and tokens. It does so for BuiltIn's variants, for keywords with `KeywordName` arguments (Robot Framework 7.4 and newer) and for registered run keywords (`semantic_analyzer/run_keyword.py`). None of the features uses them for its own output:
  - inlay hints skip them (`_collect_from_model`);
  - signature help shows the outer signature;
  - the renderer decomposes only `is_any_run_keyword()` (`_iter_model_sem_tokens` in `parts/semantic_tokens.py`).
- **Templates**:
  - `visit_TemplateArguments` resolves the template keyword for each data row, filling the template's placeholders first (`_format_template`). It uses the result only for diagnostics; `TemplateDataStatement.template_keyword_doc` stays empty.
  - The row tokens come from `_build_setting_tokens`, without a named split.
  - `visit_Template` and `visit_TestTemplate` resolve the name alone and render a name that does not resolve as one `argument` token.
- **`Import Library`**: for RobotCode it is a normal BuiltIn keyword `(name, *args)`. Robot Framework splits off the alias: `WITH NAME`, or `AS` from 6.0 on, as the second-to-last argument (`_split_alias` in BuiltIn). From 7.4 on, it resolves a relative library path against the directory of the file with the call; before that, only through the module search path (`Namespace.import_library`).
- **Keyword names from variables**: a keyword name that does not resolve becomes one keyword token over its cell (`_build_keyword_call_tokens`), also `${SETUP}` and `${kw}`.
- **Reserved words**: before Robot Framework 7.0, reserved words such as `END` resolve to keywords of the `Reserved` library (`KeywordDoc.is_reserved()`).
- **Signature help after a name**: `_cursor_past_keyword_name` waits for name end + 2 and `_cursor_past_import_name` for name end + 1, exclusive. Between arguments, `_active_argument_from_semantic_tokens` already takes a tab as a whole separator.

## Goals / Non-Goals

**Goals:**
- Inlay hints, signature help and the named-argument tokens follow Robot Framework's argument resolution of the installed version, and they agree with each other.
- Template data rows, the inner calls of keywords that run keywords and `Import Library` get the help of the keyword that receives their arguments.

**Non-Goals:**
- No change to completion. `variables-import-signature` already removes the `name=` items of positional-only parameters there.
- `Import Library` does not make the keywords of the imported library known to the file: no change to keyword resolution or diagnostics.
- No help for other keywords that import at run time (`Import Resource`, `Import Variables`).
- No signature help on the template setting itself.
- No change to how the text of template rows is rendered; that is `semantic-model-token-rendering`.
- No new kinds of hints and no new settings.

## Decisions

### D1: The fixes by cause

The labels are used in tasks.md.

| Cause | Fix | Labels |
|---|---|---|
| Positional-only parameters are treated as named | The mapping of D2 follows Robot Framework, so their names never make an argument named. Their hint shows the bare name. | IH1, SH6, ST15 |
| Robot Framework does not resolve named arguments for registered run keywords | No own argument of such a keyword counts as named, in all three features. | IH7, SH6 |
| Expansions | Only `&{…}`, also with item access, makes the following arguments named. From the first `@{…}` on, also with item access, the positions are unknown (D4). | IH10, SH13 |
| Variables in argument names | A name with variables whose values are known counts with these values (D5). | IH12 |
| The hint of a variable-length parameter is repeated with `=` | Only its first argument gets a hint, `*name` without `=`. | IH2 |
| Inner calls are not used | Inner calls get the hints and the signature of the inner keyword; every keyword that runs keywords is rendered like BuiltIn's variants (D6). | IH4, SH10, ST19 |
| Keyword names from variables are one keyword token | The variable gets its `variable` token, the rest of the cell none (D7). | ST28 |
| Template rows are not linked to the template keyword | The analyzer keeps the template keyword per row and resolves a template name with its first data row (D8). | IH3, SH9, ST18, ST27 |
| `Import Library` uses its own signature for the library's arguments | The analyzer loads the library like a Library import (D9). | IH8, SH11 |
| Reserved words get a namespace hint | No hints for a keyword of the `Reserved` library. | IH11 |
| Signature help after a name ignores a tab separator | The same threshold as between arguments: the second space, or a tab. | SH14 |

### D2: One argument mapping for the three features

A function in the semantic analyzer package maps the argument cells of a call to Robot Framework's parameters. For each cell it gives one of: the positional parameter, a named parameter or the free named parameter, or "unknown position". It wraps Robot Framework's `NamedArgumentResolver` of the installed version, the class `ArgumentSpec.resolve` uses without validation, so positional-only parameters behave as on that version. For a registered run keyword, BuiltIn's variants included, it never resolves names.

- The analyzer uses it to decide the `NAMED_ARGUMENT_NAME` split. Only a literal name is split, so a name with variables keeps its `variable` token.
- Inlay hints and signature help call it at request time, with the keyword documentation and the argument values of the statement.
- `ArgumentSpec.resolve` stays as it is: completion still calls it without validation, and completion is not part of this change.

*Alternatives considered:*
- Store the mapping on the model. Rejected: more data in the namespace cache for a result that is cheap to compute again.
- Fix the three code paths one by one. Rejected: they disagree today, for example on `&{d}[k]` (hints treat it as a dictionary, signature help does not), and every rule would have to be fixed three times.

### D3: Hint labels follow how the parameter is passed

- A positional-only parameter shows its bare name (`⟨a⟩1`): the hint names the parameter, but `a=` would suggest a syntax that Robot Framework passes as a value.
- A variable-length parameter shows `*name` on its first argument only (`⟨*messages⟩a    b    c`), as one parameter takes them all.

Both are the user's decisions. *Alternative considered:* no hint for positional-only parameters. Rejected: from Robot Framework 7.4 on, many BuiltIn keywords have positional-only parameters and would lose all hints.

### D4: Expansions follow Robot Framework's variable syntax

The mapping uses Robot Framework's `is_list_variable` and `is_dict_variable`, so item access (`@{x}[0]`, `&{x}[k]`) counts as an expansion of the item, as at run time.
- After a dictionary expansion, every argument counts as named, as in Robot Framework's resolver.
- From the first list expansion on, the positions are unknown: inlay hints show no parameter hints, and signature help activates no parameter for positional arguments.

*Alternative considered:* count a list as one argument. Rejected by the user, for the hints and on 2026-10-26 for signature help: every later hint and every active parameter could be wrong, because Robot Framework knows the number of list items only at run time.

### D5: Variables in argument names count with known values

A `${name}=value` whose variables the analysis can resolve counts with the resolved name, as Robot Framework replaces them before it checks the name. The values come from the variables whose values are known before the run, the way RobotCode resolves variables in import names (`get_resolvable_variables`, on the model after the cleanup). This applies to inlay hints and signature help. The semantic tokens keep the `variable` token on the name, and a cell cannot carry both.

### D6: Inner calls are keyword calls

Every `RunKeywordCallStatement` is treated alike: BuiltIn's variants, keywords with `KeywordName` arguments and registered run keywords. Registered means registered by a library other than BuiltIn: BuiltIn registers keywords such as `Log Many` and `Set Test Variable` only to get their arguments unresolved, and since `semantic-model-feature-tests` (its RK1) they are plain calls. Named arguments stay unresolved for every registered keyword, BuiltIn's included (D2).
- **Rendering**: the outer keyword is rendered as a call, its inner calls like BuiltIn's variants, recursively.
- **Inlay hints**:
  - the cells before the first inner keyword get the hints of the outer signature;
  - each inner call gets the hints of a call: the namespace hint before the inner keyword and the parameter hints of the inner keyword;
  - an inner keyword that does not resolve gets none;
  - `ELSE`, `ELSE IF`, `AND` and the conditions after `ELSE IF` get none.
- **Signature help**:
  - on the outer keyword's own cells, on an inner keyword's name and on the markers, the outer signature;
  - from the second space or a tab after an inner keyword's name, the signature of the innermost call whose arguments hold the cursor;
  - for an inner keyword that does not resolve, the outer signature with its variable-length parameter.

*Alternative considered:* keep the outer hint `name=` on the inner keyword and add the namespace hint. Rejected: two hints in front of one name, and the namespace hint is what every other call shows there.

### D7: Keyword names from variables render as variables

A keyword name that is a variable gets a `variable` token for the variable name; the rest of the cell gets none, as for every variable (`semantic-highlighting`, "Variables get a token for their name only"). This applies to setups, teardowns and the inner keywords of keywords that run keywords, the places where Robot Framework takes a keyword name from a variable. In a step, `${x}` in the keyword position is an assignment. Hints and signature help stay off for such calls, as today.

### D8: Template data rows know their keyword

- `visit_TemplateArguments` keeps the keyword it already resolves for the row in `TemplateDataStatement.template_keyword_doc`. That field exists and is cached already.
- It splits the row's `name=value` cells with that keyword (ST18).
- A row whose cells fill the template's placeholders is recognized as Robot Framework does: the number of placeholders equals the number of cells. Such a row gets no hints and no signature, because no parameter receives its cells.
- When the template name alone does not resolve, the setting is resolved with the values of the first data row, like `visit_TemplateArguments` does (ST27). It is then rendered like a resolved template: the fixed text as `keywordCall`, the placeholders as `variable` tokens with `embedded`.
- The other cells of template rows keep their tokens; `semantic-model-token-rendering` decides them.

*Alternative considered:* resolve the template keyword in the LSP features at request time. Rejected: the analyzer resolves it anyway, and all three features need it.

### D9: `Import Library` loads the library like a Library import

The analyzer recognizes BuiltIn's `Import Library` and resolves its first argument as Robot Framework does at run time:
- with the variables whose values are known replaced;
- from 7.4 on, a relative path against the directory of the file with the call; before that, only through the module search path.

It loads the library through the imports manager with the arguments before the alias marker. When that fails, it loads the library without arguments, as for a Library import. The `__init__` documentation is kept on the call statement, as `ImportStatement.init_keyword_doc` is for imports. Inlay hints and signature help use it for the cells between the name and the marker. The name cell keeps the hint and the signature of `Import Library`'s own `name` parameter. A name with variables that cannot be resolved gives no library, and the cells after it get no hints.

*Alternative considered:* load the library in the LSP features at request time. Rejected: it would duplicate the analyzer's import handling, base directory and variables, for two features.

### D10: Tests

Each scenario of the three deltas has one test in the rules module of its feature from `semantic-model-feature-tests`. Where a MODIFIED scenario keeps its name but changes its expectation, its test changes with it, for example "Argument of the inner keyword". The mapping of D2 also gets unit tests per Robot Framework version. Each fix of D1 lands with its tests, which pass with the fix and fail without it.

## Risks / Trade-offs

- **[Loading libraries for `Import Library` slows the analysis or runs library code]** → The imports manager loads and caches them as it does for Library imports; names with variables that cannot be resolved load nothing.
- **[The named-argument tokens change between Robot Framework versions]** → Intended: they follow the installed version's resolver, which takes positional-only arguments differently from 7.1 on. The tests run on all versions.
- **[Lines with Run Keyword variants get more hints]** → The namespace hint replaces the outer `name=` hint, and the arguments get the hints a direct call of the inner keyword would get.
- **[Template rows show hints in long data tables]** → They are the same hints a call shows, and `robotcode.inlayHints.parameterNames` switches them off.

## Migration Plan

No setting changes. The model gains the `__init__` documentation of `Import Library` calls. The namespace cache stores the RobotCode version and is emptied when it differs, so a release renews it. Rollback is reverting the change.
