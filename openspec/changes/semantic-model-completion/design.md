# Design: semantic-model-completion

## Context

See proposal.md (Why). The current state that shapes the approach:

- `CompletionCollector.collect` takes all nodes of the parsed model at the cursor (`get_nodes_at_position`, innermost first), calls every matching `complete_<NodeType>` handler (20 of them) and then `complete_default`, and joins their items. The handlers work on the RF tokens and the text: indentation, separators, `EOL`, and `rfind("{")` inside a token for a variable whose closing brace is still missing.
- Completion uses the namespace of the last finished analysis (`get_initialized_namespace`, since 2c6fe37c2, "to be a bit more responsive"), and a text change keeps it. Probe on RF 7.5 with the flag on: after typing `    Log    ` on a new line, completion gets the namespace from before the edit, whose semantic model has the old `No Operation` statement on that line; completion still offers `message=`, `level=`, … because it reads the line from the current text and finds `Log` by name.
- An up-to-date model would not add anything at the typical cursor position either: `token_path_at()` excludes the token end, so right after `${fo`, `Collections.` or `Log␣␣␣␣` it returns the `EOL` token; `${fo` is an `ARGUMENT` without sub-tokens, and `Collections.` with no keyword after it is a `KEYWORD` token without `NAMESPACE` and without `lib_entry`.
- Everything completion reads from the namespace exists on both paths: the keyword finder, the imported libraries and resources, and the scope tree behind `get_variable_matchers()` and `get_resolvable_variables()`, which the SemanticAnalyzer builds too. Its `ModelHelper` calls (BDD prefix, the keyword of a call through `finder.find_keyword`, keyword prefix, argument position) work on both namespaces. A first probe at four positions with incomplete input gave identical items on both paths.
- There is no completion corpus. Completion is tested in five files; two of them run with both flag states (`test_completion_deprecated_keywords.py`, `test_private_keywords.py`).

## Goals / Non-Goals

**Goals:**
- Prove completion parity under both flag states over a corpus that includes incomplete input.
- Fix in the SemanticAnalyzer what the corpus finds where the result with the flag on is wrong, before it becomes the default.

**Non-Goals:**
- No model branch in `completion.py` and no change to which namespace completion uses.
- No new completion kinds: block options (#419) and template-row arguments are separate changes; without a model branch they go into the handlers once.
- No removal of `ModelHelper` from completion (see D4).
- `SemanticModel.get_variables_at()` stays unused; completion keeps reading variables through the namespace.

## Decisions

### D1: No model branch; the context comes from the current text

The semantic model belongs to the last finished analysis, and completion runs between a keystroke and the next analysis, so a model branch would read what stood on the cursor line before the edit (see Context). Completion keeps its handlers and its lookups by name.

*Alternatives considered:*
- A fresh namespace for every completion request, as the other features use: a full analysis per keystroke, which reverses 2c6fe37c2.
- The model only when the namespace matches the current text version, the text otherwise: two implementations of the same context detection that must stay equal.

### D2: Corpus: test data, incomplete input, completion test documents

`test_completion_model.py` follows `test_hover_model.py`: two module-scoped protocols (flag off and on) with the vacuity guard, the `.robot` files of the LSP test data (without `very_big_file.robot`), and the documents of the completion tests written to a temporary project and opened in both protocols.

Positions per line, comment lines skipped: column 0, the end of the indentation, the start and end of every cell, the position after each `{` of a variable and after each `.` in a keyword cell, and the end of the line. They are capped per file and thinned evenly like in the hover test; the cap comes from a measured run time.

The test data are mostly complete code, so a document with incomplete input adds the typical typing positions: an unclosed `${fo` and `%{NA`, `${` alone, `BuiltIn.` and a resource name followed by `.` with nothing after the dot, a keyword followed only by a separator, an indented empty line in a test case and in a keyword, a partial setting name in `*** Settings ***` and in a test case (`[Ta`), a partial section header (`*** Te`), partial import paths (`Library    ./`, `Resource    ../`), a BDD prefix (`Given `), a named argument (`level=`), and a data row of a templated test.

The items are compared as dictionaries after replacing the process-specific object ids in `data` (`str(id(...))` and the doc-cache names built from them).

*Alternative considered:* snapshot files of the items, which would also catch a bug that both paths share. Rejected for this change: the gate is parity, and the item lists of the test data would make large snapshots that change with every library update.

### D3: Deviations: fix the analyzer, xfail only legacy bugs

Completion has no branch, so a deviation means that the two analyzers fill the namespace differently at that position. If the result with the flag on is wrong, the SemanticAnalyzer is fixed in this change, with a regression test. If the result with the flag off is wrong, the position gets a documented xfail with its reason (the known-deviations table of the hover test).

### D4: `ModelHelper` stays until the cleanup

The seven calls are text and finder helpers that serve both paths. Deleting `ModelHelper` is the job of `semantic-model-cleanup`, which decides once, for all remaining users, where the helpers go. Its task 2.3 ("collapse to model-only") then becomes "move the helpers completion uses and remove the mixin".

*Alternative considered:* move the helpers out of `ModelHelper` now. Rejected: the legacy features use some of them until the cleanup, so they would move twice or exist twice.

### D5: Granularity audit against the actual consumers

`token_path_at()` and `token_at()` have no production caller, so the audit cannot wait for one. It records, for each variable-related `TokenKind`, the code that branches on it: `_TOKEN_KIND_TO_SEM_TOKEN` in `semantic_tokens.py` and its mirror in the REPL lexer, signature help, inlay hints, the code actions, `model_variables.py` (inline values, selection ranges, debugging), and the analyzer. Output: a keep/merge table in `dev-docs/semantic-model.md` that replaces the open question on the granularity in the Sub-Token Decomposition section; that question still expects completion as a consumer of `token_path_at()`. Only kinds without a distinct consumer and with the same LSP mapping are merged; every merge keeps `test_semantic_tokens_flag_parity.py`, the analyzer snapshots and all `test_*_model.py` suites unchanged. When in doubt, the kind stays.

## Risks / Trade-offs

- [Completion lists are long (well over 100 items at a keyword position), so many positions make the test slow] → a per-file cap from a measured run, as in the hover test.
- [The corpus finds many deviations between the analyzers] → each is analyzed before it is fixed or marked; the run on all RF versions is the gate.
- [The parity test cannot see a bug that both paths share] → accepted (D2); the targeted completion tests cover the behavior itself.

## Migration Plan

(1) Parity test over the test data and the completion test documents, (2) the document with incomplete input, (3) the Completion section and the Ideas Collection of `dev-docs/semantic-model.md`, (4) deviations fixed or marked, (5) audit and its table. Rollback = revert; the flag default stays `false`.
