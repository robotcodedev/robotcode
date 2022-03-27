# Change Log

All notable changes to the "robotcode" extension will be documented in this file.

## [Unreleased]
- none so far
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
