# Spec Delta

## Purpose

Defines how a library declares that its keyword set depends on its import arguments or on external state, how RobotCode reads that declaration without instantiating the library, and how RobotCode caches such libraries, including the default entry and the fallback for import arguments whose values are only known at run time. Failed loads remain governed by `library-imports`.

## ADDED Requirements

### Requirement: Libraries declare their keyword set with a class or module attribute

A library SHALL be able to declare how its keyword set behaves through an attribute of its class or module, called the keyword-set attribute here (its name is settled before implementation, see the design). Two values SHALL be recognised: `args` (the keywords depend on the import arguments) and `volatile` (the keywords depend on external state such as a server, a process or the environment). Values SHALL be matched the way Robot Framework matches `ROBOT_LIBRARY_SCOPE` values, ignoring case, spaces and underscores. RobotCode SHALL read the attribute from the imported class or module before the library is instantiated, so reading it never runs the library's initializer. A subclass SHALL inherit the declaration of its base class. A value set only on the instance SHALL NOT count. A missing attribute or any other value SHALL count as no declaration, and no diagnostic SHALL be reported for it. The declaration SHALL also be known when the library cannot be instantiated with the import's arguments. RobotCode SHALL NOT assume a declaration for a library that does not carry the attribute, including Robot Framework's own `Remote` library; a subclass of `Remote` that sets the attribute SHALL count as declared like any other library. This SHALL behave the same on every supported Robot Framework version.

#### Scenario: Class declares args
- **WHEN** a library class sets the keyword-set attribute to `args`
- **THEN** RobotCode caches the library per set of import arguments (see "Libraries declared `args` are cached per set of statically resolved arguments")

#### Scenario: Module declares volatile
- **WHEN** a module library sets the keyword-set attribute to `volatile`
- **THEN** its documentation is never written to the disk cache

#### Scenario: Wrapper subclass
- **WHEN** a project file defines `class ServiceA(ArgLib): pass` and `ArgLib` declares `args`
- **THEN** `ServiceA` is cached per set of import arguments like `ArgLib`

#### Scenario: Subclass of Robot Framework's Remote library
- **WHEN** a project file defines `class XYService(Remote)` that sets the keyword-set attribute to `args`, and two suites import it with the URIs of two servers that provide different keywords
- **THEN** each suite gets the keywords of its own server, also when served from the disk cache in a later session

#### Scenario: Value set on the instance only
- **WHEN** a library class sets the keyword-set attribute to `args` only inside `__init__`, on the instance
- **THEN** the library counts as undeclared

#### Scenario: Spelling of the value
- **WHEN** the attribute is `"ARGS"` or `"Args"`
- **THEN** the library counts as declared `args`

#### Scenario: Unknown value
- **WHEN** the attribute is `"arguments"`
- **THEN** the library counts as undeclared and no diagnostic is reported

#### Scenario: Initializer fails
- **WHEN** a library class declares `args` and its `__init__` raises an exception for the import's arguments
- **THEN** the library still counts as declared `args`

### Requirement: Undeclared libraries keep one cache entry

A library without a declaration SHALL keep one disk cache entry per library, whatever its import arguments. The first result stored without load errors SHALL be served for every set of import arguments, in the same session and in later sessions, until the library's files change. A stored result with load errors SHALL NOT be served.

#### Scenario: Two argument sets of an undeclared library
- **WHEN** an undeclared dynamic library `ArgLib(mode)` returns `Kw A One` for `a` and `Kw B One` for `b`, a suite importing `ArgLib    a` is analysed first, and afterwards a suite importing `ArgLib    b`
- **THEN** the second suite is served the keywords of `a`, as before this change

#### Scenario: Remote imported directly
- **WHEN** a suite imports `Remote` with the URI of one server, and afterwards a suite imports `Remote` with the URI of another server that provides different keywords
- **THEN** `Remote` counts as undeclared, and the second suite is served the keywords of the first server, as before this change

### Requirement: Libraries declared `args` are cached per set of statically resolved arguments

