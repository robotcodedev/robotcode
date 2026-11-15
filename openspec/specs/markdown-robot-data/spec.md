# markdown-robot-data Specification

## Purpose

Defines how RobotCode analyses the Markdown files it serves (see `document-formats`): which code blocks hold Robot Framework data and at which positions, where editor features apply, where code placed by code actions goes, how Robocop treats these files, and how `analyze code` checks them.

## Requirements

### Requirement: Only the code blocks Robot Framework reads are analysed

In a Markdown file RobotCode serves, it SHALL analyse exactly the code blocks Robot Framework executes. A block opens at a line that starts, after any whitespace, with at least three backticks or tildes followed by `robot` or `robotframework` in any letter case, and closes at a line of only the same character, at least as many; an unclosed block runs to the end of the file. Other lines SHALL produce no diagnostics, tokens or symbols.

#### Scenario: Prose that looks like Robot syntax
- **WHEN** a `.robot.md` file has the line `*** Test Cases ***` in its prose, outside any code block
- **THEN** no section, test, diagnostic or semantic token is produced for that line

#### Scenario: Tilde fence with a longer closing fence
- **WHEN** a block opens with the line `~~~ Robot` and closes with the line `~~~~~`
- **THEN** its content is analysed

#### Scenario: Same blocks as Robot Framework
- **WHEN** the blocks RobotCode finds in a Markdown file are compared with the lines Robot Framework keeps from that file
- **THEN** every line Robot Framework keeps lies in one of RobotCode's blocks

### Requirement: Blocks continue the blocks before them

Robot Framework reads all blocks of a file as one text. RobotCode SHALL therefore treat a block that does not start with a section header as continuing the section of the block before, and indented lines at its start as continuing the test or keyword there.

#### Scenario: Test continued in the next block
- **WHEN** the first block ends inside the test `First Test` and the next block starts with the indented line `    Log    second step`
- **THEN** that line is analysed as a step of `First Test`

### Requirement: Positions are those of the file

Every position RobotCode reports for a Markdown file, such as of diagnostics, hovers, definitions, references, semantic tokens, symbols and ranges, SHALL be the line and column in the file, also in an indented code block whose indentation Robot Framework removes.

#### Scenario: Indented code block
- **WHEN** a `robotframework` block is indented by four spaces inside a list item and defines the test `Indented Test` at line 14, column 5 of the file
- **THEN** the test's document symbol starts at line 14, column 5

### Requirement: File names follow Robot Framework

A served Markdown file named `__init__` with an active extension other than `robot.md` SHALL be an init file. `__init__.robot.md` SHALL be a suite file, because Robot Framework does not read it as an init file. Every other served Markdown file SHALL be a suite file.

#### Scenario: Init file
- **WHEN** the extension `md` is active and a folder contains `__init__.md`
- **THEN** RobotCode analyses it with the rules of an init file

#### Scenario: Init-named Markdown suite
- **WHEN** the extension `robot.md` is active and a folder contains `__init__.robot.md`
- **THEN** RobotCode analyses it as a suite file

### Requirement: Completion is offered only inside code blocks

In a Markdown file, RobotCode SHALL offer completion only on lines inside a code block, including empty lines in a block and blocks that hold only empty lines, and never in prose or on fence lines.

#### Scenario: Prose
- **WHEN** completion is requested after the word `Log` in a prose line of a `.robot.md` file
- **THEN** RobotCode returns no completion items

#### Scenario: Block with only an empty line
- **WHEN** completion is requested on the empty line of a block that consists of the fence lines and one empty line
- **THEN** RobotCode returns completion items

### Requirement: Ranges stay inside code blocks

In a Markdown file, folding ranges, selection ranges and the ranges of document symbols SHALL start and end on lines inside code blocks; prose and fence lines after the last line of an element SHALL NOT belong to its range.

#### Scenario: Keyword followed by prose
- **WHEN** the keyword `Greet` is the last element of a block that is followed by prose and another block
- **THEN** the folding range and the symbol range of `Greet` end at its last line inside the first block

### Requirement: Code placed by code actions lands inside a code block

Code that a code action places itself in a Markdown file, such as the keyword of "Create Keyword" or "Extract keyword" or the variable of "Create suite variable", SHALL be inserted inside a code block: after the last line of the section it extends, or, when a new section is needed, at the end of the last code block. Prose and fence lines SHALL stay unchanged.

#### Scenario: New keyword section
- **WHEN** "Create Keyword" is applied for an undefined keyword call in a `.robot.md` file without keyword section, whose last code block is followed by prose
- **THEN** `*** Keywords ***` and the new keyword are inserted before the closing fence of the last code block, and the prose is unchanged

#### Scenario: Existing keyword section
- **WHEN** the file's first code block ends with a keyword section and is followed by prose and a second block with tests
- **THEN** the new keyword is inserted after the last keyword of that section, before the closing fence of the first block

### Requirement: Robocop checks and formats Markdown files itself

For a Markdown file, RobotCode SHALL use Robocop's own support for Markdown files, with the current text of the editor: Robocop's findings are reported at their positions in the file, and formatting returns Robocop's result. With a Robocop older than 9.2, RobotCode SHALL report no Robocop findings for Markdown files, and a formatting request SHALL return no edit and tell the user that formatting Markdown files needs Robocop 9.2 or newer.

#### Scenario: Prose is not checked
- **WHEN** a `.robot.md` file has several empty prose lines between two code blocks, with Robocop 9.2 or newer
- **THEN** Robocop reports no finding about consecutive empty lines

#### Scenario: Formatting a block
- **WHEN** formatting is requested for a `.robot.md` file whose code block contains `    Log      badly   spaced`, with Robocop 9.2 or newer
- **THEN** that line becomes `    Log    badly    spaced`, and the prose and fence lines are unchanged

#### Scenario: Older Robocop
- **WHEN** Robocop 9.1 is installed and formatting is requested for a `.robot.md` file
- **THEN** no edit is returned, the user is told that Robocop 9.2 or newer is needed, and no Robocop finding is reported for the file

### Requirement: analyze code checks the Markdown files RobotCode serves

`robotcode analyze code` SHALL check the Markdown files RobotCode serves in the workspace like `.robot` files, and SHALL NOT check other Markdown files.

#### Scenario: Markdown suite and README
- **WHEN** `robotcode analyze code` runs in a project whose robot.toml sets no `extensions`, on Robot Framework 7.5.1, with `shop.robot.md`, which calls an undefined keyword, and `README.md`
- **THEN** a "keyword not found" diagnostic is reported for `shop.robot.md`, and `README.md` is not analysed
