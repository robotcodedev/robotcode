# Spec: semantic-model-smart-rename

## ADDED Requirements

### Requirement: Keyword rename edits only the keyword name token

When renaming a keyword, the edit SHALL target only the `KEYWORD` token range at the definition and at each call site, leaving any `BDD_PREFIX`, `NAMESPACE`, and `SEPARATOR` tokens unchanged. `prepareRename` SHALL return the keyword-name token range, not the whole cell.

#### Scenario: Rename a BDD-prefixed call

- **WHEN** a keyword called as `Given Log` is renamed to `Write`
- **THEN** the call becomes `Given Write` (the `Given ` prefix is preserved)

#### Scenario: Rename a namespace-qualified call

- **WHEN** a keyword called as `BuiltIn.Log` is renamed
- **THEN** only `Log` is edited; `BuiltIn.` remains

### Requirement: Variable rename respects definition scope

Renaming a variable SHALL confine the edit set to the variable's scope: a variable in a `DefinitionBlock.local_variables` (FOR loop variable, `EXCEPT AS` variable, local assignment, `VAR LOCAL`) renames only within that block's line range; a file/suite/global variable renames across the workspace. Scope is determined via `find_variable(name, line)` + `enclosing_definition_block()`.

#### Scenario: Loop variables in different keywords are independent

- **WHEN** `${i}` used in a FOR loop inside keyword A is renamed
- **THEN** a same-named `${i}` in an unrelated FOR loop inside keyword B is not edited

#### Scenario: Local does not touch file scope

- **WHEN** a local `${x}` inside one keyword is renamed
- **THEN** a file-scope `${x}` referenced elsewhere is left unchanged

### Requirement: Alias and tag renames use resolved model references

Renaming a library alias SHALL edit the `WITH NAME` alias token and every `KeywordCallStatement` whose `lib_entry` is that aliased entry. Renaming a tag SHALL edit all occurrences recorded in `keyword_tag_references` / `testcase_tag_references`.

#### Scenario: Rename a library alias

- **WHEN** `Library    X    WITH NAME    Foo` is renamed from `Foo` to `Bar`
- **THEN** the alias and every `Foo.Keyword` call are updated to `Bar.Keyword`

#### Scenario: Rename a tag workspace-wide

- **WHEN** a tag is renamed
- **THEN** every test and keyword carrying that tag across the workspace is updated
