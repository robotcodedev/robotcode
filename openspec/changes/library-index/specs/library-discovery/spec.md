# Spec Delta

## Purpose

Defines which libraries and resources RobotCode lists without importing anything: standard libraries, libraries and resources that installed packages declare through entry points, project resource files and project Python libraries. Also defines how this index is shown in `robotcode doc` and in the VS Code documentation browser, and how it ranks import completion.

## ADDED Requirements

### Requirement: Packages declare libraries and resources through entry points

RobotCode SHALL read the entry-point groups `robotframework.libraries`, `robotframework.resources` and `robotframework.variables` of every distribution installed in the Python environment it runs in, editable installs included. The entry-point name SHALL be taken as the exact string a user writes after `Library`, `Resource` or `Variables`, and it may contain `/`. The entry-point value SHALL be taken as the module or package the entry lives in (`module` or `module:attribute`). The value SHALL only be shown and SHALL NOT be used to resolve the entry. Each listed entry SHALL name its distribution and version. Declared libraries and resources SHALL be listed. Declared variables SHALL NOT be listed in the documentation index and SHALL only be used for import completion. A package that declares nothing SHALL keep working when it is named explicitly.

#### Scenario: Declared library
- **WHEN** a distribution `acme 1.0` declares `Acme.Web = acme.web:Web` in `robotframework.libraries`
- **THEN** the index lists the library `Acme.Web` as declared by `acme 1.0`

#### Scenario: Declared resource with a path name
- **WHEN** a distribution declares `acme/keywords/login.resource = acme.keywords` in `robotframework.resources`
- **THEN** the index lists the resource `acme/keywords/login.resource`

#### Scenario: Declared variables are not listed
- **WHEN** a distribution declares `acme/vars.yaml = acme` in `robotframework.variables`
- **THEN** the documentation index does not list it

#### Scenario: Package without declarations
- **WHEN** a library package declares no entry points and a user runs `robotcode doc SeleniumLibrary`
- **THEN** the library is documented as any explicitly named library, although it does not appear in the index

### Requirement: The index is built without importing

Building the index SHALL NOT import any Python module of a listed library or variable file, SHALL NOT import the module named in an entry-point value and SHALL NOT instantiate any library. It SHALL only read package metadata, the RobotCode configuration and project files.

#### Scenario: Library whose import fails
- **WHEN** a distribution declares a library whose module raises an exception on import, and the index is built
- **THEN** the library is listed
- **AND** its module has not been imported

### Requirement: Declared entries open as Robot Framework imports them

Opening an index entry SHALL resolve its name exactly as Robot Framework resolves a `Library` or `Resource` import of that name. It SHALL use the project root as the importing directory. It SHALL pass no import arguments, except for project libraries declared with arguments. The same name declared by two distributions SHALL be listed twice, once for each distribution. Opening either entry SHALL show what Robot Framework would import for that name.

#### Scenario: Same name from two distributions
- **WHEN** the distributions `acme 1.0` and `other 2.0` both declare the library `AcmeLibrary`
- **THEN** the index lists `AcmeLibrary` twice, once with `acme 1.0` and once with `other 2.0`

#### Scenario: Opening a declared resource
- **WHEN** the entry `acme/keywords/login.resource` is opened and the directory containing the `acme` package is on the Python path
- **THEN** the documentation of that resource file is shown, as `Resource    acme/keywords/login.resource` would import it

### Requirement: Invalid declarations are reported

An entry of any of the three groups SHALL be reported as an invalid declaration with its group, distribution, version, name, value and the reason if:
- its value is not a module reference (`module` or `module:attribute` with dotted identifiers);
- its name is empty;
- its name contains a variable (`${`, `@{`, `&{`, `%{`);
- its name contains `::`;
- in the resources group, the extension of its name, compared case-insensitively, is not a resource file extension that the installed Robot Framework accepts;
- in the variables group, its name is neither a path that the installed Robot Framework imports as a variable file (ending in one of its variable-file extensions, `/` or the path separator) nor a dotted module name, which Robot Framework imports as a module.

