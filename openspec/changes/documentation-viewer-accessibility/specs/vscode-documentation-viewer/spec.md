# Spec Delta

## ADDED Requirements

### Requirement: Names of a viewer's fields for screen readers

A viewer SHALL give screen readers and other assistive technology the name "Target" for its target field, "Filter the outline" for the filter field of its outline, and "Find in the page" for the field of its find bar, instead of the fields' placeholders.

#### Scenario: Target field
- **WHEN** a screen reader reads the target field of a viewer that shows `BuiltIn`
- **THEN** it announces the field as "Target"

#### Scenario: Filter field
- **WHEN** a screen reader reads the filter field of a viewer's outline
- **THEN** it announces the field as "Filter the outline"

#### Scenario: Find field
- **WHEN** the find bar of a viewer is open and a screen reader reads its field
- **THEN** it announces the field as "Find in the page"

### Requirement: Names of the outline entries for screen readers

A viewer SHALL give screen readers and other assistive technology the title of its heading as the name of each outline entry, without the characters of the entry's icons.

#### Scenario: Outline entry of a keyword
- **WHEN** a viewer shows `BuiltIn` and a screen reader reads the outline entry of `Should Be Equal`
- **THEN** it announces the entry as `Should Be Equal`

#### Scenario: Outline entry with entries below it
- **WHEN** a viewer shows `BuiltIn` and a screen reader reads the outline entry `Introduction`
- **THEN** it announces the entry as `Introduction`, together with its state as expanded or collapsed

### Requirement: The toolbar of a viewer for screen readers

A viewer SHALL present its toolbar to screen readers and other assistive technology as a toolbar named "Documentation Viewer". The Tab key SHALL still move through the toolbar's controls one by one, as it does without the group.

#### Scenario: Control in the toolbar
- **WHEN** a screen reader reads the back button of a viewer
- **THEN** it announces the button as part of the toolbar "Documentation Viewer"

#### Scenario: Tab through the toolbar
- **WHEN** the back button of a viewer has the focus and the user presses Tab
- **THEN** the focus moves to the forward button
