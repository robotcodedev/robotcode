# Spec Delta

## MODIFIED Requirements

### Requirement: Documentation actions in the editor

RobotCode SHALL offer the source actions "Show in Documentation Viewer", "Show in New Documentation Viewer" and "Open Documentation (deprecated)", in this order, under the same conditions:
- on the name of a Library or Resource import;
- on a keyword reference in a keyword call, setup, teardown or template;
- on the name in a keyword definition header.

The offered actions and what they document SHALL be the same on both analysis paths, except on inner keywords of keyword-typed arguments.

#### Scenario: Library import name
- **WHEN** source actions are requested with the cursor on `Collections` in `Library    Collections`
- **THEN** the menu lists "Show in Documentation Viewer", "Show in New Documentation Viewer" and "Open Documentation (deprecated)", in this order, all for the library `Collections`

#### Scenario: Keyword of a library
- **WHEN** the user chooses "Show in Documentation Viewer" on a call of `Remove From List`
- **THEN** a viewer shows `Collections` at `Remove From List`

#### Scenario: Keyword definition in a resource file
- **WHEN** source actions are requested on the name in a keyword definition header of a `.resource` file
- **THEN** the three actions are offered, and "Show in Documentation Viewer" shows that resource file at the keyword

#### Scenario: Keyword definition in a suite file
- **WHEN** source actions are requested on the name in a keyword definition header of a file with a `*** Test Cases ***` section
- **THEN** the three actions are offered, and "Show in Documentation Viewer" shows that suite file at the keyword

#### Scenario: Keyword definition header with a step on the same line
- **WHEN** source actions are requested on the name in the header `Same Line Kw    Log    x`, where the first step follows the name on the same line
- **THEN** the three actions are offered for that keyword, as for a header without a step

#### Scenario: Both analysis paths
- **WHEN** the same positions are evaluated with the semantic-model analysis path enabled and disabled
- **THEN** the offered actions, their order and what they document are identical, except on inner keywords of keyword-typed arguments

#### Scenario: Deprecated action
- **WHEN** the user chooses "Open Documentation (deprecated)" on a call of `Remove From List`
- **THEN** the Libdoc page of `Collections` opens at `Remove From List`

#### Scenario: Own key on a keyword
- **WHEN** the user has bound a key to `editor.action.sourceAction` with the arguments `{"kind": "source", "preferred": true, "apply": "first"}`, the cursor is on a call of `Remove From List`, and the user presses that key
- **THEN** a viewer shows `Collections` at `Remove From List`, no menu is shown, and the editor keeps the focus

#### Scenario: Own key without documentation
- **WHEN** the cursor is in a comment and the user presses that key
- **THEN** no viewer opens or changes, and VS Code reports that no preferred source action is available

#### Scenario: No key of RobotCode
- **WHEN** the cursor is on a call of `Remove From List` and the user presses Shift+F1 without a binding of their own
- **THEN** no viewer opens

## ADDED Requirements

### Requirement: Documentation actions on inner keywords of keyword-typed arguments

With the semantic-model analysis path enabled, the documentation actions and the link in the hover's heading SHALL also target the inner keyword of a keyword whose arguments are typed `KeywordName` and `KeywordArgument` (Robot Framework 7.4 and newer), with the cursor on that inner keyword. The legacy path offers no target there.

#### Scenario: Inner keyword of a library keyword
- **WHEN** a library keyword `Run It` takes `name: KeywordName, *args: KeywordArgument` and the cursor is on `Log` in `Run It    Log    x`, on Robot Framework 7.4 or newer with the semantic-model analysis path enabled
- **THEN** the documentation actions are offered for `BuiltIn` at `Log`
