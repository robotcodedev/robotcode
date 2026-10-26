# Design: semantic-model-variables-set-by-keywords

## Context

See proposal.md for the motivation. This change runs after `semantic-model-cleanup` and `semantic-model-variables-at-cursor`, so the semantic-model path is the only one. The names below are those of today's code.

**Robot Framework** (BuiltIn, the same in 5.0.1, 6.1.1, 7.0.1, 7.1.1 and 7.5 unless noted):
- The five keywords take the name as their first argument without resolving it (`run_keyword_variant(resolve=0)`). `_get_var_name` first replaces variables in it. When the result is a variable name, that is the name; otherwise the name as written is used. So `${x}` names `${x}` unless a variable `${x}` exists whose value is itself a variable name. `_resolve_var_name` strips a leading `\` and turns `$x`, `@x` and `&x` into `${x}`, `@{x}` and `&{x}`. Variables nested in the name are resolved.
- Without a value, the keywords copy the value of the variable known at the call, and fail with "Variable '${x}' not found." when there is none (`_get_var_value`).
- `Set Suite Variable` takes `children=<value>` as its last value, an option and not part of the value.
- Scopes, from the User Guide ("Variable scopes"): local is the current test or keyword; test is the current test and every keyword it uses; suite is the current suite, without child suites unless `children` is true; global is every test and suite executed afterwards. `Set Test Variable` in a suite setup or teardown is an error before Robot Framework 7.2; from 7.2 on the variable is visible in that setup and the suite teardown only. `VAR` has the scopes `LOCAL`, `TEST`, `TASK`, `SUITE`, `GLOBAL`, and `SUITES` from 7.1 on.

**RobotCode:**
- Neither analyzer handles the five keywords. A probe on Robot Framework 5.0.1 and 7.5 shows `VariableNotFound` on the name `${a}` and on every later use, in the same test, after a call of a keyword that sets the variable, in another test and in another keyword. Until `semantic-model-feature-tests` fixes RK1, the model also reports `KeywordNotFound` on `\${b}` and `$c`.
- `visit_Var` (`semantic_analyzer/analyzer.py`) defines a `VAR` variable with a definition type per scope (`LocalVariableDefinition`, `TestVariableDefinition`, `VariableDefinition`, `GlobalVariableDefinition`). `semantic-model-variables-at-cursor` (its D6) makes every scope visible after the line in the test or keyword that contains it. Other tests and keywords do not see such a variable.
- `SemanticModel.find_variable` (`semantic_analyzer/model.py`) looks in the local variables of the enclosing definition, then in the file scope: command line, own Variables section, imports, built-in. After the cleanup, completion and hover read variables through it, as do inline values and debug expressions.
- The documentation of user keywords is built from their AST without a namespace: `get_model_doc` in `library_doc.py` keeps the keyword nodes (`_MyResourceBuilder.keywords_nodes`). The keywords of imported resources reach the analysis through that documentation.

## Goals / Non-Goals

**Goals:**
- No `VariableNotFound` on the name and on the uses that Robot Framework resolves, as far as the analysis of one file and its imports can know them.
- References, Rename, hover, completion, semantic tokens, inline values and debug expressions treat the name as a definition.

**Non-Goals:**
- Variables that libraries or listeners set through BuiltIn's API.
- Variables that the `__init__.robot` of a parent directory or another suite sets. Decided by the user on 2026-10-27: not in this change. Reading the `__init__.robot` of parent directories would make the analysis of a file depend on files it does not import, which needs its own plan for when diagnostics renew.
- New diagnostics. A use before the variable is set at run time, and `Set Test Variable` in a suite setup or teardown before Robot Framework 7.2, stay unreported where the analysis cannot see the order.
- Keywords that only read variables by name, such as `Get Variable Value` and `Variable Should Exist`.
- Type hints in the name; these keywords do not parse them.

## Decisions

### D1: The call defines the variable its name names

The analyzer handles a call that resolves to one of the five BuiltIn keywords; a user keyword with the same name defines nothing.
- **Name:** the first argument, read as `_resolve_var_name` reads it. Variables nested in it are uses and are resolved like those of a `VAR` name. A name that cannot be resolved statically gets the hint of a declaration and defines nothing, as for `VAR`.
- **Definition:** the definition type of the scope, as `visit_Var` chooses it. Its name token covers the name only, without `\`, `$`, `{` and `}`, so references keep the written form and the semantic token is that of a `VAR` name.
- **Value:** `children=…` as the last value of `Set Suite Variable` is an option. Without a value, the name is also a use of the variable known at the call: a reference, or `VariableNotFound` when there is none.
- **`${name}` as written:** the analysis takes the written name. Robot Framework names another variable only when `${name}` exists and its value is a variable name, which is why its documentation recommends the escaped forms.

*Alternative considered:* only the escaped forms define a variable, and `${name}` stays a use. Rejected: Robot Framework takes `${name}` as the name whenever the variable does not exist or its value is no variable name, and code uses both forms.

### D2: In the calling test or keyword, after the call

The definition is known in the test or keyword that contains the call, after the call, for every scope. This is what D6 of `semantic-model-variables-at-cursor` does for `VAR`. For `Set Local Variable` it is all. A call in `[Setup]` counts as before the first step, one in `[Teardown]` as after the last, and one in the `Test Setup` setting as the setup of every test.

*Alternative considered:* the whole body, wherever the call stands. Rejected: inside one body the order is known, and a use before the call fails at run time.

### D3: In other tests and keywords, in any order

- When the documentation of a user keyword is built, a scan of its body records the variables it sets with test, suite or global scope. These are calls named like the five keywords, also with `BuiltIn.`, whose name is statically known, and `VAR` with scope `TEST`, `TASK`, `SUITE`, `SUITES` or `GLOBAL`. The scan resolves nothing, so it works for the keywords of resources, which are documented without a namespace.
- The analysis of a file collects these variables from its own keywords and from the keywords of every resource it imports, directly or through other resources. From its tests, suite setup and suite teardown it adds those with suite or global scope. They are known in every test and keyword of the file. In the body with the call, D2 holds instead, so a use before the call is still reported there.
- A keyword that sets a variable through another user keyword needs no call analysis: that keyword is in the file or an imported resource, so its variable is known anyway.
- A test variable set in a test stays in that test (D2), as test variables end with their test.

*Alternatives considered:*
- Known only after a call of the setting keyword, in the calling body. Rejected: keyword bodies use variables their callers set, and layered keywords set them through others, so the most common uses would keep their errors.
- Known in the whole workspace. Rejected for this change: unrelated files would depend on each other, and a change in one would renew the diagnostics of the others.

### D4: One variable for all calls that set it

A name that is already known at the call is a reference of that variable, as for other statements that set an existing variable (`variable-assignments`). Several calls that set the same variable define it once. The first definition counts: the file's own in its order, then those of the imported resources in import order. The others are references. Find References lists all the names and uses, and Rename keeps each written form. A variable set by a keyword therefore never stands next to a file-scope variable of the same name.

*Alternative considered:* one definition per call. Rejected: Find References would show only part of the places, and Rename would miss the rest.

### D5: The model's lookup

`find_variable` and `get_variables_at` see the variables of D3 after the local variables of the enclosing definition. Variables whose call lies in that definition after the position are skipped (D2). Completion, hover, inline values and debug expressions get them from there, and the cursor features follow the rules of `semantic-model-variables-at-cursor`, for example the value at the stopped position.

### D6: Diagnostics

`VariableNotFound` disappears on the names and on the uses of D2 and D3. For a name that cannot be resolved statically, the hint of a declaration replaces today's `VariableReferenceNotStaticallyResolvable`. A name without a value reports `VariableNotFound` when the variable is unknown (D1). Nothing else is added (Non-Goals).

### D7: Specs written at implementation

`inline-values` ("Visibility at the stopped position") and `debug-expressions` ("Definitions") list where variables come from, and `semantic-model-variables-at-cursor` modifies both. Their deltas for this change are written once that change is archived, from the main specs then (task 1.2), so that no copy goes stale.

### D8: Tests

- Each scenario of the two deltas has a test: those of `variable-assignments` in `test_variable_assignments.py`, which runs on one path after the cleanup, and the token scenario in `test_semantic_tokens_rules.py`.
- Analyzer tests in `tests/robotcode/robot/diagnostics/test_semantic_analyzer/` cover the name forms (`@list`, `&dict`, `\@{list}`), `children=`, a name without a value and the scan of D3, on all Robot Framework versions.
- A namespace restored from the namespace cache gives the same result (`test_namespace_cache_restore.py`).
- Each part lands with its tests, which pass with it and fail without it.

## Risks / Trade-offs

- **[A use before the variable is set at run time is not reported in other tests and keywords]** Examples are a test that runs before the setter, `--randomize`, or a test variable of a keyword that only the suite setup calls. → Accepted (D3): the analysis does not know which test calls what, and in which order. Reporting would flag runs that pass.
- **[The scan of D3 goes by name]** A user keyword named like a BuiltIn one adds its variables to D3. → Rare; the call analysis of D1 resolves the keyword.
- **[`${name}` whose variable holds a variable name]** Robot Framework sets another variable than the analysis assumes. → Robot Framework recommends the escaped forms for that reason (D1).
- **[The keyword documentation gains a field]** → A new RobotCode version empties the caches. Development caches need clearing after the change.

## Migration Plan

No settings change. The caches renew with a new RobotCode version. Each part can be reverted on its own, with its tests.
