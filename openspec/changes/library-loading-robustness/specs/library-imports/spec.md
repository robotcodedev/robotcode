# Spec Delta

## Purpose

Defines how RobotCode loads library and variable file imports for the analysis: the time limit and what happens when it expires, how failed and timed-out loads are kept, which calls are made to a library whose load fails, how a load without the import's arguments is made visible, and which library imports that Robot Framework ignores are reported.

## ADDED Requirements

### Requirement: Loading stops when the load timeout expires

RobotCode SHALL load each library and variable file for the analysis in a separate process and SHALL end that process when the configured load timeout expires (`load-library-timeout` in `[tool.robotcode-analyze]`, `--load-library-timeout`, the VS Code setting `robotcode.analysis.robot.loadLibraryTimeout` or the environment variable `ROBOTCODE_LOAD_LIBRARY_TIMEOUT`; default 10 seconds). The load SHALL return a timeout error right after the timeout, without waiting for the library or variable file to finish, and no code of the library or variable file SHALL keep running in that process afterwards. The import SHALL report that loading timed out after the configured number of seconds (for a library that Robot Framework imports by default, such as `BuiltIn`, the analysed file reports it), in the language server and in `robotcode analyze code`. A load that finishes within the timeout SHALL behave as before.

#### Scenario: Library that blocks at import
- **WHEN** a suite imports a library whose module blocks for 60 seconds at import and `load-library-timeout` is 2
- **THEN** the import reports that loading the library timed out after 2 seconds
- **AND** the analysis of the suite finishes without waiting for the 60 seconds

#### Scenario: Library code does not continue
- **WHEN** a library that would write a file after blocking at import for 5 seconds is loaded with a timeout of 1 second
- **THEN** the file is not written, also not after the 5 seconds

#### Scenario: Variable file that blocks
- **WHEN** a suite has `Variables    slow_vars.py` whose module blocks for 60 seconds and `load-library-timeout` is 2
- **THEN** the import reports that loading timed out after 2 seconds, without waiting for the 60 seconds

#### Scenario: Default library that blocks
- **WHEN** loading `BuiltIn`, which every file imports by default, times out
- **THEN** the file reports "Can't import default library 'BuiltIn': …" with the timeout message, as before

#### Scenario: Library that loads in time
- **WHEN** a library loads within the timeout
- **THEN** its keywords and documentation are available as before

### Requirement: A timed-out load is kept until the library changes

A load that timed out SHALL be kept as the result of that import in the same way as the result of a load that failed with an error, which RobotCode keeps while an analysed file imports the library or variable file: other files and later analyses in the same session (a language server run, or one `robotcode analyze code` run) that import the same library or variable file with the same statically resolved arguments SHALL get that result without a new load. The library or variable file SHALL be loaded again when one of its files changes, and in a new session, for example after the language server restarts because the configuration changed or because of Clear Cache and Restart. A timed-out result SHALL NOT be written to the disk cache, and the analysis of files that depend on it SHALL NOT be written to the namespace cache.

#### Scenario: Two suites import the same blocking library
- **WHEN** two suites import the same library with the same arguments in one `robotcode analyze code` run and loading it times out
- **THEN** the library is loaded once
- **AND** both imports report the timeout

#### Scenario: The library file changes
- **WHEN** loading a library timed out in the language server and the library's source file is then saved
- **THEN** the library is loaded again for the next analysis

#### Scenario: A new session
- **WHEN** a library timed out in one `robotcode analyze code` run and loads within the timeout in the next run
- **THEN** the next run shows its keywords and no timeout

#### Scenario: Not in the namespace cache
- **WHEN** namespace caching is enabled and a suite has `Library    SlowLib.py    slow`, whose load times out, followed by `Library    SlowLib.py    fast    AS    Fast`, which loads
- **THEN** the analysis of the suite is not written to the namespace cache

### Requirement: A library that cannot report its keyword names is not asked for documentation

When RobotCode loads a library for the analysis, it SHALL request the library's keyword names before the library's introduction and importing documentation, the order Robot Framework's Libdoc uses. When getting the keyword names fails, RobotCode SHALL NOT make further requests to the library: the import SHALL report the failure, and the import's arguments SHALL remain available (for example in the hover of the import), with the introduction and importing documentation taken from the library's Python docstrings, which Robot Framework also uses when a dynamic library returns no documentation. For a `Remote` import with valid arguments whose server does not answer, RobotCode SHALL make no more connection attempts than Robot Framework makes when it imports the library. The documentation of libraries that report their keyword names SHALL be unchanged.

