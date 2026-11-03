# Spec Delta

## ADDED Requirements

### Requirement: Code keeps the text of the documentation

When documentation in Robot Framework's format is converted to Markdown, on every surface and every supported Robot Framework version, code SHALL keep the text as written, so that a reader can copy it and paste it without rework. Code is text in double backticks, whatever else Markdown reads as a code span, and preformatted blocks. Nothing in code SHALL be escaped or become bold, italic, a link or an image.

#### Scenario: Characters that plain text escapes
- **WHEN** a Robot-format documentation writes ``` ``vscode/<n>`` ``` and ``` ``#FF00FF`` ```
- **THEN** the rendered documentation contains `` `vscode/<n>` `` and `` `#FF00FF` ``

#### Scenario: The same characters in plain text
- **WHEN** a Robot-format documentation writes `a < b` and `issue #42` outside of code
- **THEN** the rendered documentation contains `a \< b` and `issue \#42`

#### Scenario: Bold and italic markers in code
- **WHEN** a Robot-format documentation writes ``` ``a *b* c`` ``` and ``` ``a _b_ c`` ```
- **THEN** the rendered documentation contains `` `a *b* c` `` and `` `a _b_ c` ``

#### Scenario: URL in code
- **WHEN** a Robot-format documentation writes ``` ``see http://example.com/x now`` ```
- **THEN** the rendered documentation contains `` `see http://example.com/x now` ``

#### Scenario: Bold around code
- **WHEN** a Robot-format documentation writes ``` *bold ``<a>`` bold* ```
- **THEN** the rendered documentation contains `` **bold `<a>` bold** ``

#### Scenario: Name without a link target
- **WHEN** a Robot-format documentation writes `` `<x>` `` and nothing can be linked to that name
- **THEN** the rendered documentation contains `` `<x>` ``

#### Scenario: Double backticks that Robot Framework does not read as code
- **WHEN** a Robot-format documentation writes ``` ``<a>``s ```
- **THEN** the rendered documentation contains ``` ``<a>``s ```

#### Scenario: Backtick in code
- **WHEN** a Robot-format documentation writes ``` ``a`b`` ```
- **THEN** the rendered documentation shows one code span with the text ``a`b``

#### Scenario: Section header in a preformatted block
- **WHEN** a Robot-format documentation has the preformatted line `| *** Test Cases ***`
- **THEN** the code block in the rendered documentation contains `*** Test Cases ***`

### Requirement: Markup of links and names falls away in code

In code, the markup of links and names, which Libdoc does not show either, SHALL fall away and its text SHALL stay: a link `[target|text]` becomes `text`, and a name in single backticks inside code becomes the name. Text around the markup SHALL stay as written.

#### Scenario: Name in a preformatted block
- **WHEN** a Robot-format documentation has the preformatted line ``| `Add Cookie`   foo   bar``
- **THEN** the code block in the rendered documentation contains `Add Cookie   foo   bar`

#### Scenario: Link in a preformatted block
- **WHEN** a Robot-format documentation has the preformatted line `| [https://example.com/x|response] => 1`
- **THEN** the code block in the rendered documentation contains `response => 1`

#### Scenario: Text around a link in a preformatted block
- **WHEN** a Robot-format documentation has the preformatted line `| a | b [x|y] c | d`
- **THEN** the code block in the rendered documentation contains `a | b y c | d`

#### Scenario: Name in a code span
- **WHEN** a Robot-format documentation writes ``` ``x `Alpha Kw` y`` ``` and the library has the keyword `Alpha Kw`
- **THEN** the rendered documentation contains `` `x Alpha Kw y` `` without a link

#### Scenario: Link in a code span
- **WHEN** a Robot-format documentation writes ``` ``see [a|b] now`` ```
- **THEN** the rendered documentation contains `` `see b now` ``

### Requirement: Double backticks fall away in preformatted blocks

In a preformatted block, code in double backticks SHALL lose its backticks, because the whole block already is code.

#### Scenario: Code in a preformatted block
- **WHEN** a Robot-format documentation has the preformatted line ``| Get Text    h1    # Returns ``${True}`` ``
- **THEN** the code block in the rendered documentation contains `Get Text    h1    # Returns ${True}`