RobotCode SHALL NOT try to correct an invalid declaration. Invalid declarations SHALL NOT be listed as entries and SHALL NOT affect import completion.

#### Scenario: Value that is not a module reference
- **WHEN** a distribution declares `Bad = not a module` in `robotframework.libraries`
- **THEN** `Bad` is reported as an invalid declaration, with the reason that the value is not a module reference

#### Scenario: Name with import arguments
- **WHEN** a distribution declares `Remote::http://127.0.0.1:8270 = acme` in `robotframework.libraries`
- **THEN** it is reported as an invalid declaration, because entry names carry no import arguments

#### Scenario: Markdown resource on an older Robot Framework
- **WHEN** a distribution declares the resource `acme/keywords.robot.md`, on RF 7.4
- **THEN** it is reported as an invalid declaration, because the installed Robot Framework does not accept Markdown resource files
- **AND** on RF 7.5 it is listed as a resource

#### Scenario: Variables by path and by module name
- **WHEN** a distribution declares `acme/vars.toml = acme` and `acme.vars = acme.vars` in `robotframework.variables`
- **THEN** `acme/vars.toml` is reported as an invalid declaration
- **AND** `acme.vars` is not reported

### Requirement: Standard libraries are listed

The index SHALL list the standard libraries of the installed Robot Framework: the names in Robot Framework's `STDLIBS`, except `Easter` and `Reserved`.

#### Scenario: Standard libraries on RF 7.5
- **WHEN** the index is built on RF 7.5
- **THEN** it lists `BuiltIn`, `Collections`, `DateTime`, `Dialogs`, `OperatingSystem`, `Process`, `Remote`, `Screenshot`, `String`, `Telnet` and `XML`
- **AND** it does not list `Easter`

### Requirement: Project resource files are listed

The index SHALL list the resource files of the project, whether they are imported anywhere or not. The project files SHALL be collected as the language server collects its workspace documents:
- the files below the project root (each workspace folder in the language server);
- without files and folders matched by `.robotignore` or `.gitignore`;
- without hidden files and folders;
- without the configured exclude patterns (`[tool.robotcode-analyze] exclude-patterns`, and `robotcode.workspace.excludePatterns` in VS Code).

The extensions SHALL be the resource extensions that the installed Robot Framework accepts, compared case-insensitively. Each file SHALL be listed by its path relative to the project root, with `/` as the separator on every operating system.

<!-- The following paragraph follows the recommended default of design.md Q2 (not yet decided); rewrite it before implementation if Q2 is decided otherwise. -->
Files ending in `.resource`, and on Robot Framework 6.1 or newer `.rsrc`, SHALL be listed without reading them. A file with one of the other resource extensions (`.robot`, `.rst` and `.rest`, on Robot Framework 6.1 or newer `.json`, and on Robot Framework 7.5 `.md` and `.markdown`) SHALL be listed only if its name before the extension is not `__init__` (compared case-insensitively), Robot Framework reads it as a resource file without raising an error, and it defines at least one keyword, variable or import. When reading it on Robot Framework 6.0 or newer, RobotCode SHALL use the languages configured for the project, and Robot Framework's messages about the file SHALL NOT be printed. Suite files with a test case or task section are therefore not listed, and neither are suite initialization files or documents that contain no Robot Framework code.

#### Scenario: Resource file that nothing imports
- **WHEN** the project contains `resources/unused.resource` and no file imports it
- **THEN** the index lists `resources/unused.resource`

#### Scenario: Ignored and excluded files
- **WHEN** the project contains `build/gen.resource` with `build/` in `.gitignore`, `.venv/x.resource`, and `vendor/y.resource` matched by an exclude pattern
- **THEN** none of these files is listed

