# Spec: documentation-cli

## Purpose

Defines the `robotcode doc` command group, which shows the documentation of one library, resource file or suite file in the terminal, in files and as JSON. It covers the subcommands and their targets, the resolution with the project's configuration, live generation, the behaviour on failing loads, the output formats, keyword overview and lookup, and the terminal browser.

## Requirements

### Requirement: Subcommands and targets

`robotcode doc` SHALL provide the subcommands `lib`, `keywords`, `keyword` and `browse`. Each SHALL document exactly one TARGET. A TARGET SHALL be one of:

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

### Requirement: Targets resolve with the project configuration

Each call SHALL load its target anew. It SHALL apply the environment variables, python path, languages, variables and variable files of the `robot.toml` configuration and the selected profiles, together with the command's options `-v/--variable`, `-V/--variablefile`, `-P/--pythonpath` and `--language`. Variables in the TARGET name and in its import arguments SHALL be resolved with these variables.

#### Scenario: Python path from the configuration
- **WHEN** `robot.toml` sets `python-path = ["lib"]`, `lib/MyLib.py` defines the library `MyLib`, and `robotcode doc keywords MyLib` is run in the subdirectory `tests/` of the project
- **THEN** the keywords of `MyLib` are listed

#### Scenario: Variable from a profile
- **WHEN** the profile `dev` defines the variable `MODE = "b"` and `robotcode -p dev doc keywords 'ArgLib::${MODE}'` is run
- **THEN** the overview lists `Mode B Keyword`

#### Scenario: Variable on the command line
- **WHEN** `robotcode doc keywords -v MODE:b 'ArgLib::${MODE}'` is run in a project that defines no `MODE`
- **THEN** the overview lists `Mode B Keyword`

#### Scenario: Translated resource file
- **WHEN** `robot.toml` sets `languages = ["de"]` and `robotcode doc keywords deutsch.resource` is run on RF 6.0 or newer, for a resource file with the headers `*** Einstellungen ***` and `*** Schlüsselwörter ***` and no `Language:` line
- **THEN** the overview lists the keywords of the file

#### Scenario: Language on the command line
- **WHEN** `robotcode doc keywords --language de deutsch.resource` is run on RF 6.0 or newer, in a project without `languages`, for the file of the scenario "Translated resource file"
- **THEN** the overview lists the keywords of the file
- **AND** in a project whose `robot.toml` sets `languages = ["de"]`, `robotcode doc keywords --language fi deutsch.resource` lists them as well

#### Scenario: Relative path from a subdirectory
- **WHEN** `robotcode doc lib ../resources/common.resource` is run in the subdirectory `tests/` of the project
- **THEN** the page of `common` is shown

#### Scenario: No output directories
- **WHEN** `robot.toml` sets `output-dir = "results"` and `robotcode doc keywords Collections` is run
- **THEN** no directory `results` is created

#### Scenario: Variable file that prints
- **WHEN** a variable file prints a line and `robotcode --format json doc keywords -V noisy_vars.py Collections` is run
- **THEN** standard output holds only the JSON object, and the printed line is on standard error

#### Scenario: Options from a subdirectory
- **WHEN** `robotcode doc keywords -P sublib SubLib` is run in the subdirectory `tests/`, which contains `sublib/SubLib.py`
- **THEN** the keywords of `SubLib` are listed

#### Scenario: Library changed between two calls
- **WHEN** a keyword is added to `lib/MyLib.py` after a first `robotcode doc keywords MyLib`
- **THEN** the next `robotcode doc keywords MyLib` lists the new keyword

### Requirement: Failing loads abort

When the target cannot be found, imported or initialised, can only be loaded without the given import arguments, or is a library whose keywords cannot be read, the command SHALL write no documentation. It SHALL report the error on standard error and exit with a non-zero code. For a file that can be read neither as a resource file nor as a suite file, the error SHALL be Robot Framework's error for it as a resource file, as in Libdoc.

#### Scenario: Unknown library
- **WHEN** `robotcode doc lib NoSuchLib` is run
- **THEN** standard output is empty, standard error reports the import error and the exit code is not 0

#### Scenario: Import arguments that fail
- **WHEN** a library `StrictLib` raises for an unknown mode in its initializer and `robotcode doc lib 'StrictLib::bogus'` is run
- **THEN** no documentation is written, standard error reports that initialising `StrictLib` with `bogus` failed, and the exit code is not 0
- **AND** this holds although the library can be loaded without arguments

#### Scenario: Keywords that cannot be read
- **WHEN** `robotcode doc keywords ContextLib` is run for a library that reads a variable of the running test in `get_keyword_names`
- **THEN** standard output is empty, standard error reports that getting the keyword names failed, and the exit code is not 0