#### Scenario: Remote server that closes the connection
- **WHEN** a suite imports `Remote` with the URI of a local server that accepts connections and closes them at once
- **THEN** RobotCode connects to it as often as Robot Framework's import of `Remote` does (`get_library_information` and `get_keyword_names`), and no more
- **AND** the import reports "Getting keyword names from library 'Remote' failed: …"

#### Scenario: Import arguments stay available
- **WHEN** the hover of that `Remote` import is shown
- **THEN** it lists the arguments `uri` and `timeout`, with the docstring of `Remote.__init__`

#### Scenario: Dynamic library whose keyword names fail
- **WHEN** a dynamic library's `get_keyword_names` raises an exception
- **THEN** its `get_keyword_documentation` is never called
- **AND** the import reports the failure

#### Scenario: Working dynamic library
- **WHEN** a dynamic library returns its keyword names and documents `__intro__` and `__init__` through `get_keyword_documentation`
- **THEN** the library's introduction and importing documentation are the ones returned by `get_keyword_documentation`, as before

### Requirement: A load without the import's arguments is reported

When RobotCode loads a library with the arguments of its import and that load fails, because the arguments cannot be resolved or do not match the library's arguments or because initializing the library fails, RobotCode SHALL still load the library without arguments and use the keywords of that load, as before. For an import in the analysed file it SHALL report, in addition to the original error, an information diagnostic `LibraryLoadedWithoutArguments` on the import, saying that the keywords shown come from loading the library without arguments because loading it with the import's arguments failed. The diagnostic SHALL NOT be reported when the load without arguments fails too, when the import has no arguments, or when RobotCode does not load the library with the import's arguments at all, for example because `ignore-arguments-for-library` makes it load the library without arguments on purpose. It SHALL be suppressible with the diagnostics modifiers.

#### Scenario: Initializing the library fails
- **WHEN** a suite has `Library    StrictLib.py    bogus` and `StrictLib.__init__` raises `ValueError` for `bogus`
- **THEN** the import reports the initialization error as before
- **AND** it reports the information diagnostic `LibraryLoadedWithoutArguments`
- **AND** the keywords of `StrictLib` are found in the suite

#### Scenario: Too many arguments
- **WHEN** a suite has `Library    StrictLib.py    a    b    c` and `StrictLib` accepts at most one argument
- **THEN** the import reports Robot Framework's argument error and the information diagnostic `LibraryLoadedWithoutArguments`

#### Scenario: Variable that cannot be resolved
- **WHEN** a suite has `Library    StrictLib.py    ${NOT_KNOWN}` and `${NOT_KNOWN}` is not defined anywhere RobotCode can see
- **THEN** the import reports that the variable was not found and the information diagnostic `LibraryLoadedWithoutArguments`

#### Scenario: The load without arguments fails too
- **WHEN** a library requires an argument and its import's argument cannot be used
- **THEN** only the original error is reported, without `LibraryLoadedWithoutArguments`

#### Scenario: Arguments ignored on purpose
- **WHEN** a library matches `ignore-arguments-for-library` and its import has arguments
- **THEN** no `LibraryLoadedWithoutArguments` diagnostic is reported

### Requirement: Library imports that Robot Framework ignores are reported

On Robot Framework 7.4 and newer, RobotCode SHALL report a warning `LibraryImportIgnored` on a library import of the analysed file that Robot Framework ignores because the name under which it would be imported (its alias, otherwise the library name) is already taken by an earlier import of that file, directly or through an imported resource file, or by a library that Robot Framework imports by default (such as `BuiltIn`):
- by the same library with different arguments: "Library '<name>' has already been imported with different arguments. This import is ignored.";
- by a library with another name: "Another library with name '<name>' has already been imported. This import is ignored."

The earlier import SHALL be given as related information. Arguments SHALL be compared after static resolution, with the variables RobotCode knows at the position of each import (built-in variables, variables and variable files given in the configuration or on the command line, variables of the file and of imported resources and variable files, and environment variables of the analysing process). Built-in variables that Robot Framework only sets during the run (`${OUTPUT DIR}`, `${SUITE NAME}`, `${TEST NAME}`, `${LOG FILE}`, `${OPTIONS}` and the other built-ins that describe the running test, suite or keyword, the log level or the output files) SHALL have no value in this resolution; built-in variables with a fixed value, such as `${TEMPDIR}`, `${/}` and `${EMPTY}`, SHALL keep it. When an argument of either import still contains a variable after resolution, an unknown one or a built-in without a value, directly or through another variable, no warning SHALL be reported. No warning SHALL be reported when loading either library reported errors, for ignored imports inside imported resource files, for imports of the same library with the same arguments (Robot Framework logs them at INFO level), and on Robot Framework 7.3 and older, which log all these cases at INFO level only. The warning SHALL be suppressible with the diagnostics modifiers.

