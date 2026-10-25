## ADDED Requirements

### Requirement: The context menu of the outline

A right-click on a row of a viewer's outline SHALL show a menu with Open, which shows the entry as a click on the row does, Open in New Documentation Viewer, which shows the target at the entry in a new viewer, and Add Bookmark, or Remove Bookmark while the entry's place is bookmarked for the viewer's folder. The menu SHALL hold no Cut, Copy and Paste. The context menu key and Shift+F10 SHALL open it on the focused row.

#### Scenario: Menu of a keyword

- **WHEN** the user right-clicks `Get From Dictionary` in the outline of `Collections`
- **THEN** the menu offers Open, Open in New Documentation Viewer, Add Bookmark and Go to Source, and no Cut, Copy or Paste

#### Scenario: Open

- **WHEN** the user chooses Open in the menu of `Get From List`
- **THEN** the viewer shows `Get From List`, and back returns to the place before

#### Scenario: Open in a new viewer

- **WHEN** the user chooses Open in New Documentation Viewer in the menu of `Get From List` of `Collections`
- **THEN** a new viewer shows `Collections` at `Get From List`, and the first viewer stays at its place

#### Scenario: Add Bookmark

- **WHEN** the user chooses Add Bookmark in the menu of `Get From List` while the viewer shows the top of the page
- **THEN** the bookmark `Collections › Get From List` exists in the viewer's folder, and the page stays at its top

#### Scenario: Remove Bookmark

- **WHEN** the bookmark `Collections › Get From List` exists, and the user opens the menu of `Get From List`
- **THEN** the menu offers Remove Bookmark in place of Add Bookmark, and choosing it removes the bookmark

#### Scenario: Rows without a source

- **WHEN** the user right-clicks the row `Keywords`, a heading of the introduction, or a data type
- **THEN** the menu offers Open, Open in New Documentation Viewer and Add Bookmark, without Go to Source

#### Scenario: With the keyboard

- **WHEN** a row of the outline has the focus, and the user presses Shift+F10
- **THEN** the menu of that row opens

#### Scenario: Filter field and page

- **WHEN** the user right-clicks in the filter field of the outline or on the page
- **THEN** VS Code's menu with Cut, Copy and Paste opens there

### Requirement: Go to Source from the outline

The menu of a keyword whose file and line are known SHALL offer Go to Source, which SHALL open the file at the keyword's line: a resource or suite file, a library of the project, or a library of the Python environment. The file SHALL open in the editor group of the text editor used last, or beside the viewer without one. The menus of other keywords, of data types and of headings SHALL NOT offer it.

#### Scenario: Keyword of a resource file

- **WHEN** a viewer shows `resources/shop.resource`, and the user chooses Go to Source in the menu of one of its keywords
- **THEN** an editor shows `shop.resource` at the line of that keyword

#### Scenario: Keyword of a library of the Python environment

- **WHEN** the user chooses Go to Source in the menu of `Get From Dictionary` of `Collections`
- **THEN** an editor shows `Collections.py` of the folder's Python environment at the method of `Get From Dictionary`

#### Scenario: Group of the text editor used last

- **WHEN** a viewer is beside a `.robot` file, and the user chooses Go to Source
- **THEN** the file opens in the group of the `.robot` file, and the viewer stays visible

#### Scenario: Without a text editor

- **WHEN** no text editor was used since VS Code started, and the user chooses Go to Source
- **THEN** the file opens beside the viewer

### Requirement: Documentation does not change the menu

HTML in documentation SHALL NOT change what the context menu of a viewer offers.

#### Scenario: Context in documentation

- **WHEN** a library documented in HTML format contains an element with the attribute by which a webview sets the context of VS Code's menu, and the user right-clicks the element
- **THEN** VS Code's menu with Cut, Copy and Paste opens, without the entries of the outline's menu
