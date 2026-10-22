## ADDED Requirements

### Requirement: The Ctrl+hover hint shows the documentation without extra empty lines

Holding Ctrl over a name in a Robot Framework file SHALL show the documentation in its hint with the spacing of Quick Documentation. A table SHALL follow its heading directly, headings and paragraphs SHALL get no additional empty line, and code blocks SHALL keep their line breaks. Quick Documentation and the hover without Ctrl SHALL show the same documentation without any markup as text.

#### Scenario: Arguments of a keyword

- **WHEN** Ctrl is held and the mouse rests on `Open Shop As` in `shop.Open Shop As    alice`
- **THEN** the hint shows the rows of the argument table below the heading "Arguments:", spaced as in Quick Documentation

#### Scenario: Library import

- **WHEN** Ctrl is held and the mouse rests on `Collections` in `Library    Collections`
- **THEN** the hint shows the library's version and scope below the heading "Library *Collections*", spaced as in Quick Documentation

#### Scenario: Paragraphs of the documentation

- **WHEN** Ctrl is held and the mouse rests on `Log` in `Log    Opened ${BASE_URL} as ${user}`
- **THEN** the paragraphs of the keyword's documentation are as far apart as in Quick Documentation

#### Scenario: Code block

- **WHEN** Ctrl is held and the mouse rests on `shopvars.py` in `Variables    ../libraries/shopvars.py`
- **THEN** the hint shows each variable of the file on its own line

#### Scenario: Quick Documentation and the hover without Ctrl

- **WHEN** Quick Documentation is opened on `Collections` in `Library    Collections`, or the mouse rests on it without Ctrl
- **THEN** the documentation shows the heading, the library's version and scope and the introduction, and no markup as text
