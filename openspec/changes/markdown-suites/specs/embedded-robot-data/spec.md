# Spec Delta

## Purpose

Defines how RobotCode recognises, extracts and analyses Robot Framework data embedded in Markdown and reStructuredText files — which files count as suites, resources or init files, how positions map to the file, which editor features apply, how `analyze` and `discover` treat them, and how the VS Code and IntelliJ clients associate them with the language server.

## ADDED Requirements

### Requirement: Embedded files are typed like Robot Framework does

RobotCode SHALL treat `*.robot.rst` (all versions) and `*.robot.md` (RF ≥ 7.5) as suite files, `*.rst`/`*.rest` (all versions) and `*.md`/`*.markdown` (RF ≥ 7.5) as resource files when imported, opened through a configured pattern or passed explicitly, and `__init__.rst`/`__init__.md` as init files (RobotCode's own decision, like its unconditional `__init__.robot` rule; Robot Framework treats them as init files only when `rst`/`md` is a configured suite extension). `__init__.robot.md` SHALL be typed as a suite file; Robot Framework skips it in directory runs like every `_`-prefixed file and parses it only when passed explicitly. Plain Markdown/reST files SHALL NOT be scanned as suites in workspaces unless configured.

#### Scenario: Suite typing on RF 7.5
- **WHEN** `sample.robot.md` is opened on RF 7.5
- **THEN** it is analysed as a suite file

#### Scenario: Markdown suite on RF 7.4
- **WHEN** `sample.robot.md` is opened on RF 7.4
- **THEN** it is not analysed as Robot Framework data

#### Scenario: README stays prose
- **WHEN** a workspace contains `README.md` without configuration for plain Markdown
- **THEN** it is neither preloaded, analysed nor listed by `discover files`

### Requirement: Only Robot Framework code blocks are analysed, at their file positions

Only the content of Markdown fenced blocks (```` ``` ```` or `~~~`, three or more characters, closed by a fence of the same character and at least the same length, whose info string's first word is exactly `robotframework` or `robot`, case-insensitive, further words ignored; an unclosed block at end of file included; an empty closed block contributes one empty line) and of reStructuredText `code`/`code-block`/`sourcecode` directives with the `robotframework` argument SHALL be analysed, exactly the blocks Robot Framework executes. Every reported position (diagnostics, hover, definitions, references, semantic tokens, symbols, ranges) SHALL refer to the file's own line and column, including for blocks indented inside lists, whose common margin Robot Framework removes.

#### Scenario: Indented fenced block
- **WHEN** a `.robot.md` file contains a `robotframework` fence indented by four spaces inside a list item, with a test named `Indented Test` at file line 14, column 5
- **THEN** the test's document symbol and definition range start at line 14, column 5
- **AND** the analysis result equals Robot Framework's parsing of the dedented block

#### Scenario: Prose is ignored
- **WHEN** the prose of a `.robot.md` file contains text that looks like Robot Framework syntax outside a fence
- **THEN** no diagnostics, tokens or symbols are produced for those lines

#### Scenario: Parity with Robot Framework
- **WHEN** the extracted, concatenated text of a `.robot.md` or `.robot.rst` file is compared with what Robot Framework's own reader produces for the same file
- **THEN** they are identical

### Requirement: Embedded resources resolve their keywords

A `Resource` import of a Markdown (RF ≥ 7.5) or reStructuredText resource SHALL load the keywords defined in its code blocks; no "resource is empty" warning SHALL be reported for a resource with keywords, and keyword definitions SHALL point to the file line inside the block.

#### Scenario: Keyword from a reST resource
- **WHEN** a suite imports `keywords.rst` whose code block defines `Greet` and calls `Greet`
- **THEN** no `ResourceEmpty` or `KeywordNotFound` diagnostic is reported
- **AND** go-to-definition on `Greet` opens `keywords.rst` at the keyword's line

### Requirement: Whole-document edits are withheld for embedded documents

For embedded documents RobotCode SHALL NOT offer formatting, quick fixes that append to the end of the file or refactorings that rewrite the document text; other code actions and edits inside code blocks SHALL work. Robocop diagnostics SHALL be computed on the extracted text.

#### Scenario: Format request
- **WHEN** formatting is requested for `sample.robot.md`
- **THEN** no edit is returned and the file is unchanged

### Requirement: Missing docutils is reported, not raised

When a reStructuredText file is opened and docutils is not installed, RobotCode SHALL report one diagnostic at the start of the file stating that reStructuredText data requires docutils, and SHALL treat the file as containing no Robot Framework data.

#### Scenario: reST without docutils
- **WHEN** `sample.robot.rst` is opened in an environment without docutils
- **THEN** exactly one diagnostic about the docutils requirement is reported and no exception is logged

### Requirement: discover and analyze cover embedded suites

`discover` SHALL report the file line of tests in embedded suites in `lineno`, `range` and item ids, also for content read from stdin; `discover files` SHALL list `*.robot.rst` and, on RF ≥ 7.5, `*.robot.md`; `analyze code` SHALL scan them in workspace folders and SHALL analyse any Markdown/reST file passed explicitly.

#### Scenario: Test line in a Markdown suite
- **WHEN** `robotcode --format json discover tests` runs on RF 7.5 for a `.robot.md` whose test `Indented Test` is at file line 14
- **THEN** the item reports `lineno` 14 and a `range` starting at line 13 (zero-based)

#### Scenario: Explicit analyze of a Markdown resource
- **WHEN** `robotcode analyze code keywords.md` runs on RF 7.5
- **THEN** one file is analysed

### Requirement: Editor clients keep the host language and still get language features

In VS Code, files matching the configured embedded-file patterns (default `**/*.robot.md` and `**/*.robot.rst`) SHALL keep their Markdown/reStructuredText language and SHALL receive RobotCode language features, test-explorer items, and run/debug commands. In IntelliJ, `*.robot.md`/`*.robot.rst` SHALL be sent to the language server as Robot Framework documents while keeping their file type.

#### Scenario: Hover in a Markdown suite in VS Code
- **WHEN** `sample.robot.md` is open in VS Code with the default patterns on RF 7.5
- **THEN** the Markdown preview works and hovering a keyword inside a fence shows its documentation
- **AND** the test explorer shows the suite's tests at their file lines
