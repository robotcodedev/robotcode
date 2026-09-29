# Spec Delta

## Purpose

Defines how RobotCode loads library and variable file imports for the analysis: the time limit and what happens when it expires, how a timed-out load is kept, and how a load without the import's arguments is made visible.

## ADDED Requirements

### Requirement: Loading stops when the load timeout expires

RobotCode SHALL end the process that loads a library or variable file for the analysis when the configured load timeout expires (`load-library-timeout`, default 10 seconds). The load SHALL return a timeout error right after the timeout, without waiting for the library or variable file to finish, and no code of the library or variable file SHALL keep running in that process afterwards. The import SHALL report that loading timed out after the configured number of seconds (for a library that Robot Framework imports by default, such as `BuiltIn`, the analysed file reports it), in the language server and in `robotcode analyze code`. A load that finishes within the timeout SHALL behave as before.

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

A load that timed out SHALL be kept as the result of that import in the same way as the result of a load that failed with an error, which RobotCode keeps while an analysed file imports the library or variable file: other files and later analyses in the same session (a language server run, or one `robotcode analyze code` run) that import the same library or variable file with arguments that resolve to the same values SHALL get that result without a new load. The library or variable file SHALL be loaded again when one of its files changes (a variable file only when RobotCode knows its path without loading it), and in a new session, for example after the language server restarts because the configuration changed or because of Clear Cache and Restart. A timed-out result SHALL NOT be written to the disk cache, and the analysis of files that depend on it SHALL NOT be written to the namespace cache.

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

### Requirement: A load without the import's arguments is reported

When RobotCode loads a library with the arguments of its import and that load fails, because the arguments cannot be resolved or do not match the library's arguments or because initializing the library fails, RobotCode SHALL still load the library without arguments and use the keywords of that load, as before. For an import in the analysed file it SHALL report, in addition to the original error, an information diagnostic `LibraryLoadedWithoutArguments` on the import, saying that the keywords shown come from loading the library without arguments because loading it with the import's arguments failed. The diagnostic SHALL NOT be reported when the load without arguments fails too, when the import has no arguments, or when RobotCode does not load the library with the import's arguments at all, for example because `ignore-arguments-for-library` makes it load the library without arguments on purpose.

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
