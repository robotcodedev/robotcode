# cli-ascii-output Specification

## Purpose

Defines which characters robotcode uses in the text it writes to the console, so that its output works on any stream encoding, such as the ANSI code page Python uses for a pipe on Windows.

## Requirements

### Requirement: Own console text is ASCII

robotcode SHALL compose the text it writes to standard output and standard error from ASCII characters only. This covers help texts, messages, headings, tables, status markers, separators, the REPL's text output, the help of its dot-commands, and the decoration of `robotcode doc`. Text taken from the user's data or a library's documentation SHALL be written as it is.

#### Scenario: Help of every command
- **WHEN** the help of every robotcode command and subcommand is shown
- **THEN** it contains only ASCII characters

#### Scenario: Results on a cp1252 stream
- **WHEN** `robotcode results summary --failed` writes to a stream encoded in cp1252, for a run whose names and messages are ASCII
- **THEN** it exits with 0 and writes only ASCII characters

#### Scenario: Every results command
- **WHEN** `summary`, `show`, `log`, `stats`, `diff` and `compare` with every `--show` view run on a stream encoded in ASCII, for runs whose names and messages are ASCII
- **THEN** each exits with 0

#### Scenario: Help of the dot-commands
- **WHEN** `.help`, and `.help` with the name of each dot-command, run in `robotcode repl` with standard input and output being pipes encoded in ASCII
- **THEN** the output contains only ASCII characters

#### Scenario: No project found
- **WHEN** `robotcode config root` runs in a folder without a project
- **THEN** it reports `Cannot detect root folder.` without an emoji

### Requirement: Status as a name

robotcode SHALL write a status as its name in bold, without an icon.

#### Scenario: Status in the summary
- **WHEN** `robotcode results summary` shows a failed run
- **THEN** the status line reads `- _Status:_ **FAIL**`

#### Scenario: Status of a listed test
- **WHEN** `robotcode results show` lists a passed test
- **THEN** its line starts with `- **PASS**`

### Requirement: ASCII equivalents

robotcode SHALL write `->` for an arrow, `...` for an omission, `, ` between values that belong together, `: ` between a heading and its subject, and ` - ` between an item and its detail.

#### Scenario: Status change in a diff
- **WHEN** `robotcode results diff` shows a test that passed in the baseline and fails now
- **THEN** its line shows `**PASS** -> **FAIL**`

#### Scenario: Heading
- **WHEN** `robotcode results summary` shows `output.xml`
- **THEN** the heading reads `# Summary: output.xml`

#### Scenario: Cut message
- **WHEN** a message is cut to `--message-chars`
- **THEN** it ends with `...`

#### Scenario: Time and duration
- **WHEN** `robotcode results log` shows a keyword that started at 23:51:01 and took 1 ms
- **THEN** its timing reads `_(23:51:01, 1 ms)_`

### Requirement: User data as it is

robotcode SHALL write names, messages, documentation, metadata and paths with the characters they have, also those outside ASCII.

#### Scenario: Name outside ASCII
- **WHEN** `robotcode results show` lists a test named `Grüße ✓` on a stream encoded in UTF-8
- **THEN** the line shows `Grüße ✓`

### Requirement: JSON with escapes

With `--format json` or `--format json_indent`, robotcode SHALL write every character outside ASCII as a JSON `\u` escape.

#### Scenario: Name outside ASCII in JSON
- **WHEN** `robotcode --format json results show` lists a test named `Grüße ✓` on a stream encoded in cp1252
- **THEN** it exits with 0
- **AND** the parsed JSON holds the name `Grüße ✓`

### Requirement: Colors only on a stream that takes Unicode

With colors on, robotcode SHALL write its Markdown without colors when the encoding of the stream is not a UTF encoding.

#### Scenario: Colors forced on a cp1252 stream
- **WHEN** `robotcode --color results summary` writes to a stream encoded in cp1252
- **THEN** it exits with 0 and writes the Markdown as without `--color`

### Requirement: Argument kinds in robotcode doc

On the console, `robotcode doc` SHALL mark argument kinds as Libdoc's signatures do: `/` after the positional-only arguments and `*` before the named-only arguments when there is no variable number of positional arguments. The hovers of the language server SHALL keep their markers.

#### Scenario: Signature in the keyword list
- **WHEN** `robotcode doc keywords` lists a keyword `pick_rows(table, /, column, *names, limit: int = 10, **options)`
- **THEN** its signature shows `table, /, column, *names, limit: int = 10, **options` without `⟶` and `🏷`

#### Scenario: Hover keeps its markers
- **WHEN** the language server shows the hover of that keyword
- **THEN** it marks `table` with `⟶` and `limit` with `🏷`, as before
