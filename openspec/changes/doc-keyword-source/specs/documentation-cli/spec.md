# Spec Delta

## MODIFIED Requirements

### Requirement: Subcommands and targets

`robotcode doc` SHALL provide the subcommands `lib`, `keywords`, `keyword`, `source` and `browse`. Each SHALL document exactly one TARGET. A TARGET SHALL be one of:

- a library name, such as a standard library, a module or `module.Class`;
- the path of a library file;
- the path of a resource file with an extension Robot Framework accepts for resource imports in the installed version, including Markdown resource files on RF 7.5.

#### Scenario: Directory as target
- **WHEN** `robotcode doc lib Mysuite` is run in a directory that contains the directory `Mysuite`
- **THEN** the output is the page of an empty library named `Mysuite`, as Libdoc prints it
- **AND** the exit code is 0

#### Scenario: Library by name
- **WHEN** `robotcode doc lib Collections` is run with the output piped
- **THEN** the output is the page of `Collections` defined by `library-documentation-markdown`

#### Scenario: Resource file
- **WHEN** `robotcode doc lib resources/common.resource` is run
- **THEN** the output is the page of `common` with its keywords

#### Scenario: Resource file with another extension
- **WHEN** `robotcode doc keywords plain.txt` is run for a resource file in Robot Framework's plain text format
- **THEN** the overview lists its keywords

#### Scenario: Variable as the target
- **WHEN** `robotcode doc lib -v COMMON:resources/common.resource '${COMMON}'` is run
- **THEN** the output is the page of the resource file `common`

#### Scenario: Backslash in an import argument
- **WHEN** a library documents its import argument and `robotcode doc keyword 'EchoLib::a\b' Echo` is run
- **THEN** the documentation shows the argument `a\b` with its backslash

#### Scenario: Markdown resource file
- **WHEN** `robotcode doc keywords keywords.md` is run on RF 7.5 for a Markdown resource file whose code block defines `Md Kw`
- **THEN** the overview lists `Md Kw`

#### Scenario: Suite file
- **WHEN** `robotcode doc lib tests/login.robot` is run for a file with a test case section and the keyword `Suite Kw`
- **THEN** the output is the page with the title `Suite *Login*` and the keyword `Suite Kw`
- **AND** with `--format json` its `type` is `SUITE`

#### Scenario: Suite initialization file
- **WHEN** `robotcode doc lib 01__my_suite/__init__.robot` is run on any supported Robot Framework version, for an initialization file with a `Suite Setup` setting and the keyword `Init Kw`
- **THEN** the output is the page with the title `Suite *My Suite*` and the keyword `Init Kw`
- **AND** standard error reports no error for the `Suite Setup` setting

#### Scenario: Import arguments
- **WHEN** a library `ArgLib` offers the keyword `Mode B Keyword` only when it is initialised with `b`, and `robotcode doc keywords 'ArgLib::b'` is run
- **THEN** the overview lists `Mode B Keyword`

### Requirement: Markdown output

Without `--format` or with `--format text`, the subcommands `lib`, `keywords`, `keyword` and `source` SHALL write Markdown through RobotCode's terminal output. It is rendered on a colour terminal, and written as raw Markdown with `--no-color`, in a pipe and in an AI-agent session. It is paged according to `--pager/--no-pager`.

#### Scenario: Piped output
- **WHEN** `robotcode doc lib Collections` is run with standard output piped
- **THEN** the output is the raw Markdown of the page and nothing else

#### Scenario: Output file
- **WHEN** `robotcode doc lib -o collections.md Collections` is run
- **THEN** `collections.md` contains the page of `Collections` with `\n` line endings, and nothing is written to standard output

#### Scenario: Output file in a missing directory
- **WHEN** `robotcode doc lib -o out/sub/collections.md Collections` is run and `out` does not exist
- **THEN** `out/sub/collections.md` contains the page of `Collections`

## ADDED Requirements

### Requirement: Source of keywords

`robotcode doc source TARGET NAME …` SHALL show, for every keyword that one of the names selects, where it is defined and its code with line numbers, and SHALL NOT show its documentation apart from a docstring in its code. A name SHALL select keywords as in `robotcode doc keyword`, and a name that selects none SHALL be handled as there.