#### Scenario: Import arguments for a resource file
- **WHEN** `robotcode doc keywords 'resources/common.resource::bogus'` is run
- **THEN** standard output is empty, standard error reports that resource and suite files take no import arguments, and the exit code is not 0

#### Scenario: Missing resource file
- **WHEN** `robotcode doc lib missing.resource` is run and no such file exists
- **THEN** standard output is empty, standard error reports the missing file and the exit code is not 0

#### Scenario: Resource file with unrecognised section headers
- **WHEN** `robotcode doc lib deutsch.resource` is run on RF 6.1 or newer for the file of the scenario "Translated resource file", in a project without `languages`
- **THEN** standard output is empty and the exit code is not 0
- **AND** standard error reports Robot Framework's error for the file as a resource file, `Unrecognized section header '*** Einstellungen ***'`, not the error of the suite builder

#### Scenario: Error reported by Robot Framework
- **WHEN** `robotcode doc keywords dup.resource` is run on RF 7.0 or newer for a resource file that defines the keyword `Dup Kw` twice
- **THEN** standard error reports the error for `Dup Kw` once, and the exit code is 0

#### Scenario: One keyword cannot be created
- **WHEN** a dynamic library returns the names `Good Keyword` and `Bad Keyword` and raises when asked for the arguments of `Bad Keyword`, and `robotcode doc keywords` is run for it
- **THEN** `Good Keyword` is listed, standard error reports the error of `Bad Keyword`, and the exit code is 0

### Requirement: Markdown output

Without `--format` or with `--format text`, the subcommands `lib`, `keywords` and `keyword` SHALL write Markdown through RobotCode's terminal output. It is rendered on a colour terminal, and written as raw Markdown with `--no-color`, in a pipe and in an AI-agent session. It is paged according to `--pager/--no-pager`.

#### Scenario: Piped output
- **WHEN** `robotcode doc lib Collections` is run with standard output piped
- **THEN** the output is the raw Markdown of the page and nothing else

#### Scenario: Output file
- **WHEN** `robotcode doc lib -o collections.md Collections` is run
- **THEN** `collections.md` contains the page of `Collections` with `\n` line endings, and nothing is written to standard output

#### Scenario: Output file in a missing directory
- **WHEN** `robotcode doc lib -o out/sub/collections.md Collections` is run and `out` does not exist
- **THEN** `out/sub/collections.md` contains the page of `Collections`

### Requirement: JSON output

With the global `--format json` or `json-indent`, `robotcode doc lib TARGET` SHALL print one object with these fields:

- `name`;
- `type`: `LIBRARY`, `RESOURCE` or `SUITE`;
- `version`, `scope`, `source` and `lineno`;
- `markdown`: the page, as the Markdown output without colour shows it;
- `keywords`: one entry per keyword, in the order of the page and without private keywords;
- `types`: one entry per data type, in the order of the page.

Every field SHALL be present in every object.

#### Scenario: Library as JSON
- **WHEN** `robotcode --format json doc lib Collections` is run on RF 7.5
- **THEN** the object has the `name` `Collections`, the `type` `LIBRARY` and the `scope` `GLOBAL`
- **AND** its `markdown` is the Markdown that `robotcode --no-color doc lib Collections` prints
- **AND** its first keyword entry is `Append To List` with the `anchor` `append-to-list`, and the anchor of every keyword and type entry is the anchor of a heading in `markdown`

#### Scenario: Selected keyword as JSON
- **WHEN** `robotcode --format json doc keyword Collections "Get Match Count"` is run
- **THEN** the object has no `markdown` and its `keywords` holds exactly the entry of `Get Match Count`

### Requirement: Keyword overview

`robotcode doc keywords TARGET` SHALL list every keyword of the page, in the order of the page, each with its name, its arguments and the first paragraph of its documentation. With PATTERN arguments, only keywords whose name contains one of the patterns SHALL be listed. `*` and `?` SHALL work as wildcards; case and spaces SHALL be ignored as in Libdoc's `list`, and underscores SHALL be ignored as well. When no keyword is selected, the output SHALL say so and the exit code SHALL be 0.

#### Scenario: Substring
- **WHEN** `robotcode doc keywords Collections dictionary` is run
- **THEN** every listed keyword has `dictionary` in its name, case-insensitively, and every such keyword of `Collections` is listed

#### Scenario: Underscores ignored
- **WHEN** `robotcode doc keywords Collections get_from_list` is run
- **THEN** `Get From List` is listed

#### Scenario: Tag
- **WHEN** a resource keyword is tagged `smoke test` and `robotcode doc keywords common.resource --tag smoke_test` is run
- **THEN** that keyword is listed and no keyword without a matching tag

#### Scenario: Nothing selected
- **WHEN** `robotcode doc keywords Collections nosuchname` is run
- **THEN** the output says that no keyword matches and the exit code is 0