#### Scenario: Same library with different arguments
- **WHEN** a suite has `Library    ArgLib.py    a` followed by `Library    ArgLib.py    b`, on RF 7.5
- **THEN** the second import gets the warning "Library 'ArgLib' has already been imported with different arguments. This import is ignored."
- **AND** its related information points to the first import

#### Scenario: Named instead of positional argument
- **WHEN** a suite has `Library    ArgLib.py    a` followed by `Library    ArgLib.py    x=a`, on RF 7.5
- **THEN** the second import gets the warning, as Robot Framework warns about it

#### Scenario: Another library under a taken name
- **WHEN** a suite has `Library    ArgLib.py` followed by `Library    OtherLib.py    AS    ArgLib`, on RF 7.5
- **THEN** the second import gets the warning "Another library with name 'ArgLib' has already been imported. This import is ignored."

#### Scenario: Taken alias
- **WHEN** a suite has `Library    ArgLib.py    AS    Two` followed by `Library    ArgLib.py    c    AS    Two`, on RF 7.5
- **THEN** the second import gets the warning "Library 'Two' has already been imported with different arguments. This import is ignored."

#### Scenario: Arguments that resolve to the same value
- **WHEN** a suite defines `${VAL}    a` in its `*** Variables ***` section and has `Library    ArgLib.py    a` followed by `Library    ArgLib.py    ${VAL}`, on RF 7.5
- **THEN** no warning is reported

#### Scenario: Value only known at runtime
- **WHEN** a suite has `Library    ArgLib.py    a` followed by `Library    ArgLib.py    ${FROM_RUNTIME}` and `${FROM_RUNTIME}` is not known to RobotCode, on RF 7.5
- **THEN** no `LibraryImportIgnored` warning is reported

#### Scenario: Built-in variable that only has a value during the run
- **WHEN** a suite has `Library    ArgLib.py    a` followed by `Library    ArgLib.py    ${OUTPUT DIR}`, on RF 7.5
- **THEN** no `LibraryImportIgnored` warning is reported, although Robot Framework warns at run time

#### Scenario: Built-in variable without a value, reached through a variable
- **WHEN** a suite defines `${LOG}    ${OUTPUT DIR}/x` in its `*** Variables ***` section and has `Library    ArgLib.py    a` followed by `Library    ArgLib.py    ${LOG}`, on RF 7.5
- **THEN** no `LibraryImportIgnored` warning is reported

#### Scenario: Built-in variable with a fixed value
- **WHEN** a suite has `Library    ArgLib.py    a` followed by `Library    ArgLib.py    ${EMPTY}`, on RF 7.5
- **THEN** the second import gets the warning "Library 'ArgLib' has already been imported with different arguments. This import is ignored."

#### Scenario: Earlier import in a resource file
- **WHEN** a suite imports `common.resource`, which has `Library    ArgLib.py    a`, and the suite then has `Library    ArgLib.py    b`, on RF 7.5
- **THEN** the suite's library import gets the warning, with related information pointing to the import in `common.resource`

#### Scenario: Ignored import inside a resource file
- **WHEN** a suite has `Library    ArgLib.py    a` followed by a resource import whose file has `Library    ArgLib.py    b`, on RF 7.5
- **THEN** no `LibraryImportIgnored` warning is reported in the suite

#### Scenario: Library that fails to load
- **WHEN** a suite has `Library    StrictLib.py    fast` followed by `Library    StrictLib.py    bogus` and initializing with `bogus` fails, on RF 7.5
- **THEN** the second import reports its errors and no `LibraryImportIgnored` warning

#### Scenario: Older Robot Framework
- **WHEN** a suite has `Library    ArgLib.py    a` followed by `Library    ArgLib.py    b`, on RF 7.3
- **THEN** no `LibraryImportIgnored` warning is reported

#### Scenario: Suppressed
- **WHEN** the second import carries `# robotcode: ignore[LibraryImportIgnored]`
- **THEN** no warning is reported for it
