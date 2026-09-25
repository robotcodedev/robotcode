# Spec Delta

<!-- `robotcode doc` is the working name of the command; the final name is design question Q2. -->

## Purpose

Defines RobotCode's documentation command: which targets it documents, how it resolves them with the project's configuration, how it shows, writes, lists and searches their canonical documentation, how it reports errors, and the terminal documentation browser it opens on an interactive terminal.

## ADDED Requirements

### Requirement: Only explicitly named targets are documented

`robotcode doc` SHALL document exactly the targets given on its command line, one or more per call, in the given order. A target SHALL be a library name (a standard library, a module or `module.Class`), a path to a library file or directory, either of them followed by import arguments in Libdoc's `Name::arg1::arg2` form, or a path to a file with an extension Robot Framework accepts for resource imports in the installed version (suite files included, documented with their keywords). Without a target the command SHALL fail with a usage error. `robotcode libdoc` SHALL remain an unchanged pass-through to Robot Framework's Libdoc.

#### Scenario: Library and resource in one call
- **WHEN** `robotcode doc Collections resources/common.resource` is run with the output piped
- **THEN** the output contains the canonical documentation of `Collections` followed by that of `common`

#### Scenario: No target
- **WHEN** `robotcode doc` is run without a target
- **THEN** it prints a usage error and exits with code 2

### Requirement: Targets resolve like the analysis resolves imports

Targets SHALL be resolved the way RobotCode's analysis resolves imports of the project: with the `robot.toml` configuration and the selected profiles (python path, variables, variable files, environment variables), the library-loading settings of `[tool.robotcode-analyze]` (`load-library-timeout`, the cache settings) and the analysis disk cache, plus the `-v/--variable`, `-V/--variablefile` and `-P/--pythonpath` options given to the command. Variables in import arguments SHALL be resolved as in an import; relative paths SHALL be resolved against the current working directory.

#### Scenario: Library found through the configured python path
- **WHEN** `robot.toml` sets `python-path = ["lib"]`, `lib/MyLib.py` defines the library `MyLib`, and `robotcode doc MyLib` is run in the project root
- **THEN** the documentation of `MyLib` is shown

#### Scenario: Import arguments with a variable
- **WHEN** a dynamic library `ArgLib` returns the keyword `Kw <mode>` for its import argument `mode`, `robot.toml` defines the variable `MODE = "b"`, and `robotcode doc 'ArgLib::${MODE}'` is run
- **THEN** the documentation lists the keyword `Kw B` (Robot Framework capitalises the returned name)
- **AND** its metadata shows the import argument `${MODE}` as given

#### Scenario: Variable given on the command line
- **WHEN** `robotcode doc -v MODE:c 'ArgLib::${MODE}'` is run in the same project while no documentation of `ArgLib` is in the analysis disk cache (which keeps one entry for this library, whatever its import arguments)
- **THEN** the documentation lists the keyword `Kw C`

### Requirement: Output modes

When standard input and standard output are an interactive terminal, the session is no AI-agent session as RobotCode detects it for its colour and pager defaults, and neither `-o/--output`, `--no-tui`, `-k/--keyword`, `--list` nor a search option is given, the command SHALL open the documentation browser with the given documents. An explicit `--tui` SHALL open the browser in an AI-agent session as well, as explicit colour and pager options take precedence over the agent detection; `--tui` without an interactive terminal SHALL be a usage error. Otherwise it SHALL write the canonical Markdown of all given documents through RobotCode's terminal output: rendered on a coloured terminal, as raw Markdown with `--no-color`, in a pipe and in an AI-agent session, paged according to `--pager/--no-pager`. With `-o/--output PATH` the Markdown SHALL be written to that file instead; when `PATH` is an existing directory or ends with a path separator, one file per document SHALL be written into it. Files SHALL be UTF-8 with `\n` line endings on every platform.

#### Scenario: Piped output
- **WHEN** `robotcode doc Collections` is run with standard output piped
- **THEN** the output is the raw canonical Markdown of `Collections` and nothing else

#### Scenario: One output file for several targets
- **WHEN** `robotcode doc -o all.md Collections String` is run
- **THEN** `all.md` contains the canonical documentation of `Collections` followed by that of `String` and nothing is written to standard output

#### Scenario: Interactive terminal
- **WHEN** `robotcode doc Collections` is run in an interactive terminal outside an AI-agent session
- **THEN** the documentation browser opens with the documentation of `Collections`

#### Scenario: Interactive terminal without the browser
- **WHEN** `robotcode --no-color --no-pager doc --no-tui Collections` is run in an interactive terminal
- **THEN** the raw canonical Markdown of `Collections` is written to standard output

#### Scenario: AI-agent session
- **WHEN** `robotcode doc Collections` is run in an interactive terminal of an AI-agent session
- **THEN** the canonical Markdown of `Collections` is written to standard output without colour and without a pager
- **AND** with `--tui` the documentation browser opens instead

### Requirement: One file per document with links between them

In directory output each document SHALL be written as `<name>.md`, where `<name>` is the document's library or resource name; a further document with a name already written in the same call SHALL get a numeric suffix (`<name>-2.md`, …). A reference in one written document to the name of another document written in the same call — a Markdown reference link `[Name]` or a backtick name `` `Name` `` in Robot-format or plain-text documentation that does not name a keyword, type or section of its own document — SHALL link to that document's file, also when the document's introduction defines `Name` as a reference link to an external URL.

