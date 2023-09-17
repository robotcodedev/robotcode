# Change Log

All notable changes to "robotcode" are documented in this file.

## v0.57.0 (2023-09-17)

### Feat

- **langserver**: improved quickfix `create keyword` can now add keywords to resource files if valid namespace is given
- **langserver**: Quick fixes for code actions are generated for all diagnostics specified in the request, and quick fixes are generated with the name of the variable or keyword in the label.
- new code action refactor rewrite: surroundings for TRY/EXCEPT/FINALLY

### Refactor

- **langserver**: move code action `assign result to variable` to refactorings

## v0.56.0 (2023-09-11)

### Feat

- **langserver**: new code action quick fix - Add argument
- **langserver**: new code action quick fix - create suite variable
- **langserver**: new code action quick fixes - assign kw result to variable, create local variable, disable robot code diagnostics for line

### Refactor

- **langserver**: move all error messages to one place

## v0.55.1 (2023-09-06)

### Fix

- **debugger**: correct update of test run results when suite teardown fails or is skipped during suite teardown for RF 4.1

## v0.55.0 (2023-09-05)

### Feat

- **langserver**: support for robocop 4.1.1 code descriptions
- **langserver**: better completion for variable imports

### Fix

- **langserver**: correct handling of @ variable and & dictionary arguments in signature help and completion
- **langserver**: don't complete arguments for run keywords
- **vscode**: update of RobotCode icon in status bar when Python environment is changed

### Refactor

- move code_actions and support unions with enums and string in dataclasses

## v0.54.3 (2023-09-03)

### Fix

- **langserver**: dont show values in completions if the token before is an named argument token
- **langserver**: change scope name of argument tokens to allow better automatic opening of completions
- **langserver**: correct some styles for semantic highlightning

## v0.54.2 (2023-09-02)

### Fix

- **langserver**: escape pipe symbols in keyword argument descriptions in hover
- **vscode**: correct highligtning of keyword arguments
- **langserver**: sorting of completion items on library imports

## v0.54.1 (2023-09-02)

### Fix

- **build**: disable html report for pytest

## v0.54.0 (2023-09-01)

### Feat

- **langserver**: better signature help and completion of keyword arguments and library import arguments, including completions for type converters like Enums, bools, TypedDict, ...
- **langserver**: better argument signatures for completion and signature help

### Fix

- **langserver**: correct end positon of completion range in arguments
- **langserver**: disable directory browsing in documentation server

## v0.53.0 (2023-08-28)

### Feat

- **langserver**: first version of completion of enums and typed dicts for RF >= 6.1
- **robocop**: with code descriptions in `robocop` diagnostics you can jump directly to the website where the rule is explained

## v0.52.0 (2023-08-26)

### Feat

- **langserver**: inlay hint and signature help now shows the correct parameters and active parameter index, make both work for library and variable imports and show type informations if type hints are defined
- **debugger**: add some more informations in verbose mode
- **langserver**: goto, highlight, rename, hover, find references for named arguments
- **robotcode**: internal cli args are now hidden

### Fix

- use import nodes to add references for libraries/resources and variables

## v0.51.1 (2023-08-14)

## v0.51.0 (2023-08-13)

### Feat

- **langserver**: rework "Analysing", "Hover", "Document Highlight", "Goto" and other things to make them faster, simpler, and easier to extend
- **langserver**: highlight namespace references
- **discovery**: option to show/hide parsing errors/warnings at suite/test discovery

### Fix

- **langserver**: correct highlighting of keyword arguments with default value
- **langserver**: correct hovering, goto, etc. for if/else if/inline if statements

### Refactor

- **langserver**: speed up hovering for keywords, variables and namespace by using references from code analysis

## v0.50.0 (2023-08-08)

### Feat

- **discover**: tags are now discovered normalized by default
- **robotcode**: use default configuration if no project root or project configuration is found

### Fix

- made RobotCode work with Python 3.12

## v0.49.0 (2023-08-03)

### Feat

- "create keyword" quick fix detects bdd prefixes in the keyword being created and creates keywords without the prefix
- reporting suites and tests with the same name when tests are discovered
- user default `robot.toml` config file

### Fix

- completion of bdd prefixes optimized

## v0.48.0 (2023-07-30)

### Feat

- **vscode**: added a statusbar item that shows some information about the current robot environment, like version, python version, etc.
- removed old `robotcode.debugger` script in favor of using `robotcode debug` cli command

### Fix

- better output for discover info command
- discover tests for RF 6.1.1
- in a test run, errors that occur are first selected in the test case and not in the keyword definition
- correct completion of settings with ctrl+space in some situation
- correct update of test run results when suite teardown fails or is skipped during suite teardown
- **robotcode**: add missing profile settings to config documentation

## v0.47.5 (2023-07-20)

### Fix

- add missing log-level in testcontroller

## v0.47.4 (2023-07-20)

### Fix

- don't update tests if editing `__init__.robot` files

## v0.47.3 (2023-07-18)

### Fix

- move to commitizen to create new releases, this is only a dummy release..
- reset changlog

## v0.47.2 (2023-07-17)

### Fix

- duplicated header completions if languages contains same words

