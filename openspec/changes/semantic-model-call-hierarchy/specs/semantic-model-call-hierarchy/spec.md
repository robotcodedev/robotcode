# Spec: semantic-model-call-hierarchy

## ADDED Requirements

### Requirement: Prepare call hierarchy for keywords and test cases

`textDocument/prepareCallHierarchy` SHALL return a `CallHierarchyItem` for the keyword or test case under the cursor, resolved via `model.statement_at()` / `token_path_at()`. The item's `data` SHALL carry a stable cross-file identity so follow-up incoming/outgoing requests can locate the correct model.

#### Scenario: Prepare on a keyword definition

- **WHEN** prepare is invoked on a keyword definition header
- **THEN** a `CallHierarchyItem` for that keyword is returned with round-trippable identity data

#### Scenario: Prepare on a keyword call

- **WHEN** prepare is invoked on a keyword-call token whose `keyword_doc` resolves to a workspace definition
- **THEN** a `CallHierarchyItem` for the resolved definition is returned

### Requirement: Outgoing calls include Run Keyword inner calls

`callHierarchy/outgoingCalls` SHALL enumerate the `KeywordCallStatement`s in the definition's body, descending recursively into `RunKeywordCallStatement.inner_calls`, and emit one `CallHierarchyOutgoingCall` per resolved callee with the KEYWORD token ranges as `from_ranges`.

#### Scenario: Outgoing calls from a keyword body

- **WHEN** outgoing calls are requested for a keyword whose body calls `Log` and, inside `Run Keyword If`, calls `My KW`
- **THEN** both `Log` and `My KW` appear as outgoing calls, each with the range of its own keyword token

### Requirement: Incoming calls are found workspace-wide

`callHierarchy/incomingCalls` SHALL resolve callers via the aggregated `keyword_references` for the target `KeywordDoc`, grouping call-site locations by their enclosing definition, across all workspace models.

#### Scenario: Incoming calls from another file

- **WHEN** incoming calls are requested for a keyword that is called from a test in a different file
- **THEN** that test appears as an incoming caller with the call-site range

#### Scenario: A test has no incoming calls

- **WHEN** incoming calls are requested for a test case
- **THEN** the result is empty (nothing calls a test)
