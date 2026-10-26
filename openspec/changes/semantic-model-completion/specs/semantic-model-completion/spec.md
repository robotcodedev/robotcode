# Spec: semantic-model-completion

## Purpose

Completion answers the same with the semantic-model analysis path enabled as with it disabled, and it offers items for the current text of the document, also while the last analysis still describes an earlier text. The variable-related `TokenKind` values are audited against the code that branches on them.

## ADDED Requirements

### Requirement: Completion answers the same on both analysis paths

At every probed position of the LSP test data, of a document with incomplete input and of the documents of the completion tests, the completion items SHALL be identical with the semantic-model analysis path enabled and disabled. A documented xfail is permitted only where the items with the path disabled are demonstrably wrong.

#### Scenario: Dual-protocol parity test

- **WHEN** completion is requested at the probed positions through two protocols, one with the semantic-model path disabled and one with it enabled
- **THEN** all item lists are identical, or the position carries a documented xfail with its reason

#### Scenario: Incomplete input

- **WHEN** completion is requested right after `${fo` without a closing brace, after `BuiltIn.` with no keyword name yet, after a keyword followed only by a separator, and on an indented empty line of a test case
- **THEN** both paths offer the same items

### Requirement: Completion offers items for the current text

Completion SHALL offer the items for the current text of the document, also when the last finished analysis describes an earlier text. The context comes from the current text, and the keyword of a call and the library of a prefix are looked up by the names written there.

#### Scenario: Line typed before the next analysis

- **WHEN** the user types `    Log    ` on a new line of a test case and requests completion at its end before the document is analyzed again, with the semantic-model path enabled or disabled
- **THEN** the named arguments of `Log` (`message=`, `level=`, …) are offered

### Requirement: Sub-token granularity audit is performed and documented

The variable-related `TokenKind` values SHALL be audited against the code that branches on them (semantic tokens and the REPL lexer, signature help, inlay hints, code actions, inline values, selection ranges, debugging, the analyzer). The keep/merge table SHALL be recorded in `dev-docs/semantic-model.md`. Only kinds without a distinct consumer SHALL be merged, and no merge SHALL change a consumer's output.

#### Scenario: Audit result is recorded

- **WHEN** the audit completes
- **THEN** `dev-docs/semantic-model.md` contains a table listing every variable-related TokenKind with its consumers and a keep/merge verdict

#### Scenario: Merges are behavior-neutral

- **WHEN** a TokenKind merge is applied
- **THEN** `test_semantic_tokens_flag_parity.py`, the analyzer snapshot tests, and all `test_*_model.py` suites pass without output changes
