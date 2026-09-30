# Spec Delta

## Purpose

Defines how RobotCode loads library and variable file imports for the analysis: the time limit and what happens when it expires, how a timed-out load is kept, how an import that ends early is reported, how loaded documentation is cached per set of import arguments, and how a load without the import's arguments is made visible.

## ADDED Requirements

### Requirement: Loading stops when the load timeout expires

RobotCode SHALL end the process that loads a library or variable file for the analysis when the configured load timeout expires (`load-library-timeout`, default 10 seconds). The load SHALL return a timeout error right after the timeout, without waiting for the library or variable file to finish, and no code of the library or variable file SHALL keep running in that process afterwards. The import SHALL report that loading timed out after the configured number of seconds, with the code `LibraryTimeoutError` for a library and `VariablesTimeoutError` for a variable file (for a library that Robot Framework imports by default, such as `BuiltIn`, the analysed file reports it), in the language server and in `robotcode analyze code`. A load that finishes within the timeout SHALL behave as before.

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

### Requirement: A library that exits at import is reported on the import

When a library or variable file ends the process that loads it, for example with `sys.exit()` at import, RobotCode SHALL report on the import that loading failed because the import ended with that exit code before it finished, without mentioning the process that RobotCode loads it in, with the code `LibraryExitError` for a library and `VariablesExitError` for a variable file, and SHALL continue the analysis. The result SHALL be kept like a timed-out load. The analysing process SHALL NOT end.

#### Scenario: Library calls sys.exit at import
- **WHEN** a suite imports a library whose module calls `sys.exit(0)` at import and calls `Not Existing Keyword`
- **THEN** the import reports `LibraryExitError`: loading the library failed because the import ended with exit code 0 before it finished
- **AND** `robotcode analyze code` also reports `KeywordNotFound` for `Not Existing Keyword`

### Requirement: A timed-out load is kept until the library changes

A load that timed out SHALL be kept as the result of that import in the same way as the result of a load that failed with an error, which RobotCode keeps while an analysed file imports the library or variable file: other files and later analyses in the same session (a language server run, or one `robotcode analyze code` run) that import the same library or variable file with arguments that resolve to the same values SHALL get that result without a new load. A library SHALL be loaded again when a file in the directory of its source changes (for a package: in its package directory; for a library RobotCode cannot find without loading it: on the Python path), a variable file when the file itself changes (only when RobotCode knows its path without loading it), and both in a new session, for example after the language server restarts because the configuration changed or because of Clear Cache and Restart. A timed-out result SHALL NOT be written to the disk cache, and the analysis of files that depend on it SHALL NOT be written to the namespace cache.

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

### Requirement: Each set of import arguments has its own stored documentation

RobotCode SHALL keep the documentation of a library or variable file in its disk cache per set of import arguments, resolved with the variables RobotCode knows for the import. An import whose arguments differ from those of a stored entry SHALL be loaded with its own arguments, and its errors SHALL be reported, also when documentation of the same library or variable file with other arguments is stored and also after a restart, without clearing the cache. Each argument set that loads without errors SHALL be served from the disk cache in later sessions. A library that matches `ignore-arguments-for-library` is loaded without arguments and SHALL have one stored entry.

#### Scenario: Argument added to a library without arguments
- **WHEN** `Library    NoArgumentLib.py` was analysed and stored in the disk cache and the import is changed to `Library    NoArgumentLib.py    extra`
- **THEN** the import reports Robot Framework's error that the library expects no arguments, without clearing the cache

#### Scenario: Mistyped Remote URL
- **WHEN** `Library    Remote    http://127.0.0.1:8270` loaded and was stored, and the URL is changed to one that refuses the connection
- **THEN** the import reports the connection error, and the keywords loaded from the first URL are not used for it

#### Scenario: Argument sets stay cached
- **WHEN** one suite imports `ModeLib` with `a` and another with `b`, and the keywords of `ModeLib` depend on that argument
- **THEN** each import gets the keywords of its own argument, also in the next session, where both come from the disk cache without a new load

#### Scenario: Arguments ignored on purpose keep one entry
- **WHEN** a library matches `ignore-arguments-for-library` and is imported with arguments
- **THEN** it is loaded without arguments and stored under one entry without the arguments