## v0.47.1 (2023-07-10)

### Fix

- dont update tests in an opened file twice if file is saved
- **debugger**: print the result of an keyword in debugger also if it has a variable assignment

## v0.47.0 (2023-07-10)

### Feat

- **debugger**: expanding dict and list variables in the variable view of the debugger, this also works in hints over variables, in the watch view and also by evaluating expressions/keywords in the command line of the debugger
- show deprecation information if using `Force Tags` and `Default Tags`
- complete reserved tags in Tags settings
- show more informations in hint over a variables import
- **debugger**: simple keyword completion in debugger
- **debugger**: switching between "keyword" and "expression" mode by typing `# exprmode` into debug console (default: keyword mode)
- **debugger**: debugger does not stop on errors caught in TRY/EXCEPT blocks

### Fix

- **debugger**: hide uncaught exceptions now also works correctly for RF >=5 and < 6.1
- **debugger**: (re)disable attachPython by default
- correct message output in test results view
- stabilize debugger with new vscode version > 1.79
- Update diagnostic for Robocop 4.0 release after disablers module was rewritten

## v0.46.0 (2023-07-05)

### Feat

- Allow multiline RF statements in debug console

### Fix

- **debugger**: evaluation expressions in RFW >= 6.1 not work correctly
- insted of starting the debugger, start robotcode.cli in debug launcher

## v0.45.0 (2023-06-23)

### Feat

- library doc now generates a more RFW-like signature for arguments and argument defaults like ${SPACE}, ${EMPTY}, ${True}, etc. for the respective values

### Fix

- document_symbols throws exception if section name is empty
- change code property for diagnostics for analyse imports to ImportRequiresValue

## v0.44.1 (2023-06-21)

### Fix

- completion and diagnostics for import statements for RF >= 6.1

## v0.44.0 (2023-06-21)

### Feat

- add option to start a debugpy session for debugging purpose

### Fix

- correct handling error in server->client JSON RPC requests
- detect languageId of not given at "textDocument/didOpen"
- extension not terminating sometimes on vscode exit

### Refactor

- make mypy and ruff happy

## v0.43.2 (2023-06-20)

### Fix

- update testitems does not work correctly if a __init__.robot is changed
- only update test explorer items if file is a valid robot suite

## v0.43.1 (2023-06-15)

### Fix

- Intellisense doesn't work when importing yml file with variables #143

## v0.43.0 (2023-06-14)

### Feat

- support for importing `.json` files in RF 6.1
- Enable importing and completion of `.rest`, `.rsrc` and `.json` resource extensions (not parsing)
- support for new RF 6.1 `--parse-include` option for discovering and executing tests

### Fix

- correct highlightning `*** Tasks ***` and `*** Settings ***`
- hover over a tasks shows "task" in hint and not "test case"
- checks for robot version 6.1

## v0.42.0 (2023-06-05)

### Feat

- support for new `--parseinclude` option in robot config

### Fix

- compatibility with Python 3.12
- resolving variable values in hover for RF 6.1

### Refactor

- fix some mypy warnings

## v0.41.0 (2023-05-24)

### Feat

- new `robotcode.robotidy.ignoreGitDir` and `robotcode.robotidy.config` setting to set the config file for _robotidy_ and to ignore git files if searching for config files for _robotidy_
- optimize/speedup searching of files, setting `robotcode.workspace.excludePatterns` now supports gitignore like patterns

### Fix

- patched FileReader for discovery should respect accept_text

### Refactor

- some optimization in searching files

## v0.40.0 (2023-05-17)

### Feat

- show argument infos for dynamic variables imports

### Fix

- wrong values for command line vars

## v0.39.0 (2023-05-16)

### Feat

- new command `RobotCode: Select Execution Profiles`
- language server now is a robotcode cli plugin and can use config files and execution profiles

## v0.38.0 (2023-05-15)

### Feat

- new command `discover tags`

### Fix

- Bring output console into view if robotcode discovery fails
- use dispose instead of stop to exit language server instances

### Refactor

- fix some ruff warnings

## v0.37.1 (2023-05-11)

### Fix

- **discover**: wrong filename in diagnostics message on update single document

## v0.37.0 (2023-05-10)

### Feat

- Reintroduce of updating the tests when typing
- test discovery now runs in a separate process with the `robotcode discover` command, this supports also prerunmodifiers and RF 6.1 custom parsers

### Fix

- some correction in completions for robotframework >= 6.1
- **langserver**: resolving variables as variable import arguments does not work correctly

### Refactor

- correct some help texts and printing of output

## v0.36.0 (2023-05-01)

### Feat

- simple `discover all` command
- select run profiles in test explorer

## v0.35.0 (2023-04-25)

### Feat

- **runner**: add `run` alias for `robot` command in cli

### Fix

- **debug-launcher**: switch back to `stdio` communication, because this does not work on Windows with python <3.8

## v0.34.1 (2023-04-21)

### Fix

- some code scanning alerts

## v0.34.0 (2023-04-20)

### Feat

- **debugger**: refactored robotcode debugger to support debugging/running tests with robotcode's configurations and profiles, also command line tool changes.

### Fix

