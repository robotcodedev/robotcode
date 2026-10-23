## ADDED Requirements

### Requirement: A restored semantic model refers to the keywords and imports of the restored namespace

With the semantic-model analysis path enabled, a namespace restored from the namespace disk cache SHALL resolve the keyword calls, imports and template rows of its semantic model to the same keywords and imports as a fresh analysis of the same file state, with their library or resource documentation. The features that read them SHALL answer as for a fresh analysis, also after the file is opened in the editor with unchanged text.

#### Scenario: BuiltIn keyword after a restart

- **WHEN** a suite calls `Log`, its namespace is restored from the cache with the semantic-model path enabled, and the suite is then opened in the editor without changes
- **THEN** the documentation target at `Log` is `BuiltIn` with the keyword `Log`, as for a fresh analysis

#### Scenario: Library import and a call with its prefix

- **WHEN** a suite imports `Collections` and calls `Collections.Append To List`, and its namespace is restored from the cache with the semantic-model path enabled
- **THEN** the documentation targets at the import and at the call are those of a fresh analysis
