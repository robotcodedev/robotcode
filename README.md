# Robot Code Readme

Language Server and client for Visual Studio Code.

## Requirements

* Python 3.8 or above
* Robotframework 3.2 and above

## Installation

At the moment, it is only possible to install the vsix manually in VSCode.
Download the vscode-package artifact from the latest [CI/Actions](https://github.com/d-biehl/robotcode/actions/workflows/build.yml) run and install the containing vsix file manually in VSCode.

## Features

* Syntax Highlighting
    * Semantic highlighting (comming soon)
* Syntax Analysis
    * also for 'run keyword(s) (if/unless/...)'
    * live updating if library or resources changed    
* Code Completion
    * Headers
    * Settings
    * Keywords
* Signature Help
* Goto Definition
* Folding
* Hover Information
* Loading Library/Resources with support for builtin variables
* Integrate 'Robocop' tool static code analysis of Robot Framework code.
    * https://github.com/MarketSquare/robotframework-robocop


... more comming soon