#### Scenario: Documentation website
- **WHEN** `robotcode doc -o site/ BuiltIn Collections` is run on RF 7.5
- **THEN** `site/BuiltIn.md` and `site/Collections.md` are written
- **AND** the reference `[BuiltIn]` in the introduction of `Collections.md` links to `BuiltIn.md`, although `Collections` defines `[BuiltIn]` as a link to robotframework.org

#### Scenario: Two resources with the same name
- **WHEN** `robotcode doc -o site/ a/common.resource b/common.resource` is run
- **THEN** `site/common.md` documents `a/common.resource` and `site/common-2.md` documents `b/common.resource`

### Requirement: Keyword selection

`-k/--keyword PATTERN`, repeatable, SHALL restrict the output to the keywords whose names match one of the patterns, with `*` and `?` as wildcards and case and spaces ignored, as `libdoc … show` matches names. For each given document the output SHALL keep the level-1 heading, the metadata and the `Keywords` section with the matching entries, and leave out `Introduction`, `Importing` and `Data types`. When no keyword of any given document matches, the command SHALL say so on standard error and exit with a non-zero code.

#### Scenario: One keyword
- **WHEN** `robotcode doc -k "get match count" Collections` is run with the output piped
- **THEN** the output contains the heading `Collections`, its metadata and exactly one keyword entry, `Get Match Count`

#### Scenario: Wildcard pattern
- **WHEN** `robotcode doc -k "*dictionary*" Collections` is run
- **THEN** every keyword entry in the output has `dictionary` in its name, case-insensitively, and every such keyword of `Collections` is present

#### Scenario: No match
- **WHEN** `robotcode doc -k "No Such Keyword" Collections` is run
- **THEN** standard error reports that no keyword matched and the exit code is not 0

### Requirement: Keyword listing

`--list` SHALL print, for each given document in order, its name and every keyword (or every keyword selected by `-k`) in the canonical order, each with the first paragraph of its documentation on one line.

#### Scenario: Listing a library
- **WHEN** `robotcode doc --list Collections` is run with the output piped on RF 7.5
- **THEN** the output names `Collections` and has one line per keyword, the first being `Append To List` with "Adds `values` to the end of `list`."

### Requirement: Search across documents

`--search TEXT` SHALL find the keywords of all given documents whose name, documentation, argument names, types, default values and descriptions, return or raises descriptions or tags contain `TEXT`, case-insensitively; `--search-regex PATTERN` SHALL do the same with a regular expression. Tags SHALL be compared after Robot Framework's tag normalisation, and both options SHALL behave like the `--search` and `--search-regex` options of `robotcode results` and `robotcode discover`, including their mutual exclusion. The matches SHALL be printed like `--list`, grouped by document. A search without matches SHALL report that nothing was found and exit with code 0.

#### Scenario: Search two libraries
- **WHEN** `robotcode doc --search dictionary Collections BuiltIn` is run
- **THEN** the output lists `Get From Dictionary` under `Collections` and `Create Dictionary` under `BuiltIn`

#### Scenario: Search by tag
- **WHEN** a resource keyword is tagged `smoke test` and `robotcode doc --search smoke_test common.resource` is run
- **THEN** that keyword is listed

#### Scenario: Both search options
- **WHEN** `--search` and `--search-regex` are given together
- **THEN** the command fails with a usage error

### Requirement: Load errors and exit code

A target whose documentation has load errors, including a library that cannot be imported, SHALL still produce its document (with the errors in its `Importing` section), the errors SHALL also be reported on standard error, and the exit code SHALL NOT be 0. The other targets of the same call SHALL be documented normally.

#### Scenario: One library cannot be imported
- **WHEN** `robotcode doc -o site/ Collections NoSuchLib` is run
- **THEN** `site/Collections.md` is complete and `site/NoSuchLib.md` contains the import error in its `Importing` section
- **AND** the import error is reported on standard error and the exit code is not 0

### Requirement: Terminal documentation browser

The documentation browser SHALL show a sidebar next to a content pane. The sidebar SHALL list, for each document, the `Introduction` with its sections, `Importing`, the `Keywords` with their count, the `Data types` and the tags used by the keywords, each only when the document has it, in the order of the document; selecting an entry SHALL scroll the content pane to it. A keyword filter SHALL narrow the keyword list to the keywords whose names contain the filter text, case-insensitively, and show the number of shown and of all keywords; selecting a tag SHALL narrow the list to the keywords with that tag. The content pane SHALL be RobotCode's documentation viewer with its text search, link following and back/forward history, and jumps from the sidebar SHALL be part of that history. The sidebar SHALL be hideable, and with several documents each SHALL be reachable from the sidebar.

#### Scenario: Jump to a keyword
- **WHEN** the browser shows `Collections` and `Get Match Count` is selected in the sidebar
- **THEN** the content pane shows the `Get Match Count` entry at the top
- **AND** going back returns the content pane to its previous position

#### Scenario: Filter keywords
- **WHEN** the keyword filter is set to `dict` in the browser showing `Collections`
- **THEN** the keyword list contains only keywords with `dict` in their names and shows their number together with the total number of keywords

#### Scenario: Several documents
- **WHEN** `robotcode doc Collections String` opens the browser
- **THEN** the sidebar offers both documents and selecting a keyword of `String` shows its entry