#### Scenario: Keyword of a Python library
- **WHEN** `robotcode doc source ShopLibrary Greeting` is run for a method with a decorator that starts on line 39 and whose `def` is on line 40
- **THEN** the output names `libraries/ShopLibrary.py:40`
- **AND** it shows the lines from the decorator to the end of the method, each with its line number

#### Scenario: Keyword of a resource file
- **WHEN** `robotcode doc source orders.resource "Create Order"` is run
- **THEN** the output names the file and the line of the keyword
- **AND** it shows the keyword's lines up to its last line that isn't blank, and not the next keyword

#### Scenario: Keyword of a suite file
- **WHEN** `robotcode doc source tests/login.robot "Suite Kw"` is run for a keyword in the keyword section of a suite file
- **THEN** the output names the file and the line and shows the keyword's lines

#### Scenario: Several keywords
- **WHEN** a name selects several keywords, or several names are given
- **THEN** the output shows each keyword with its place and its code, in the order of `robotcode doc keyword`

#### Scenario: A name without a match
- **WHEN** `robotcode doc source ShopLibrary Greeting Nope` is run
- **THEN** the output shows `Greeting`
- **AND** `Nope` is reported on standard error together with similar keyword names
- **AND** the exit code is not 0

### Requirement: Source of a library or a resource

`robotcode doc source TARGET` without a name SHALL show where the library, resource file or suite file is, and the whole file with line numbers.

#### Scenario: Resource file
- **WHEN** `robotcode doc source resources/orders.resource` is run
- **THEN** the output names `resources/orders.resource`
- **AND** it shows all lines of the file, each with its line number

#### Scenario: Library by name
- **WHEN** `robotcode doc source ShopLibrary` is run
- **THEN** the output names the file of the library and shows all its lines

#### Scenario: Keywords in other files
- **WHEN** a library's keywords are defined in other files than the library's class, and `robotcode doc source Lib` is run
- **THEN** the output shows the file of the library
- **AND** `robotcode doc source Lib Kw` shows the file in which `Kw` is defined

### Requirement: Code that cannot be shown

When a keyword or a target has no source file, its file can't be read, or its code can't be found in the file, the command SHALL report this on standard error together with the place, as far as it is known, and the exit code SHALL NOT be 0. What the other names select SHALL still be shown.

#### Scenario: Library without a source file
- **WHEN** `robotcode doc source Lib Kw` is run for a keyword that reports no source file
- **THEN** standard error names `Kw` and says that its code isn't available
- **AND** the exit code is not 0

#### Scenario: Another keyword can be shown
- **WHEN** one name selects a keyword without a source file, and another selects a keyword with one
- **THEN** the output shows the second keyword
- **AND** the exit code is not 0

### Requirement: Paths in the source output

In Markdown output, a path SHALL be relative to the project root with `/` as its separator when the file is in the project, and absolute otherwise. A line of a file SHALL be shown as the file has it, without its line ending.

#### Scenario: A file in the project
- **WHEN** `robotcode doc source orders.resource` is run from a subfolder of the project
- **THEN** the output names `resources/orders.resource`, relative to the project root

#### Scenario: An installed library
- **WHEN** `robotcode doc source BuiltIn Log` is run
- **THEN** the output names the absolute path of `BuiltIn.py`

### Requirement: JSON of the source

With the global `--format json` or `json-indent`, `robotcode doc source` SHALL print one object with `name`, `type`, `version`, `scope`, `source`, `lineno`, `code` and `keywords`. With a name, `keywords` SHALL hold the selected keywords and `code` SHALL be empty; without a name, `code` SHALL hold the file and `keywords` SHALL be empty. A keyword SHALL have `name`, `source`, `lineno`, `start_lineno`, `end_lineno` and `code`.

#### Scenario: A keyword as JSON
- **WHEN** `robotcode --format json doc source ShopLibrary Greeting` is run for a method with a decorator on line 39 and its `def` on line 40
- **THEN** the keyword has its absolute `source`, `lineno` 40 and `start_lineno` 39
- **AND** its `code` holds the lines from `start_lineno` to `end_lineno` without line numbers

#### Scenario: A file as JSON
- **WHEN** `robotcode --format json doc source resources/orders.resource` is run
- **THEN** `code` holds the content of the file without line numbers
- **AND** `keywords` is empty
