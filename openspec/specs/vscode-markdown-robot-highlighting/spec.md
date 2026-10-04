# Spec: vscode-markdown-robot-highlighting

## Purpose

Defines how VS Code's Markdown preview and the Documentation Viewer highlight Robot Framework code blocks, so that they get colors like the code blocks of other languages there.

## Requirements

### Requirement: Robot Framework code blocks are highlighted in Markdown views

In VS Code's Markdown preview and in the Documentation Viewer, a fenced code block whose language is `robotframework` or `robot`, in any letter case, SHALL be highlighted with Robot Framework's syntax. Section headers, test and keyword names, keyword calls, settings, control structures, variables, comments and numbers SHALL get the colors that the Markdown preview gives these kinds of tokens in other languages, in light, dark and high-contrast themes. The text of the code SHALL stay unchanged. Code blocks of other languages SHALL be highlighted as before.

#### Scenario: Robot code block in the Markdown preview
- **WHEN** a Markdown file contains a `robot` code block with `*** Test Cases ***`, the test `My Test` and the line `    Log    ${x}    # note`, and the file is shown in the Markdown preview
- **THEN** the section header, the test name, the keyword call `Log`, the variable `${x}` and the comment are highlighted, each in another color than the plain text

#### Scenario: Example code in the Documentation Viewer
- **WHEN** the Documentation Viewer shows `BuiltIn` on Robot Framework 7.5
- **THEN** its `robotframework` code blocks are highlighted, with section headers, keyword calls and variables in colors

#### Scenario: Other languages stay as they are
- **WHEN** the Markdown file of the first scenario also contains a `python` code block
- **THEN** the `python` block is highlighted as it was without RobotCode's highlighting

### Requirement: A Markdown preview starts no language server

When RobotCode is activated because a Markdown preview opens, it SHALL NOT start a language server for a workspace folder that contains no Robot Framework files and no open Robot Framework document.

#### Scenario: Markdown preview in a workspace without Robot Framework files
- **WHEN** a workspace contains only Markdown files and the user opens the Markdown preview of one of them
- **THEN** the Robot Framework code blocks in it are highlighted, and no RobotCode language server runs
