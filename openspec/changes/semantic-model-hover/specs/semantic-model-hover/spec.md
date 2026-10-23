# Spec: semantic-model-hover

## ADDED Requirements

### Requirement: Keywords in inline IF bodies and Run Keyword arguments have a documentation target on the model path
With the semantic-model analysis path enabled, a keyword in the body of an inline IF and a keyword in the arguments of a Run Keyword variant, nested ones too, SHALL have the documentation target they have on the legacy path: that keyword with the import that defines it. The documentation source actions and, with viewer links, the link in the heading of the hover come from that target.

#### Scenario: Keyword in an inline IF
- **WHEN** the semantic-model path is enabled and the cursor is on `Log` in `IF    ${TRUE}    Log    a    ELSE    No Operation`
- **THEN** the documentation source actions are offered for `BuiltIn` at `Log`, and with viewer links the heading of the hover links there, as on the legacy path

#### Scenario: Keyword in the arguments of Run Keyword
- **WHEN** the semantic-model path is enabled and the cursor is on `Log` in `Run Keyword    Log    hi`
- **THEN** the documentation source actions and the link of the hover's heading are those of `Log`, as on the legacy path

#### Scenario: Keyword in a nested Run Keyword If
- **WHEN** the semantic-model path is enabled and the cursor is on `Log` in `Run Keyword    Run Keyword If    ${TRUE}    Log    hi`
- **THEN** the documentation source actions and the link of the hover's heading are those of `Log`, as on the legacy path

### Requirement: Hover answers the same on both analysis paths
At every probed position of the hover test data and of the documents of the hover tests, the hover response (contents and range) SHALL be identical with the semantic-model analysis path enabled and disabled, with and without viewer links. A documented xfail is permitted only where the legacy output is demonstrably wrong.

#### Scenario: Dual-protocol parity test
- **WHEN** the hover is requested at the probed positions through two protocols, one with the semantic-model path disabled and one with it enabled
- **THEN** all responses are identical, or the position carries a documented xfail with its reason

#### Scenario: Call that matches several keywords
- **WHEN** the cursor is on a call whose name matches keywords of two imported resource files
- **THEN** both paths show the documentation of each of them, joined and without a link in the heading
