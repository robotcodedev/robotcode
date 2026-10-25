## MODIFIED Requirements

### Requirement: Keyword and type entries in JSON

Each keyword entry SHALL have `name`, `anchor` (the anchor of its heading in `markdown`), `args` (its arguments as one line of text), `short_doc` (the first paragraph of its documentation), `tags`, `doc` (its documentation as Markdown), and `source` and `lineno`, the file of the keyword and its line, empty and `-1` when they are unknown. Each type entry SHALL have `name` and `anchor`, the anchor of its heading in `markdown`, to which the links to the type in `markdown` point.

#### Scenario: Fields of a keyword entry
- **WHEN** `robotcode --format json doc lib Collections` is run
- **THEN** every keyword entry has `name`, `anchor`, `args`, `short_doc`, `tags`, `doc`, `source` and `lineno`

#### Scenario: Source of a library keyword
- **WHEN** `robotcode --format json doc lib Collections` is run
- **THEN** the entry of `Append To List` has the path of `Collections.py` as `source` and the line of its method as `lineno`

#### Scenario: Source of a resource keyword
- **WHEN** `robotcode --format json doc lib` is run for a resource file
- **THEN** each keyword entry has the path of the resource file as `source` and the line of its definition as `lineno`