- correct toml json schema urls

### Refactor

- fix some ruff errors
- create robotcode bundled interface

## v0.33.0 (2023-04-09)

### Feat

- Improved Handling of UTF-16 encoded multibyte characters, e.g. emojis are now handled correctly

### Fix

- end positions on formatting

## v0.32.3 (2023-04-07)

### Fix

- correct formatting with robotframework-tidy, also support tidy 4.0 reruns now, closes #124

## v0.32.2 (2023-04-05)

### Fix

- update git versions script

## v0.32.1 (2023-04-05)

### Fix

- dataclasses from dict respects Literals also for Python 3.8 and 3.9

## v0.32.0 (2023-04-05)

### Feat

- allow expression for str options, better handling of tag:<pattern>, name:<pattern> options
- add command for robots _testdoc_

### Refactor

- switch to src layout

## v0.31.0 (2023-03-30)

### Feat

- Profiles can now be enabled or disabled, also with a condition. Profiles can now also be selected with a wildcard pattern.
- new commands robot, rebot, libdoc for robotcode.runner
- **robotcode**: Add commands to get informations about configurations and profiles

### Refactor

- move the config command to robotcode package
- add more configuration options, update schema, new command config

## v0.30.0 (2023-03-22)

### Feat

- **robotcode-runner**: robotcode-runner now supports all features, but not all robot options are supported

### Refactor

- implement robot.toml config file and runner

## v0.29.0 (2023-03-21)

### Feat

- support for Refresh Tests button in test explorer

## v0.28.4 (2023-03-19)

### Fix

- update regression tests

## v0.28.3 (2023-03-19)

### Fix

- correct analysing keywords with embedded arguments for RF >= 6.1
- correct discovering for RobotFramework 6.1a1

## v0.28.2 (2023-03-10)

### Fix

- correct version of robotcode runner

## v0.28.1 (2023-03-10)

### Fix

- Source actions are missing in the context menu for versions #129

## v0.28.0 (2023-03-09)

### Feat

- debugger is now started from bundled/tool/debugger if available

### Fix

- #125 Robot Code crashes with a variables file containing a Dict[str, Callable]
- return codes for command line tools now uses sys.exit with return codes

## v0.27.2 (2023-03-06)

### Fix

- unknown workspace edit change received at renaming
- The debugger no longer requires a dependency on the language server

### Refactor

- some big refactoring, introdude robotcode.runner project

## v0.27.1 (2023-03-01)

## v0.27.0 (2023-03-01)

### Feat

- split python code into several packages, now for instance robotcode.debugger can be installed standalone

### Refactor

- introduce bundled/libs/tool folders and move python source to src folder

## v0.26.2 (2023-02-25)

### Fix

- publish script

## v0.26.1 (2023-02-25)

### Fix

- Github workflow

## v0.26.0 (2023-02-25)

### Feat

