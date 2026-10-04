# Spec Delta

## ADDED Requirements

### Requirement: Variables expand into their items

While a run is paused, the Variables view SHALL show the Local scope of the selected frame inline and the frame's other scopes (Test, Suite, Global) as groups whose variables are loaded when a group is expanded. A list variable SHALL expand into its length and its items, shown in pages of 100 items with an entry that loads the next page. A dictionary variable SHALL expand into its length and its entries. A frame without scopes SHALL show no variables and no error. Each variable SHALL show the name of its Python type, such as `str`, `list` or `DotDict`.

#### Scenario: Expand a list

- **WHEN** the run is paused after `@{items}=    Create List    a    b    c` and the user expands `@{items}`
- **THEN** the items `a`, `b` and `c` are shown with their indexes, and the type column shows `list`

#### Scenario: Large list

- **WHEN** a paused test has a list variable with 300 items and the user expands it
- **THEN** the first 100 items are shown with an entry for the remaining 200, and choosing that entry shows the next 100

#### Scenario: Expand a dictionary

- **WHEN** the run is paused after `&{options}=    Create Dictionary    a=1    b=2` and the user expands `&{options}`
- **THEN** the entries `'a'` and `'b'` are shown with their values

#### Scenario: Frame without scopes

- **WHEN** the user selects a frame for which the debugger reports no scopes
- **THEN** the Variables view is empty and the IDE logs no error

### Requirement: Set Value for variables of the paused keyword or test

While a run is paused, Set Value SHALL be offered for the variables of the Local scope of the innermost frame. The new value SHALL be evaluated as the debugger evaluates it: as a Python expression in which Robot Framework variables are replaced. After a successful change, the Variables view and the rest of the run SHALL use the new value. A value the debugger rejects SHALL show the debugger's error message and leave the variable unchanged. Set Value SHALL NOT be offered for variables of outer frames, for the Test, Suite and Global groups, or for items of lists and dictionaries.

#### Scenario: Change a variable

- **WHEN** the run is paused before `Log    ${x}`, the user sets `${x}` to `'changed'` and resumes
- **THEN** the Variables view shows `'changed'` for `${x}` before the resume, and `Log    ${x}` logs `changed`

#### Scenario: Invalid value

- **WHEN** the user sets `${x}` to the bare word `changed`
- **THEN** the IDE shows the debugger's error message and `${x}` keeps its value

#### Scenario: Not offered for suite variables

- **WHEN** the user opens the context menu of a variable in the Suite group
- **THEN** Set Value is not available

### Requirement: Frames show their keyword, test or suite

The Frames view SHALL show each frame with the name of its keyword, test or suite, followed by its file name and line in a secondary color. Frames without a source file SHALL be shown dimmed. Selecting a frame SHALL show its source at the frame's line and column.

#### Scenario: Paused inside a keyword

- **WHEN** the run is paused inside a user keyword called from a test
- **THEN** the top frame shows the keyword's name with its file and line, the frames below show the test and the suites, and a directory suite without a source file is dimmed

### Requirement: Expanded variables stay expanded across steps

After a step or a resume to the next stop, the Variables view SHALL restore the groups and values the user had expanded, as long as the selected frame belongs to the same keyword, test or suite at the same depth of the stack.

#### Scenario: Step over in a test

- **WHEN** the user expands the Suite and Global groups and a dictionary variable inside the Suite group, and then steps over a keyword call in the same test
- **THEN** the Suite and Global groups and the dictionary are still expanded at the next stop
