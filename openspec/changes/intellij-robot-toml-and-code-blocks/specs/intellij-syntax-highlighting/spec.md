## ADDED Requirements

### Requirement: Robot Framework code blocks in Markdown

In Markdown files, the IntelliJ plugin SHALL treat code blocks marked `robotframework` or `robot` as Robot Framework code, so that the editor and the Markdown preview highlight them as Robot Framework. Code blocks marked with other languages SHALL stay as the IDE handles them. While the IDE's Markdown support is disabled, the plugin SHALL work as without this.

#### Scenario: Code block marked robot

- **WHEN** a Markdown file has a code block marked `robot` with a `*** Keywords ***` section
- **THEN** the block is Robot Framework code in the editor, and the editor and the preview highlight its section header

#### Scenario: Code block marked robotframework

- **WHEN** a Markdown file has a code block marked `robotframework` with a `*** Test Cases ***` section
- **THEN** the block is Robot Framework code, as it is without this change

#### Scenario: Code block of another language

- **WHEN** a Markdown file has a code block marked `python`
- **THEN** the block is Python code
