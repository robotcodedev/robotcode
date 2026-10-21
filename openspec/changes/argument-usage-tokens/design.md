# Design

## Context

See proposal.md for the motivation and the spec for the behavior. The current state, read from the code on 2026-10-22:

- **Two paths render semantic tokens.** The default is the legacy path in `semantic_tokens.py`. With the `semantic_model` flag, `collect_tokens_from_model` renders the semantic model. The main spec `semantic-model-tier1-parity` requires both to send the same tokens for every file of the LSP test data (`test_semantic_tokens_flag_parity.py`). The model renderer may only map `TokenKind`, `NodeKind` and `TokenModifier` through static tables; all decisions belong to the analyzer.
- **Variable names on both paths** come from the shared `build_variable_sub_tokens`, which asks an `is_defined` callback:
  - On the legacy path, `_generate_variable_sem_tokens` asks `namespace.find_variable(name, position)`. It sends the name with the type its caller passes: `parameter` for `[Arguments]` declarations, `variable` everywhere else, and always `variable` for names inside nested variables.
  - On the model path, the `SemanticAnalyzer` asks its own `_find_variable`. Uses are `VARIABLE` tokens, and `PARAMETER` is the kind of the declaration in `[Arguments]`.
- **Both analyses resolve uses of an argument to its `ArgumentDefinition`.** An assignment such as `${user}=` or `VAR    ${user}` for a name that already is an argument or a local variable adds a reference to it instead of a new definition. This is true for `NamespaceAnalyzer` and `SemanticAnalyzer`, and `test_variable_pipeline_comparison.py` compares the two.
- **Embedded arguments** are `EmbeddedArgumentDefinition`, a subclass of `ArgumentDefinition`, and their declaration in the keyword name is a `variable` token.
- **Colours:** in PyCharm `ROBOTFRAMEWORK_PARAMETER` inherits the colour of `ROBOTFRAMEWORK_VARIABLE`. VS Code has no scope of RobotCode's own for `parameter` and uses the theme's `variable.parameter`.
- **Planned semantic-model changes:**
  - `semantic-model-switchover` adds the builtin modifier to variable tokens from the resolved definition and rejects local, global and environment modifiers (its decision D4).
  - `semantic-model-token-rendering` rebuilds the renderer and says "no new token types or modifiers".
  - `semantic-model-hover` reads `PARAMETER` as the kind of a definition.

## Goals / Non-Goals

**Goals:**

- One decision, made where the variable is resolved, that both paths turn into the same token.
- No change to the kinds of the semantic model that its other users read.

**Non-Goals:**

- New token types or LSP modifiers.
- Tokens of embedded arguments, and variables of other kinds.

## Decisions

### Uses of arguments render as the standard type `parameter`

The token type changes; no modifier is added. LSP defines `parameter` for references as well as declarations, and themes and IntelliJ colour schemes already know it.

Alternatives:
- A custom modifier such as `argument`: no theme styles it, and D4 of `semantic-model-switchover` rejected custom scope modifiers for variables.
- Keeping `variable` and deriving the kind in the IntelliJ plugin: the plugin only sees the token, so it would have to resolve the variable itself.

### The semantic model marks the token, its kind stays `VARIABLE`

When the `SemanticAnalyzer` resolves a variable token to an `ArgumentDefinition` that is not an `EmbeddedArgumentDefinition`, it sets a new model-internal `TokenModifier` on the token. The renderer's static emission policy turns `VARIABLE` with this modifier into `parameter` and passes no LSP modifier for it.

`PARAMETER` stays the kind of the declaration, so hover, inline values and other readers of the model see the same kinds as before.

Alternative: `TokenKind.PARAMETER` for uses. It would turn every use into a declaration for those readers.

### The legacy path decides from the namespace's resolution

`_generate_variable_sem_tokens` and the nested names in `_iter_variable_name_sem_tokens` send `parameter` for a name that `namespace.find_variable` resolves, at that position, to an `ArgumentDefinition` that is not embedded. This mirrors the model, and the parity suite checks that the two stay equal.

### The planned semantic-model changes learn about the marker

The design notes of `semantic-model-switchover`, `semantic-model-token-rendering` and `semantic-model-hover` get one line each:
- the marker exists;
- it renders as a type, not as a modifier;
- `PARAMETER` stays the declaration.

## Risks / Trade-offs

- [The two analyses resolve a name differently, for example in a scope corner case] → The parity suite fails for that file. A difference is accepted only as a documented xfail where the model is more correct, as `semantic-model-tier1-parity` requires.
- [VS Code themes that style `variable.parameter` change the look of argument uses] → Intended: uses then look like their declaration, as in other languages.
- [Regression outputs of `test_semantic_tokens.py` change] → The diff is reviewed before the reset: it may only turn `variable` into `parameter` at uses of `[Arguments]` arguments.