- Switch to [hatch](https://hatch.pypa.io) build tool and bigger internal refactorings

### Fix

- correct error message if variable import not found

### Refactor

- generate lsp types from json model
- fix some mypy errors
- fix some PIE810 errors
- simplify some code
- fix some flake8-return warnings
- fix some pytest ruff warning
- use `list` over useless lambda in default_factories
- change logger calls with an f-string to use lambdas
- Replace *Generator with *Iterator
- fix some ruff errors and warnings, disable isort in precommit
- **robotlangserver**: workspace rpc methods are now running threaded
- **robotlangserver**: optimize test discovering

## v0.25.1 (2023-01-24)

### Fix

- **vscode**: In long test runs suites with failed tests are still marked as running even though they are already finished

### Refactor

- add `type` parameter to end_output_group

## v0.25.0 (2023-01-24)

### Feat

- **debugger**: new setting for `outputTimestamps` in launch and workspace configuration to enable/disable timestamps in debug console

## v0.24.4 (2023-01-24)

### Fix

- **debugger**: show error/warning messages of python logger in debug console

## v0.24.3 (2023-01-23)

### Fix

- set env and pythonpath erlier in lifecycle to prevent that sometime analyses fails because of python path is not correct

## v0.24.2 (2023-01-20)

### Fix

- **robotlangserver**: retun correct robot framework version test

## v0.24.1 (2023-01-20)

### Fix

- **robotlangserver**: robot version string is incorrectly parsed if version has no patch
- start diagnostics only when the language server is fully initialized

## v0.24.0 (2023-01-16)

### Feat

- **robotlangserver**: Create undefined keywords in the same file

### Refactor

- prepare create keywords quickfix
- introduce asyncio.RLock

## v0.23.0 (2023-01-13)

### Feat

- **robotlangserver**: highlight named args in library imports

### Fix

- **robotlangserver**: remove possible deadlock in completion

## v0.22.1 (2023-01-13)

### Fix

- **robotlangserver**: resolving imports with arguments in diffent files and folders but with same string representation ie. ${curdir}/blah.py now works correctly
- **robotlangserver**: generating documentation view with parameters that contains .py at the at does not work

## v0.22.0 (2023-01-12)

### Feat

- Add onEnter rule to split a long line closes #78

## v0.21.4 (2023-01-11)

### Fix

- **robotlangserver**: remove possible deadlock in Namespace initialization

## v0.21.3 (2023-01-10)

### Fix

- **robotlangserver**: if a lock takes to long, try to cancel the lock

## v0.21.2 (2023-01-10)

### Fix

- use markdownDescription in settings and launch configurations where needed

### Refactor

- remove unneeded code

### Perf

- massive overall speed improvements

## v0.21.1 (2023-01-07)

### Perf

- Caching of variable imports

## v0.21.0 (2023-01-07)

### Feat

- new setting `robotcode.analysis.cache.ignoredLibraries` to define which libraries should never be cached

### Fix

- **robotlangserver**: speedup analyser
- try to handle unknow documents as .robot files to support resources as .txt or .tsv files
- **robotlangserver**: Loading documents hardened
- generating keyword specs for keywords with empty lineno

## v0.20.0 (2023-01-06)

### Feat

- **robotlangserver**: Implement embedded keyword precedence for RF 6.0, this also speedups keyword analysing
- **robotlangserver**: support for robot:private keywords for RF>6.0.0
- **robotlangserver**: show keyword tags in keyword documentation
- **debugger**: add `include` and `exclude` properties to launch configurations

### Fix

- **robotlangserver**:  Ignore parsing errors in test discovery
- **vscode-testexplorer**: Correctly combine args and paths in debug configurations
- speedup loading and analysing tests

### Refactor

- **robotlangserver**: Better error messages if converting from json to dataclasses
- **debugger**: Move debugger.modifiers one level higher to shorten the commandline

## v0.19.1 (2023-01-05)

### Fix

- **debugger**: use default target if there is no target specified in launch config with purpose test

## v0.19.0 (2023-01-05)

### Feat

- New command `Clear Cache and Restart Language Servers`
- **debugger**: possibility to disable the target `.` in a robotcode launch configurations with `null`, to append your own targets in `args`
- **robotlangserver**: new setting `.analysis.cache.saveLocation` where you can specify the location where robotcode saves cached data

### Fix

- **robotlangserver**: don't report load workspace progress if progressmode is off

## v0.18.0 (2022-12-15)

### Feat

- **robotlangserver**: Speedup loading of class and module libraries

### Fix

- **robotlangserver**: Update libraries when editing not work

## v0.17.3 (2022-12-11)

### Fix

- **vscode**: Highlightning comments in text mate mode
- **vscode**: Some tweaks for better highlightning

### Perf

- **robotlangserver**: Speedup keyword completion
- **robotlangserver**: refactor some unnecessary async/await methods

## v0.17.2 (2022-12-09)

### Fix

- **vscode**: Enhance tmLanguage to support thing  like variables, assignments,... better

## v0.17.1 (2022-12-08)

## v0.17.0 (2022-12-08)

### Feat

- **vscode**: Add configuration defaults for `editor.tokenColorCustomizations` and `editor.semanticTokenColorCustomizations`

## v0.16.0 (2022-12-08)

### Feat

- **vscode**: Provide better coloring in the debug console.
- **robotlangserver**: Highlight dictionary keys and values with different colors
- **robotlangserver**: Optimization of the analysis of keywords with embedded arguments
- **robotlangserver**: Highlight embedded arguments
- **vscode**: add new command `Restart Language Server`

### Fix

- **robotlangserver**: try to hover, goto, ... for keyword with variables in names
- **vscode**: Capitalize commands categories

## v0.15.1 (2022-12-07)

## v0.15.0 (2022-12-07)

### Feat

- Simplifying implementation of discovering of tests

### Fix

- debugger now also supports dictionary expressions

##  0.14.5

- Improve analysing, find references and renaming of environment variables
- Optimize reference handling.
  - This allows updating references when creating and deleting files, if necessary.

##  0.14.4

- Correct resolving paths for test execution

##  0.14.3

- Optimize locking
- Speedup collect available testcases

##  0.14.2

- Add sponsor to package

##  0.14.1

- Connection to the debugger stabilized.

##  0.14.0

- Implement inlay hints for import namespaces and parameter names
  - by default inlay hints for robotcode are only showed if you press <kbd>CONTROL</kbd>+<kbd>ALT</kbd>
  - there are 2 new settings
    `robotcode.inlayHints.parameterNames` and `robotcode.inlayHints.namespaces` where you can enable/disable the inline hints
##  0.13.28

- Remove `--language` argument if using robot < 6
  - fixes #84

##  0.13.27

- Remote Debugging

  - by installing `robotcode` via pip in your environment, you can now run the `robotcode.debugger` (see `--help` for help) from command line and attach VSCode via a remote launch config
  - more documentation comming soon.
  - closes [#86](https://github.com/d-biehl/robotcode/issues/86)

##  0.13.26

- none so far

##  0.13.25

- none so far

##  0.13.24

- The code action "Show documentation" now works for all positions where a keyword can be used or defined
- The code action "Show documentation" now respects the theme activated in VSCode. (dark, light)

##  0.13.23

- Support for Robocop >= 2.6
- Support for Tidy >= 3.3
- Speed improvements

##  0.13.22

- none so far

##  0.13.21

- none so far

##  0.13.20

- Reimplement workspace analysis
- Optimize the search for unused references

##  0.13.19

- Add a the setting `robotcode.completion.filterDefaultLanguage` to filter english language in completion, if there is another language defined for workspace or in file
- Correct naming for setting `robotcode.syntax.sectionStyle` to `robotcode.completion.headerStyle`
- Filter singular header forms for robotframework >= 6

##  0.13.18

- none so far

##  0.13.17

- Support for simple values (number, bool, str) from variable and yaml files
- Shortened representation of variable values in hover

##  0.13.16

- none so far

##  0.13.15

- none so far

##  0.13.14

- Documentation server now works also in remote and web versions of VSCode like [gitpod.io](https://gitpod.io/) and [GitHub CodeSpaces](https://github.com/features/codespaces)

##  0.13.13

- add colors to debug console
- fix resolving of ${CURDIR} in variables
- Open Documentation action now resolves variables correctly and works on resource files

##  0.13.12

- none so far

##  0.13.11

- none so far

##  0.13.10

- Correct reporting of loading built-in modules errors

##  0.13.9

- Correct analysing of "Run Keyword If"
  - fixes [#80](https://github.com/d-biehl/robotcode/issues/80)

##  0.13.8

- Support for Robocop >= 2.4
- Rework handling of launching and debugging tests
  - fixes [#54](https://github.com/d-biehl/robotcode/issues/54)
  - a launch configuration can now have a `purpose`:
    - `test`: Use this configuration when running or debugging tests.
    - `default`: Use this configuration as default for all other configurations.
- Finetuning libdoc generation and code completion
  - support for reST documentions
    - `docutils` needs to be installed
    - show documentations at library and resource import completions
- Experimental support for Source action `Open Documentation`
  - left click on a resource or library import, select Source Action and then "Open Documentation"
  - a browser opens left of the document and shows the full documentation of the library
  - works also an keyword calls
  - Tip: bind "Source Action..." to a keyboard short cut, i.e <kbd>Shift</kbd>+<kbd>Alt</kbd>+<kbd>.</kbd>

##  0.13.7

- Don't explicitly set suites to failed if there is an empty failed message
  - fixes [#76](https://github.com/d-biehl/robotcode/issues/76)

##  0.13.6

- Extensive adjustments for multiple language support for RobotFramework 5.1, BDD prefixes now works correctly for mixed languages
- New deprecated message for tags that start with hyphen, RF 5.1

##  0.13.5

- Some fixes in analysing and highlightning

##  0.13.4

- none so far

##  0.13.3

- Highlight localized robot files (RobotFramework >= 5.1)

##  0.13.2

- Support for robotidy 3.0
- References are now collected at source code analyze phase
  - this speeds up thinks like find references/renaming/highlight and so on

##  0.13.1

- Switching to LSP Client 8.0.0 requires a VSCode version >= 1.67
- Create snippets for embedded argument keywords

##  0.13.0

- Some corrections in highlightning to provide better bracket matching in arguments

##  0.12.1

- Implement API Changes for RobotTidy >= 2.2
  - fixes [#55](https://github.com/d-biehl/robotcode/issues/55)
- Switch to new LSP Protocol Version 3.17 and vscode-languageclient 8.0.0
- Disable 4SpacesTab if [GitHub CoPilot](https://copilot.github.com/) is showing inline suggestions
  - Thanks: @Snooz82

##  0.12.0

- Find references, highlight references and rename for tags
- Correct handling of keyword only arguments
- Fix the occurrence of spontaneous deadlocks

##  0.11.17

### added

- Information about possible circular imports
  - if one resource file imports another resource file and vice versa an information message is shown in source code and problems list
- References for arguments also finds named arguments

##  0.11.16

- none so far

##  0.11.15

- none so far

##  0.11.14

- none so far

##  0.11.13

- none so far

##  0.11.12

### added

- Reference CodeLenses
  - Code lenses are displayed above the keyword definitions showing the usage of the keyword
  - You can enable/disable this with the new setting `robotcode.analysis.referencesCodeLens`

##  0.11.11

### added

- Project wide code analysis
  - There are some new settings that allow to display project-wide problems:
    - `robotcode.analysis.diagnosticMode` Analysis mode for diagnostics.
      - `openFilesOnly` Analyzes and reports problems only on open files.
      - `workspace` Analyzes and reports problems on all files in the workspace.
      - default: `openFilesOnly`
    - `robotcode.analysis.progressMode` Progress mode for diagnostics.
      - `simple` Show only simple progress messages.
      - `detailed` Show detailed progress messages. Displays the filenames that are currently being analyzed.
      - default: `simple`
    - `robotcode.analysis.maxProjectFileCount` Specifies the maximum number of files for which diagnostics are reported for the whole project/workspace folder. Specifies 0 or less to disable the limit completely.
      - default: `1000`
    - `robotcode.workspace.excludePatterns` Specifies glob patterns for excluding files and folders from analysing by the language server.
- Rework loading and handling source documents
  - this speedups a lot of things like:
    - UI response
    - finding references
    - renaming of keywords and variables
    - loading reloading libraries and resources
  - When you create/rename/delete files, keywords, variables, you get an immediate response in the UI


##  0.11.10

- renaming of keywords and variables
- speedup loading of resources

##  0.11.9

### added

- Return values of keywords calls can be assigned to variables in the debugger console
  - You can call keywords in the debugger console just as you would write your keyword calls in robot files.
    Everything that starts with `'! '` (beware the space) is handled like a keyword call, for example:

    ```
    ! Log  Hello
    ```

    would call the keyword `Log` and writes `Hello` to report.

    ```
    !  Evaluate  1+2
    ```

    calls `Evaluate` and writes the result to the log.

    To assign the result of a keyword to a variable write something like

    ```
    ! ${result}  Evaluate  1+2
    ```

    This will assign the result of the expression to the variable `${result}` in the current execution context.

    A more complex example:

    ```
    ! ${a}  @{c}=  ${b}  Evaluate  "Hello World!!! How do you do?".split(' ')
    ```

    A side effect of this is that the keyword calls are logged in log.html when you continue your debug session.



##  0.11.8

### added
- Test Templates argument analysis
  - Basic usage
  - Templates with embedded arguments
  - Templates with FOR loops and IF/ELSE structures
  - see also [Robot Framework documentation](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#test-templates)

##  0.11.7

### added

- optimize restart language clients if configuration changed
- support for progress feature of language server protocol
- correct WHILE snippets
- handle invalid regular expressions in embedded keywords
- correct handling of templates with embedded arguments

##  0.11.6

- none so far

##  0.11.5

- Enable automatic publication of releases on github

##  0.11.4

- none so far

##  0.10.2

- Correct error in find variable references with invalid variables in variable section

##  0.11.3

- Fix selection range on white space

##  0.11.2

- Implement [Selection Range](https://code.visualstudio.com/docs/editor/codebasics#_shrinkexpand-selection) support for Robot Framework
  - starting from a point in the source code you can select the surrounding keyword, block (IF/WHILE,...), test case, test section and so on

##  0.11.1

- Provide better error messages if python and robot environment not matches RobotCode requirements
  - fixes [#40](https://github.com/d-biehl/robotcode/issues/40)
- Correct restart of language server client if python interpreter changed
- Correct start of root test item if `robotcode.robot.paths` is used

##  0.11.0

- Correct find references at token ends
  - If the cursor is at the end of a keyword, for example, the keyword will also be highlighted and the references will be found.

##  0.10.1

### added
- Analyse variables in documentation or metadata settings shows a hint instead of an error if variable is not found
  - fixes [#47](https://github.com/d-biehl/robotcode/issues/47)
- Correct robocop shows false "Invalid number of empty lines between sections"
  - fixes [#46](https://github.com/d-biehl/robotcode/issues/46)]

##  0.10.0

### added
- Introduce setting `robotcode.robot.paths` and correspondend launch config property `paths`
  - Specifies the paths where robot/robotcode should discover test suites. Corresponds to the 'paths' option of robot
- Introduce new RF 5 `${OPTIONS}` variable

##  0.9.6

### added

- Variable analysis, finds undefined variables
  - in variables, also inner variables like ${a+${b}}
  - in inline python expression like ${{$a+$b}}
  - in expression arguments of IF/WHILE statements like $a<$b
  - in BuiltIn keywords which contains an expression or condition argument, like `Evaluate`, `Should Be True`, `Skip If`, ...
- Improve handling of completion for argument definitions
- Support for variable files
  - there is a new setting `robotcode.robot.variableFiles` and corresponding `variableFiles` launch configuration setting
  - this corresponds to the `--variablefile` option from robot

##  0.9.5

### added

- Correct handling of argument definitions wich contains a default value from an allready defined argument

##  0.9.4

### added

- Correct handling of argument definitions wich contains a default value with existing variable with same name
- Implement "Uncaughted Failed Keywords" exception breakpoint
  - from now this is the default breakpoint, means debugger stops only if a keyword failed and it is not called from:
    - BuiltIn.Run Keyword And Expect Error
    - BuiltIn.Run Keyword And Ignore Error
    - BuiltIn.Run Keyword And Warn On Failure
    - BuiltIn.Wait Until Keyword Succeeds
    - BuiltIn.Run Keyword And Continue On Failure
  - partially fixes [#44](https://github.com/d-biehl/robotcode/issues/44)
  - speedup updating test explorers view

##  0.9.3

### added

- Introduce setting `robotcode.robot.variableFiles` and correspondend launch config property `variableFiles`
  - Specifies the variable files for robotframework. Corresponds to the '--variablefile' option of robot.
- Rework debugger termination
  - if you want to stop the current run
    - first click on stop tries to break the run like if you press <kbd>CTRL</kbd>+<kbd>c</kbd> to give the chance that logs and reports are written
    - second click stops/kill execution
- 'None' values are now shown correctly in debugger

##  0.9.2

- none so far

##  0.9.1

### added

- Rework handling keywords from resource files with duplicate names
  - also fixes [#43](https://github.com/d-biehl/robotcode/issues/43)

##  0.9.0

### added

- Optimize collecting model errors
  - also fixes [#42](https://github.com/d-biehl/robotcode/issues/42)
- Add `mode` property to launch configuration and `robotcode.robot.mode` setting for global/workspace/folder
  - define the robot running mode (default, rpa, norpa)
  - corresponds to the '--rpa', '--norpa' option of the robot module.
  - fixes [#21](https://github.com/d-biehl/robotcode/issues/21)

##  0.8.0

### added

- Introduce new version scheme to support pre-release versions of the extension
  - see [README](https://github.com/d-biehl/robotcode#using-pre-release-version)
- Rework handling VSCode test items to ensure all defined tests can be executed, also when they are ambiguous
  - see [#37](https://github.com/d-biehl/robotcode/issues/37)
- Semantic highlighting of new WHILE and EXCEPT options for RF 5.0
- Support for inline IF for RF 5.0
- Support for new BREAK, CONTINUE, RETURN statements for RF 5.0


##  0.7.0

### added

- Add `dryRun` property to launch configuration
- Add "Dry Run" and "Dry Debug" profile to test explorer
  - You can select it via Run/Debug dropdown or Right Click on the "green arrow" before the test case/suite or in test explorer and then "Execute Using Profile"
- Mark using reserved keywords like "Break", "While",... as errors
- Support for NONE in Setup/Teardowns
  - see [here](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#test-setup-and-teardown)
  - fixes [#38](https://github.com/d-biehl/robotcode/issues/38)
- Decrease size of extension package
- Sligtly correct displayName and description of VSCode package, for better relevance in Marketplace search
  - See [#39](https://github.com/d-biehl/robotcode/issues/39)

##  0.6.0

### added

- Improved variable analysis
  - In an expression like `${A+'${B+"${F}"}'+'${D}'} ${C}`, every single 'inner' variable will be recognized, you can hover over it, it can be found as reference, you can go to the definition, ...
  - Also in python expressions like `${{$a+$b}}` variables are recognized
  - Support for variables in expression in IF and WHILE statements
    - in something like `$i<5` the variables are recognized
  - Only the name of the variable is used for hovering, goto and ..., not the surrounding ${}
- Support importing variable files as module for RobotFramework 5
- Depending on selected testcase names contains a colon, a semicolon is used as separator of prerunmodifier for executing testcases
    - fixes [#20](https://github.com/d-biehl/robotcode/issues/20)
    - note: i think you should not use colons or semicolon in testcase names ;-)
- Improve Debugger
  - The debugger shows variables as inline values and when hovering, it shows the current variable value not the evaluted expression
  - Variables in the debugger are now resolved correctly and are sorted into Local/Test/Suite and Global variables
  - Fix stepping/halt on breakpoint for IF/ELSE statements if the expression is evaluated as False
  - Rework of stepping and stacktrace in the debugger
    - Only the real steps are displayed in the stack trace
- Optimize keyword matching
  - all keyword references also with embedded arguments + regex are found
  - ambigous embedded keywords are recognized correctly, also with regex
  - speed up finding keyword references
  - fix [#28](https://github.com/d-biehl/robotcode/issues/28)
  - addresses [#24](https://github.com/d-biehl/robotcode/issues/24)
- Ignoring robotcode diagnostics
  - you can put a line comment to disable robotcode diagnostics (i.e errors or warnings) for a single line, like this:

  ```robotcode
  *** Test cases ***
  first
      unknown keyword  a param   # robotcode: ignore
      Run Keyword If    ${True}
      ...    Log    ${Invalid var        # robotcode: ignore
      ...  ELSE
      ...    Unknown keyword  No  # robotcode: ignore
  ```

- Propagate import errors from resources
  - errors like: `Resource file with 'Test Cases' section is invalid` are shown at import statement
  - Note: Robocop has it's own ignore mechanism
- Initialize logging only of "--log" parameter is set from commandline
  - fixes [#30](https://github.com/d-biehl/robotcode/issues/30)
- Optimize loading of imports and collecting keywords
  - this addresses [#24](https://github.com/d-biehl/robotcode/issues/24)
  - one of the big points here is, beware of namespace pollution ;-)
- Full Support for BDD Style keywords
  - includes hover, goto, highlight, references, ...

##  0.5.5

### added

- correct semantic highlightning for "run keywords"
  - now also named arguments in inner keywords are highlighted
- correct handling of parameter names in "run keywords" and inner keywords
- correct handling of resource keywords arguments

##  0.5.4

### added

- Keyword call analysis
  - shows if parameters are missing or too much and so on...
- Highlight of named arguments
- Improve handling of command line variables when resolving variables
- Remove handling of python files to reduce the processor load in certain situations

##  0.5.3

### added

- Resolving static variables, closes [#18](https://github.com/d-biehl/robotcode/issues/18)
  - RobotCode tries to resolve variables that are definied at variables section, command line variables and builtin variables. This make it possible to import libraries/resources/variables with the correct path and parameters.
  Something like this:

  ```robotframework
  *** Settings ***
  Resource          ${RESOURCE_DIR}/some_settings.resource
  Library           alibrary    a_param=${LIB_ARG}
  Resource          ${RESOURCE_DIR}/some_keywords.resource
  ```

  - If you hover over a variable, you will see, if the variable can be resolved

- show quick pick for debug/run configuration
  - if there is no launch configuration selected and you want to run code with "Start Debugging" or "Run without Debugging", robotcode will show you a simple quick pick, where you can select a predefined configuration
- some cosmetic changes in updating Test Explorer
- correct handling of showing inline values and hover over variables in debugger
- correct handling of variable assignment with an "equal" sign
- add more regression tests

##  0.5.2

- some testing

##  0.5.1

### added

- extend README.md
  - added section about style customization
  - extend feature description
- added file icons for robot files
  - starting with VSCode Version 1.64, if the icon theme does not provide an icon for robot files, these icons are used
- add automatic debug configurations
  - you don't need to create a launch.json to run tests in the debugger view
- correct step-in FINALLY in debugger
- test explorer activates now only if there are robot files in workspace folder


##  0.5.0

### added

- Added support for RobotFramework 5.0
  - Debugger supports TRY/EXCEPT, WHILE,... correctly
  - (Semantic)- highlighter detects new statements
  - Formatter not uses internal tidy tool
  - handle EXPECT AS's variables correctly
  - Complete new statements
  - Some completion templates for WHILE, EXCEPT, ...
- Discovering tests is now more error tolerant
- Semantic tokenizing now also detects ERROR and FATAL_ERROR tokens
- some cosmetic corrections in discoring tests

note: RobotFramework 5.0 Alpha 1 has a bug when parsing the EXCEPT AS statement,
so the highlighter does not work correctly with this version.
This bug is fixed in the higher versions.

##  0.4.10

### added

- fix correct reverting documents on document close

##  0.4.9

### added

- correct CHANGELOG

##  0.4.8

### added

- extend [README](./README.md)
- extend highlight of references in fixtures and templates
- correct updating test explorer if files are deleted or reverted
- some cosmetic changes

##  0.4.7

### added

- hover/goto/references/highlight... differentiate between namespace and keyword in keyword calls like "BuiltIn.Log"
- increase test coverage

##  0.4.6
### added

- some small fixes in completion, command line parameters and variable references

##  0.4.5

### added

- correct semantic highlight of variables and settings
- completion window for keywords is now opened only after triggering Ctrl+Space or input of the first character

##  0.4.4

### added

- implement InlineValuesProvider and EvaluatableExpressionProvider in language server

##  0.4.3

### added

- implement find references for libraries, resources, variables import
- implement document highlight for variables and keywords

##  0.4.2

### added

- added support for variables import
  - completion
  - hover
  - goto
  - static and dynamic variables
- correct debugger hover on variables and last fail message
- implement find references for variables


##  0.4.1

### added

- for socket connections now a free port is used
- collect variables and arguments to document symbols
- analysing, highlighting of "Wait Until Keyword Succeeds" and "Repeat Keyword"

##  0.4.0

### added

- Big speed improvements
  - introduce some classes for threadsafe asyncio
- Implement pipe/socket transport for language server
  - default is now pipe transport
- Improve starting, stopping, restarting language server client, if ie. python environment changed, arguments changed or server crashed
- some refactoring to speedup loading and parsing documents
- semantic tokens now highlight
  - builtin keywords
  - run keywords, also nested run keywords
- analysing run keywords now correctly unescape keywords

##  0.3.2

### added

- remove deadlock in resource loading

##  0.3.1

### added

- implement find keyword references
  - closes [#13](https://github.com/d-biehl/robotcode/issues/13)
- improve parsing and analysing of "run keywords ..."
  - closes [#14](https://github.com/d-biehl/robotcode/issues/14)

##  0.3.0

### added

- remove pydantic dependency
    - closes [#11](https://github.com/d-biehl/robotcode/issues/11)
    - big refactoring of LSP and DAP types
- fix overlapping semantic tokens

##  0.2.11

### added

- fix [#10](https://github.com/d-biehl/robotcode/issues/10)
- start implementing more unit tests
- extend hover and goto for variables

##  0.2.10

### added

- extend sematic higlightning
    - builtin library keywords are declared as default_library modifier
    - higlight variables in keyword names and keyword calls
- complete embedded arguments

##  0.2.9

### added

- some correction to load libraries/resources with same name
    - fixes [#9](https://github.com/d-biehl/robotcode/issues/9)

##  0.2.8

### added

- update readme
- Added some more configuration options for log and debug messages when running tests in the debug console
- debug console now shows source and line number from log messages
- use of debugpy from vscode Python extension, no separate installation of debugpy required
- implement test tags in test controller
- implement completion, hover and goto for variables

##  0.2.7

### added

- update readme
- add run and debug menus to editor title and context menu

##  0.2.6

### added

- update readme
- semantic tokens now iterate over nodes

##  0.2.5

### added

- correct loading and closing documents/library/resources
- correct casefold in completion of namespaces

##  0.2.4

### added

- improve performance
- implement semantic syntax highlightning

##  0.2.2

### added

- integrate robotframework-tidy for formatting

## 0.2.1

### added

- improve test run messages
- add "Taks" to section completion
- add colors to test output

## 0.2.0

- Initial release


---

Check [Keep a Changelog](http://keepachangelog.com/) for recommendations on how to structure this file.