### Requirement: Keyword documentation

`robotcode doc keyword TARGET NAME …` SHALL show the full documentation of every keyword that one of the names selects. A name SHALL select the keywords whose name matches it exactly or as a pattern with `*` and `?`; case and spaces SHALL be ignored as in Libdoc's `show`, and underscores SHALL be ignored as well. A name SHALL also select every keyword with embedded arguments whose name pattern matches it.

#### Scenario: Exact name
- **WHEN** `robotcode doc keyword Collections get_match_count` is run
- **THEN** the output is the documentation of `Get Match Count` and of no other keyword

#### Scenario: Pattern
- **WHEN** `robotcode doc keyword BuiltIn "Should Be*"` is run
- **THEN** the output documents every keyword of `BuiltIn` whose name starts with `Should Be` and no other keyword

#### Scenario: Embedded arguments
- **WHEN** a resource defines `Open ${browser} Browser` and `robotcode doc keyword common.resource "Open Chrome Browser"` is run
- **THEN** the output documents `Open ${browser} Browser`

#### Scenario: Data types of the arguments
- **WHEN** a library has the keyword `paint(self, shade: Color)` with an `Enum` `Color` and `robotcode doc keyword` is run for `Paint` on RF 6.1 or newer
- **THEN** the output documents `Paint`, followed by `Color` with its members

#### Scenario: Name without a match
- **WHEN** `robotcode doc keyword Collections "Get Match Cont"` is run
- **THEN** standard error reports that no keyword matches `Get Match Cont` and names `Get Match Count`, and the exit code is not 0

### Requirement: Terminal browser

When standard input and standard output are terminals and the session is not an AI-agent session, `robotcode doc browse TARGET` SHALL open the page of `doc lib` in RobotCode's documentation viewer, the viewer of the REPL's `.doc`. There, the links of the keyword index and of the table of contents SHALL jump to their headings, and search and back/forward navigation SHALL work. Otherwise it SHALL print what `robotcode doc lib TARGET` prints.

#### Scenario: Interactive terminal
- **WHEN** `robotcode doc browse Collections` is run in an interactive terminal outside an AI-agent session
- **THEN** the viewer opens with the page of `Collections`
- **AND** following the index link `Get Match Count` shows that keyword's heading, and going back returns to the previous position

#### Scenario: AI-agent session
- **WHEN** `robotcode doc browse Collections` is run in an interactive terminal of an AI-agent session
- **THEN** no viewer opens and the raw Markdown of the page is written

#### Scenario: Pipe
- **WHEN** `robotcode doc browse Collections` is run with standard output piped
- **THEN** no viewer opens and the output is the raw Markdown of the page

### Requirement: Suite file as target

A TARGET SHALL also be the path of a suite file, a file with a test case or task section: the keywords of its keyword section are documented under the suite's name with the type `SUITE`, as Libdoc has documented suite files since RF 6.0.

#### Scenario: Suite file with a task section
- **WHEN** `robotcode doc keywords tasks/cleanup.robot` is run for a file with a task section and the keyword `Clean Up`
- **THEN** the overview lists `Clean Up`

### Requirement: Suite initialization file as target

A TARGET SHALL also be the path of a suite initialization file, a file named `__init__`, case ignored, with a suite file extension, such as `__init__.robot`: the keywords of its keyword section are documented under the name Robot Framework gives the suite of its directory, with the type `SUITE`, on every supported Robot Framework version, as Libdoc has documented `__init__.robot` since RF 6.0.

#### Scenario: Initialization file as JSON
- **WHEN** `robotcode --format json doc lib 01__my_suite/__init__.robot` is run for an initialization file with the keyword `Init Kw`
- **THEN** the object has the `type` `SUITE` and lists `Init Kw`

### Requirement: Import arguments of a target

Import arguments, when given, SHALL follow Libdoc's form `Name::arg1::arg2`; resource and suite files take none, and import arguments given to them SHALL be an error. An empty name SHALL be a usage error.

#### Scenario: Empty name
- **WHEN** `robotcode doc lib ''` is run
- **THEN** the command fails with a usage error

### Requirement: How a target is read

Whether the TARGET is a file or a library SHALL be decided after the variables in its name are resolved. A backslash in the TARGET, in its name or in its import arguments, SHALL be part of the text, not an escape character. A library name that exists as a path SHALL be made absolute before it is imported, as Libdoc does, so a directory is imported as a library in the same way as by Libdoc.

#### Scenario: Path built from a variable
- **WHEN** `robotcode doc keywords -v DIR:resources '${DIR}/common.resource'` is run
- **THEN** the overview lists the keywords of the resource file `common`

### Requirement: Languages of the documented files