For a library declared `args`, RobotCode SHALL keep one disk cache entry per set of statically resolved import arguments and SHALL serve each entry only for that set, in the same session and in later sessions, until the library's files change. The statically resolved arguments are the arguments as written, with every variable replaced whose value RobotCode knows statically: built-in variables such as `${CURDIR}`, robot.toml, profile and command-line variables, the Variables section and variable files, and environment variables. Built-in variables that only have a value at run time, such as `${OUTPUT DIR}`, `${SUITE NAME}`, `${TEST NAME}` or `${OPTIONS}`, SHALL remain known, so they are never reported as not found, but SHALL have no value in the statically resolved arguments: an argument that contains one, directly or through a variable whose value refers to one, still contains a variable after static resolution. The other built-in variables, such as `${CURDIR}`, `${EXECDIR}`, `${TEMPDIR}`, `${/}` and `${EMPTY}`, SHALL keep their values. Arguments written differently that resolve to the same values SHALL share an entry, for example `${MODE}` with the value `b` and `b`. The positional and the named form of an argument, such as `b` and `mode=b`, are different values and get separate entries. A stored result with load errors SHALL NOT be served.

#### Scenario: Two argument sets in one project
- **WHEN** `ArgLib(mode)` declares `args`, one suite imports `ArgLib    a` and calls `Kw A One`, and another suite imports `ArgLib    b` and calls `Kw B One`
- **THEN** neither suite reports `KeywordNotFound`

#### Scenario: Later session
- **WHEN** the same project is analysed again in a new session and the library's files are unchanged
- **THEN** both argument sets are served from the disk cache and the library's initializer is not run

#### Scenario: Argument from a robot.toml variable
- **WHEN** robot.toml defines `MODE = "b"` and a suite imports `ArgLib    ${MODE}`
- **THEN** the suite gets the keywords of `b` from the same entry as `ArgLib    b`

#### Scenario: Built-in variable with a static value
- **WHEN** a suite imports a library declared `args` with `${TEMPDIR}`
- **THEN** the library is loaded with the path of the temporary directory as its argument and cached under that argument set

### Requirement: The first argument set loaded without errors becomes the default entry

For a library declared `args`, the documentation of the first argument set that loads without errors SHALL also be kept as the library's default entry. The default entry SHALL record the declaration, so that later lookups need no import to learn it. It SHALL be replaced only after it has become invalid, for example because the library's files changed. Documentation requested by library name alone, which is the documentation of library-name completion items and the keyword-documentation requests by library name of the language server, SHALL use the default entry when one exists; otherwise the library SHALL be loaded without arguments, as before this change. An import written without arguments, and any other documentation target that names a library as an import without arguments, SHALL still get the documentation of its own, empty, argument set.

#### Scenario: Library-name completion
- **WHEN** a default entry exists for `ArgLib` from `ArgLib    b`, and the documentation of the `ArgLib` item of library-name completion is resolved
- **THEN** it shows the keywords of `b`, and the library is not loaded

#### Scenario: Import without arguments
- **WHEN** the default entry comes from `ArgLib    b` and a suite imports `ArgLib` without arguments
- **THEN** the suite gets the keywords `ArgLib` has without arguments (`Kw A One`)

#### Scenario: Library file changed
- **WHEN** `ArgLib.py` is edited after its default entry was stored
- **THEN** the next argument set that loads without errors becomes the new default entry

### Requirement: Import arguments whose values are only known at run time

For a library that declares its keyword set (`args` or `volatile`), RobotCode SHALL NOT load the library with an import argument that still contains a variable after static resolution, which includes an argument that contains a built-in variable that only has a value at run time. Instead, it SHALL use the library's default entry. If there is no default entry, RobotCode SHALL load the library without arguments. In both cases:
- the documentation SHALL be marked as coming from other arguments, together with the arguments that are only known at run time;
- no error SHALL be reported for the unresolved variables, and no `LibraryLoadedWithoutArguments` information (`library-imports`), because no load with the import's arguments was attempted;
- errors of the load without arguments SHALL be reported on the import like the errors of any load;
- the result SHALL NOT be written to the disk cache;
- a namespace that uses it SHALL NOT be written to the namespace cache.

The library import hover SHALL show the marker as a note above the library documentation. For an undeclared library, an argument without a static value, including one with a built-in variable that only has a value at run time, SHALL be handled as before this change.

