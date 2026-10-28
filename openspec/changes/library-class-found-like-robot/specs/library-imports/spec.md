## ADDED Requirements

### Requirement: A library import loads the class Robot Framework loads

For a library import, RobotCode SHALL load the same class or module that the installed Robot Framework loads for it, by name and by path. On Robot Framework ≥ 7.2 this includes a library class whose name differs from its module when it is the only class of that module marked with `ROBOT_AUTO_KEYWORDS`, by `@library` or by hand. The keywords of that class SHALL be available like those of any library class.

#### Scenario: Class with another name than its module
- **WHEN** on Robot Framework ≥ 7.2 the module `mylib/keywords.py` defines only the class `MyLibKeywords` with `ROBOT_AUTO_KEYWORDS = True` and the method `do_greeting`, and a suite has `Library    mylib.keywords` and calls `Do Greeting    World`
- **THEN** `robotcode analyze code` reports neither `LibraryContainsNoKeywords` on the import nor `KeywordNotFound` for `Do Greeting`
- **AND** the location of `Do Greeting` is the line of `def do_greeting` in `mylib/keywords.py`

#### Scenario: Class marked with @library, imported by path
- **WHEN** on Robot Framework ≥ 7.2 the file `deco_lib.py` defines only the class `Other` decorated with `@library` and its method `greet` decorated with `@keyword`, and a suite has `Library    deco_lib.py`
- **THEN** the import provides the keyword `Greet`

#### Scenario: More than one marked class
- **WHEN** on Robot Framework ≥ 7.2 a module defines two classes with `ROBOT_AUTO_KEYWORDS`, neither named like the module, and no module-level keywords
- **THEN** the import reports `LibraryContainsNoKeywords`, as `robot` loads the module as well

#### Scenario: Robot Framework older than 7.2
- **WHEN** on Robot Framework < 7.2 a suite imports the module `mylib.keywords` from the first scenario
- **THEN** the import reports `LibraryContainsNoKeywords`, as `robot` loads the module as well

### Requirement: A failed library import is named as in Robot Framework

When importing a library fails, RobotCode SHALL report it with the same wording as `robot`: "Importing library '<name>' failed: …", in the analysis and in `robotcode doc`.

#### Scenario: Library that does not exist
- **WHEN** a suite has `Library    NoSuchLib` and no module `NoSuchLib` exists
- **THEN** `robotcode analyze code` reports "Importing library 'NoSuchLib' failed: ModuleNotFoundError: No module named 'NoSuchLib'" on the import

#### Scenario: Documentation of a library that does not exist
- **WHEN** `robotcode doc lib NoSuchLib` runs and no module `NoSuchLib` exists
- **THEN** the error output contains "Importing library 'NoSuchLib' failed"