#### Scenario: Suite file and keyword-only robot file
- **WHEN** the project contains `tests/login.robot` with a `*** Test Cases ***` section and `common/shared.robot` with only a `*** Keywords ***` section
- **THEN** `common/shared.robot` is listed
- **AND** `tests/login.robot` is not listed

#### Scenario: Suite initialization file
- **WHEN** the project contains `tests/__init__.robot` with a `Suite Setup` setting and a `Library` import
- **THEN** `tests/__init__.robot` is not listed

#### Scenario: Markdown document without Robot Framework code
- **WHEN** the project contains a `README.md` without a Robot Framework code block and `keywords.md` with a `robotframework` code block that defines a keyword, on RF 7.5
- **THEN** `keywords.md` is listed
- **AND** `README.md` is not listed

#### Scenario: Markdown resource on an older Robot Framework
- **WHEN** the same project is indexed on RF 7.4
- **THEN** neither `.md` file is listed

#### Scenario: Paths on Windows
- **WHEN** the project contains `resources\login.resource` and is indexed on Windows
- **THEN** it is listed as `resources/login.resource`

### Requirement: Project Python libraries are declared in a RobotCode tool section

<!-- The section name `robotcode-doc` and the project root as the base of relative paths follow the recommended defaults of design.md Q1 (not yet decided); replace them before implementation if Q1 is decided otherwise. -->
RobotCode's configuration SHALL accept the tool section `[tool.robotcode-doc]` with the key `libraries` and its variant `extend-libraries`, each in the shape of `listeners`: a table from a library name to a list of import arguments. Like `[tool.robotcode-analyze]`, the section SHALL be read from every configuration file RobotCode loads (`robot.toml`, `.robot.toml`, `pyproject.toml` and the user configuration) and combined across them, and `extend-libraries` SHALL add its entries to `libraries`. The section SHALL NOT be part of a profile, and selecting a profile SHALL NOT change the list. Each name SHALL be listed as a project library without importing it. The string SHALL decide between module and file import as in Robot Framework: a name ending in `.py`, `/` or the path separator is a path relative to the project root, and any other name is a module or class found through the Python path, including `python-path`. Opening the entry SHALL import the library with the given arguments, and SHALL resolve variables in them from the selected profile. The section SHALL NOT change the analysis of imports and SHALL NOT be passed to Robot Framework.

#### Scenario: Module and file libraries
- **WHEN** `robot.toml` contains `[tool.robotcode-doc.libraries]` with `CustomerLib = []` and `"lib/legacy/Old.py" = ["strict"]`
- **THEN** the index lists the project libraries `CustomerLib` and `lib/legacy/Old.py`, the latter with the argument `strict`
- **AND** opening `lib/legacy/Old.py` documents the file `lib/legacy/Old.py` below the project root, imported with `strict`

#### Scenario: Local configuration extends the list
- **WHEN** a `.robot.toml` next to that `robot.toml` contains `[tool.robotcode-doc.extend-libraries]` with `LocalLib = []`
- **THEN** the index lists `CustomerLib`, `lib/legacy/Old.py` and `LocalLib`

#### Scenario: Profiles do not change the list
- **WHEN** the configuration also defines the profile `ci`, and `robotcode -p ci doc` is run
- **THEN** the index lists the same project libraries as `robotcode doc`

#### Scenario: Robot run is unaffected
- **WHEN** `robotcode robot` is run with that configuration
- **THEN** no option derived from `[tool.robotcode-doc]` is passed to Robot Framework

### Requirement: robotcode doc without targets shows the index

The documentation command of `doc-cli` (`robotcode doc`) SHALL show the index when it is called without targets and without lookup options (`documentation-cli`, "Only explicitly named targets are documented"). It SHALL NOT import or document any listed entry for this.
- When the output-mode rules of `documentation-cli` select the documentation browser, the TUI SHALL show the index in its sidebar, in the groups of the Markdown listing. Selecting an entry SHALL show its documentation, resolved as described for opening entries.
- Otherwise, the command SHALL write a Markdown listing to standard output, or to the file given with `--output`. The listing starts with `# Libraries and resources`, followed by the sections `## Standard libraries`, `## Installed libraries`, `## Installed resources`, `## Project libraries`, `## Project resources` and `## Invalid declarations`, in this order. Empty sections SHALL be left out.
- Each entry is one list item that starts with its name in backticks:
  - installed entries are followed by their distribution and version;
  - project libraries with arguments are followed by their arguments;
  - invalid declarations are followed by their group, distribution, version and reason.
