## ADDED Requirements

### Requirement: Suggestions under the target field

While the target field has the focus, the viewer SHALL show a list of suggestions under it when the user types, presses Ctrl+Space, on macOS also Option+Escape, or presses Down. The list SHALL show the completion of the name. For an empty field, and when nothing completes the text, the list SHALL stay closed. It SHALL close on Escape, when the field loses the focus, and when a target loads.

#### Scenario: Typing a name

- **WHEN** the user types `Coll` in the target field
- **THEN** a list under the field offers `Collections`

#### Scenario: Ctrl+Space

- **WHEN** the user has typed `Coll` and closed the list with Escape, and presses Ctrl+Space
- **THEN** the list offers `Collections` again

#### Scenario: Option+Escape on macOS

- **WHEN** on macOS the user has typed `Coll` and closed the list with Escape, and presses Option+Escape
- **THEN** the list offers `Collections` again

#### Scenario: Down

- **WHEN** the field holds `XM`, the list is closed, and the user presses Down
- **THEN** the list offers `XML`

#### Scenario: Empty field

- **WHEN** the user clears the target field and presses Down
- **THEN** no list opens

#### Scenario: Escape

- **WHEN** the list is open and the user presses Escape
- **THEN** the list closes and the field keeps the typed text

### Requirement: Completion of the target's name

The list SHALL complete the text before the first `::` as RobotCode completes `Library` and `Resource` imports in the editor: modules on the Python path, the standard libraries, and library, resource and suite files and directories, relative to the viewer's workspace folder or absolute. It SHALL offer one level at a time, the names that start with the typed part of that level, without regard to case. A text that contains `::` SHALL get no completion.

#### Scenario: Standard library

- **WHEN** the user types `Coll`
- **THEN** the list offers `Collections`

#### Scenario: Directory and file of the folder

- **WHEN** the workspace folder contains `resources/shop.resource`, and the user types `res`
- **THEN** the list offers the directory `resources`
- **AND** after the user types `resources/`, the list offers `shop.resource`

#### Scenario: Module on the Python path

- **WHEN** the setting `robotcode.robot.pythonPath` holds `libraries`, the directory `libraries` contains `ShopLibrary.py`, and the user types `Shop`
- **THEN** the list offers `ShopLibrary`

#### Scenario: Import arguments

- **WHEN** the list offers `Collections`, and the user types `Collections::`
- **THEN** the list closes

### Requirement: Choosing a suggestion

In the open list, Up and Down SHALL select a suggestion. Enter SHALL put the selected suggestion into the target field and load it, and a click on a suggestion SHALL do the same. Tab SHALL put it into the field without loading it. Enter and Tab SHALL put a selected directory into the field with a `/` at its end, and the list SHALL then offer its content. Enter without a selected suggestion SHALL load the text of the field, as before.

#### Scenario: Enter on a file

- **WHEN** the list offers `shop.resource` for `resources/`, and the user selects it and presses Enter
- **THEN** the viewer shows `resources/shop.resource`

#### Scenario: Enter on a directory

- **WHEN** the list offers the directory `resources`, and the user selects it and presses Enter
- **THEN** the field holds `resources/`, the list offers `shop.resource`, and the viewer still shows the page it showed before

#### Scenario: Tab

- **WHEN** a viewer shows `BuiltIn`, the list offers `Collections`, and the user selects it and presses Tab
- **THEN** the field holds `Collections`, the list is closed, and the viewer still shows `BuiltIn`

#### Scenario: Click

- **WHEN** the list offers `Collections` and the user clicks it
- **THEN** the viewer shows `Collections`

#### Scenario: Enter without a selected suggestion

- **WHEN** the user types `XML` while the list is open, and presses Enter without selecting a suggestion
- **THEN** the viewer shows `XML`

### Requirement: No suggestions without a language server

While no language server of RobotCode runs for the viewer's workspace folder, the list SHALL stay closed, and the viewer SHALL NOT start a language server for it. This holds while the folder's Python environment is not usable yet and when RobotCode is switched off for the folder.

#### Scenario: Environment without Robot Framework

- **WHEN** the Python environment of the folder has no Robot Framework, and the user types `Coll`
- **THEN** no list opens

### Requirement: The suggestion list for screen readers

Screen readers SHALL announce the target field as a combobox that controls the list, the list as a list of suggestions, and the selected suggestion with its kind, such as a module, a file or a directory.

#### Scenario: Selected suggestion

- **WHEN** the list is open and the user selects `Collections` with Down
- **THEN** the accessibility tree has the target field as an expanded combobox whose active descendant is the option `Collections`, with its kind