The languages of the repeatable `--language` SHALL be added to those of the configuration. On Robot Framework 6.0 and newer, resource and suite files SHALL be read in these languages, as `robot` reads them. Robot Framework 5.0 has no language support: there, a language from the configuration or from `--language` SHALL be rejected with Robot Framework's error for the option, no documentation SHALL be written, and the exit code SHALL NOT be 0.

#### Scenario: Language on Robot Framework 5.0
- **WHEN** `robotcode doc keywords --language de deutsch.resource` is run on RF 5.0
- **THEN** Robot Framework's error for the option is reported, no documentation is written, and the exit code is not 0

### Requirement: Paths relative to the start directory

`--base-dir` SHALL set the directory for `${CURDIR}` and for relative paths in TARGET; its default is the directory the command was started in. Paths given to `-o`, `-V` and `-P` SHALL be relative to the directory the command was started in.

#### Scenario: Base directory
- **WHEN** `robotcode doc lib --base-dir resources common.resource` is run in the project root
- **THEN** the page of `common` is shown

### Requirement: No side effects of the configuration

Neither the analysis settings of `[tool.robotcode-analyze]` nor any cache SHALL be involved. The command SHALL NOT create the output, log, report or debug files of the configuration or their directories. What variable files print SHALL go to standard error.

#### Scenario: Log file of the configuration
- **WHEN** `robot.toml` sets `log = "results/log.html"` and `robotcode doc lib Collections` is run
- **THEN** neither `results/log.html` nor the directory `results` is created

### Requirement: Load errors that do not abort

Other load errors, such as a keyword that cannot be created, SHALL be reported on standard error while everything else is documented, and the exit code SHALL then be 0. So SHALL the errors and warnings Robot Framework reports while it loads the target, each once and in the format of the command's own messages.

#### Scenario: Warning while loading
- **WHEN** Robot Framework warns about a resource file while `robotcode doc keywords` loads it
- **THEN** the warning appears once on standard error, the overview lists the keywords, and the exit code is 0

### Requirement: Markdown output to a file

With `-o/--output FILE`, the Markdown SHALL be written to FILE instead, as UTF-8 with `\n` line endings on every platform, and a missing directory of FILE SHALL be created. `-o` together with any `--format` other than `text` SHALL be a usage error.

#### Scenario: Output file with the JSON format
- **WHEN** `robotcode --format json doc lib -o collections.md Collections` is run
- **THEN** the command fails with a usage error

### Requirement: Keyword and type entries in JSON

Each keyword entry SHALL have `name`, `anchor` (the anchor of its heading in `markdown`), `args` (its arguments as one line of text), `short_doc` (the first paragraph of its documentation), `tags` and `doc` (its documentation as Markdown). Each type entry SHALL have `name` and `anchor`, the anchor of its heading in `markdown`, to which the links to the type in `markdown` point.

#### Scenario: Fields of a keyword entry
- **WHEN** `robotcode --format json doc lib Collections` is run
- **THEN** every keyword entry has `name`, `anchor`, `args`, `short_doc`, `tags` and `doc`

### Requirement: JSON of selected keywords

`keywords` and `keyword` SHALL print an object with the same fields except `markdown` and `types`, whose `keywords` holds only the keywords they select.

#### Scenario: Keyword overview as JSON
- **WHEN** `robotcode --format json doc keywords Collections dictionary` is run
- **THEN** the object has no `markdown` and no `types`, and its `keywords` holds only keywords with `dictionary` in their name

### Requirement: Keyword overview filtered by tag

With `--tag TAG`, which can be repeated, only keywords with a tag that matches one of the given tags as a whole SHALL be listed, with `*` and `?` as wildcards and ignoring case, spaces and underscores.

#### Scenario: Tag pattern
- **WHEN** two resource keywords are tagged `smoke login` and `smoke logout`, and `robotcode doc keywords common.resource --tag 'SMOKE*'` is run
- **THEN** both keywords are listed

### Requirement: Data types of the documented keywords

After the keywords, `robotcode doc keyword` SHALL document the data types that their arguments use.

#### Scenario: Data type used by two keywords
- **WHEN** two keywords of a library take an argument of the `Enum` `Color` and `robotcode doc keyword` selects both on RF 6.1 or newer
- **THEN** the output documents both keywords, followed by `Color`

### Requirement: Names without a matching keyword

A name that selects no keyword SHALL be reported on standard error together with similar keyword names, and the exit code SHALL NOT be 0. The keywords that the other names select SHALL still be shown.

#### Scenario: One of two names without a match
- **WHEN** `robotcode doc keyword Collections "Get Match Count" "Get Match Cont"` is run
- **THEN** the output documents `Get Match Count`, standard error reports that no keyword matches `Get Match Cont`, and the exit code is not 0
