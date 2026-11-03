# Spec Delta

## MODIFIED Requirements

### Requirement: What a name in single backticks can link to

The name can be a keyword, a section of the introduction, one of the default sections (introduction, importing, keywords) or a data type; data types are linked by the requirement "Data types". Names in headings SHALL stay as they are. Names in preformatted text SHALL NOT be links and SHALL lose their backticks, so that the text can be copied.

#### Scenario: Default section
- **WHEN** a Robot-format keyword documentation names `` `Keywords` ``
- **THEN** the name links to `#keywords`

#### Scenario: Name in a heading
- **WHEN** a Robot-format documentation has the heading ``= `Alpha Kw` =``
- **THEN** the heading of the page shows `` `Alpha Kw` ``, without a link

#### Scenario: Name in preformatted text
- **WHEN** a Robot-format documentation has the preformatted line ``| `Alpha Kw`    foo`` and the library has the keyword `Alpha Kw`
- **THEN** the code block of the page contains `Alpha Kw    foo`, without backticks