- Entries SHALL be sorted by name, ignoring case. Entries with the same name are sorted by distribution.
- When the command offers JSON output, the index SHALL be available as JSON with the same fields.

#### Scenario: Piped listing
- **WHEN** `robotcode doc | cat` is run in a project with the declared library `Acme.Web` of `acme 1.0` and the resource file `resources/login.resource`
- **THEN** the output contains `## Standard libraries` with `` `BuiltIn` ``, `## Installed libraries` with `` `Acme.Web` `` and `acme 1.0`, and `## Project resources` with `` `resources/login.resource` ``
- **AND** no library has been imported

#### Scenario: Opening an entry in the TUI
- **WHEN** `robotcode doc` runs in an interactive terminal outside an AI-agent session and the user selects `Collections` in the sidebar
- **THEN** the documentation of `Collections` is shown as for `robotcode doc Collections`

### Requirement: The VS Code documentation browser shows the index

The documentation browser of `vscode-doc-browser` SHALL offer an index view in its sidebar. It SHALL show the groups of the Markdown listing for the workspace folder of the shown page, and it SHALL be filterable by name. Selecting a library or resource SHALL open its documentation in the same browser panel, resolved as described for opening entries. Invalid declarations SHALL be shown with their reason and SHALL NOT be openable. The language server SHALL provide the index to the client through a request, and the request SHALL NOT import any entry.

#### Scenario: Opening an installed library from the index
- **WHEN** the documentation browser is open and the user selects the installed library `Acme.Web` in the index view
- **THEN** the panel shows the documentation of `Acme.Web`

#### Scenario: Project resource in the index
- **WHEN** the workspace folder contains `resources/login.resource`
- **THEN** the index view lists it under project resources, and selecting it shows its documentation

#### Scenario: Project library in the index
- **WHEN** the `robot.toml` of the workspace folder contains `[tool.robotcode-doc.libraries]` with `CustomerLib = []`
- **THEN** the index view lists `CustomerLib` under project libraries

### Requirement: Import completion ranks declared entries first

Completion of `Library`, `Resource` and `Variables` import names SHALL offer the same candidates as before. It SHALL rank a candidate before the others when it matches a declaration of the corresponding group: its full name, meaning the text before the completed segment plus the candidate, either equals a declared name or is followed in a declared name by `.` or `/`. Matched candidates SHALL name the declaring distributions in their detail. Invalid declarations SHALL NOT affect the ranking.

#### Scenario: Declared library at the top
- **WHEN** a distribution declares the library `DocTest.VisualTest` and completion is requested after `Library    `
- **THEN** `DocTest` is offered before the undeclared modules of the Python path
- **AND** after `Library    DocTest.` the candidate `VisualTest` is offered first

#### Scenario: Declared resource folder
- **WHEN** a distribution declares the resource `acme/keywords/login.resource` and completion is requested after `Resource    `
- **THEN** the folder `acme` is offered before other folders of the Python path

### Requirement: Internal modules of robot.libraries are not offered

The "Module (Internal)" candidates of `Library` import completion SHALL be only names in Robot Framework's `STDLIBS`, without the libraries that are imported automatically (`BuiltIn`, `Easter`, and before RF 7.0 `Reserved`).

#### Scenario: Helper modules on RF 7.5
- **WHEN** completion is requested after `Library    ` on RF 7.5
- **THEN** `Collections` is offered as "Module (Internal)"
- **AND** `dialogs_py` and `normalizer` are not offered as "Module (Internal)"
