# Spec Delta

## Purpose

Defines which Python and Robot Framework versions RobotCode supports, which combinations of them are tested, and how the requirements are documented, so that users know what they can rely on.

## ADDED Requirements

### Requirement: Supported Python versions

RobotCode SHALL support Python 3.10 to 3.15. Every RobotCode package SHALL list exactly these Python versions in its classifiers, and SHALL require Python 3.10 or newer without an upper bound.

#### Scenario: Package metadata
- **WHEN** a user looks at the metadata of a RobotCode package, for example on PyPI
- **THEN** its classifiers list Python 3.10, 3.11, 3.12, 3.13, 3.14 and 3.15, and it requires Python 3.10 or newer

#### Scenario: Python 3.9
- **WHEN** a user installs a RobotCode package with Python 3.9
- **THEN** the installer refuses it, because the package requires Python 3.10 or newer

### Requirement: Supported combinations of Python and Robot Framework

RobotCode SHALL support each Robot Framework version from 5.0 to 7.5 on those Python versions from 3.10 on that this Robot Framework version officially supports, as its classifiers on PyPI declare:

| Robot Framework | Python |
|---|---|
| 5.0 | 3.10 |
| 6.0 | 3.10 – 3.11 |
| 6.1, 7.0 | 3.10 – 3.12 |
| 7.1, 7.2 | 3.10 – 3.13 |
| 7.3, 7.4 | 3.10 – 3.14 |
| 7.5 | 3.10 – 3.15 |

#### Scenario: Python 3.15
- **WHEN** a project uses Python 3.15
- **THEN** Robot Framework 7.5 is the only supported Robot Framework version for it

#### Scenario: Robot Framework 5.0
- **WHEN** a project uses Robot Framework 5.0
- **THEN** Python 3.10 is the only supported Python version for it

### Requirement: Tested combinations

The CI SHALL run the test suite for every supported combination of Python and Robot Framework on Linux, macOS and Windows, and SHALL NOT run it for any other combination. The hatch `devel` matrix SHALL contain exactly the supported combinations.

#### Scenario: Python 3.15 in the CI
- **WHEN** the CI tests a commit
- **THEN** it runs the test suite with Python 3.15 and Robot Framework 7.5 on Linux, macOS and Windows, and with Python 3.15 and no other Robot Framework version

#### Scenario: Unsupported combination in the CI
- **WHEN** the CI tests a commit
- **THEN** it runs no job with Robot Framework 5.0 and Python 3.11

#### Scenario: Development environments
- **WHEN** a contributor lists the hatch environments
- **THEN** the `devel` matrix contains `devel.py3.15-rf75` and `devel.py3.10-rf50`, but not `devel.py3.15-rf74` or `devel.py3.11-rf50`

### Requirement: Unsupported combinations are not refused

RobotCode SHALL NOT check whether a combination of Python and Robot Framework is supported. The language server, the command line, the VS Code extension and the IntelliJ plugin SHALL start with every Python 3.10 or newer that has Robot Framework 5.0 or newer installed, including combinations that are not supported, and SHALL NOT warn about such a combination.

#### Scenario: Robot Framework 7.2 with Python 3.15
- **WHEN** a project uses Python 3.15 with Robot Framework 7.2
- **THEN** RobotCode starts and analyzes the project as with a supported combination, and errors that Robot Framework itself raises, such as the XML library failing to initialize, are reported like any other error of a library import

### Requirement: Documented requirements

The README and the Get Started page of the documentation SHALL show the supported combinations as a table. They SHALL say that only these combinations are tested in the CI, to keep the effort low, that other combinations may work but using them is the user's responsibility, and, as an example, that Robot Framework versions before 7.5 may not work with Python 3.15.

#### Scenario: Reading the requirements
- **WHEN** a user reads the requirements in the README or on the Get Started page
- **THEN** both show the table of supported combinations, and both say that other combinations are not tested and are the user's responsibility, with Robot Framework before 7.5 on Python 3.15 as the example