#### Scenario: Default entry exists
- **WHEN** `ArgLib` declares `args`, its default entry comes from `ArgLib    a`, and a suite imports `ArgLib    ${SUT_MODE}`, where `${SUT_MODE}` has no statically known value
- **THEN** the suite gets the keywords of `a` without a load of the library
- **AND** no `Variable '${SUT_MODE}' not found.` error is reported
- **AND** the hover on the import shows a note that the keywords come from other arguments because `${SUT_MODE}` is only known at run time

#### Scenario: No default entry
- **WHEN** the same import is analysed with an empty cache
- **THEN** the library is loaded without arguments, and the suite gets the keywords `ArgLib` has without arguments
- **AND** no `Variable '${SUT_MODE}' not found.` error is reported
- **AND** the hover on the import shows the same note
- **AND** nothing is written to the disk cache for this import

#### Scenario: Built-in variable known only at run time
- **WHEN** `ArgLib` declares `args`, its default entry comes from `ArgLib    a`, and a suite imports `ArgLib    ${OUTPUT DIR}/x`
- **THEN** the suite gets the keywords of `a` without a load of the library, and the library never receives a placeholder value for `${OUTPUT DIR}`
- **AND** `${OUTPUT DIR}` is not reported as not found
- **AND** the hover on the import shows the note naming `${OUTPUT DIR}/x`

#### Scenario: Argument that differs only by a built-in variable known only at run time
- **WHEN** `ArgLib` declares `args`, its default entry comes from `ArgLib    a`, and one suite imports `ArgLib    /x` while another imports `ArgLib    ${OUTPUT DIR}/x`, in either order
- **THEN** the first suite gets the keywords of `/x` and its import hover shows no note
- **AND** the second suite gets the keywords of `a` and its import hover shows the note naming `${OUTPUT DIR}/x`

#### Scenario: Namespace cache
- **WHEN** namespace caching is enabled and a suite uses documentation from other arguments
- **THEN** the suite is analysed again in the next session instead of being served from the namespace cache

#### Scenario: Volatile library
- **WHEN** a library declared `volatile` is imported with `${SUT_MODE}`
- **THEN** it is loaded without arguments, no `Variable '${SUT_MODE}' not found.` error is reported, and the hover on the import shows the note

#### Scenario: Undeclared library
- **WHEN** an undeclared library is imported with `${SUT_MODE}`
- **THEN** the import reports `Variable '${SUT_MODE}' not found.`, as before this change

#### Scenario: Undeclared library with a built-in variable known only at run time
- **WHEN** an undeclared library is imported with `${OUTPUT DIR}/x`
- **THEN** it is loaded as before this change, no error is reported for `${OUTPUT DIR}`, and the hover on the import shows no note

### Requirement: Libraries declared `volatile` are never persisted

RobotCode SHALL NOT write the documentation of a library declared `volatile` to the disk cache. It SHALL load the library live and keep the result in memory per set of import arguments. A namespace that depends on it SHALL NOT be written to the namespace cache.

#### Scenario: New session
- **WHEN** a suite imports a library declared `volatile` and is analysed in two sessions
- **THEN** the library is loaded in each session

#### Scenario: Namespace cache
- **WHEN** namespace caching is enabled and a suite imports a library declared `volatile`
- **THEN** the suite is not written to the namespace cache

### Requirement: User cache settings override the declaration

A library matched by `ignored-libraries` (`robotcode.analysis.cache.ignoredLibraries`) SHALL never be read from or written to the disk cache, whatever it declares. A library matched by `ignore-arguments-for-library` (`robotcode.analysis.cache.ignoreArgumentsForLibrary`) SHALL be loaded without arguments and cached under one entry like an undeclared library, whatever it declares.

#### Scenario: Declared library in ignored-libraries
- **WHEN** `ArgLib` declares `args` and matches `ignored-libraries`
- **THEN** no disk cache entry is read or written for it, and each argument set is loaded live

#### Scenario: Declared library in ignore-arguments-for-library
- **WHEN** `ArgLib` declares `args` and matches `ignore-arguments-for-library`, and suites import `ArgLib    a` and `ArgLib    b`
- **THEN** both get the keywords `ArgLib` has without arguments, from one cache entry
