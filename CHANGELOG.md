# Change Log

All notable changes to the "robotcode" extension will be documented in this file.

## [Unreleased]

### added
- remove pydantic dependency 
    - closes [#11](https://github.com/d-biehl/robotcode/issues/11)
    - big refactoring of LSP and DAP types
    

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
