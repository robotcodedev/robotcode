---
description: The About page of the RobotCode documentation.

---
# About


[![Visual Studio Marketplace](https://img.shields.io/visual-studio-marketplace/v/d-biehl.robotcode?style=flat&label=VS%20Marketplace&logo=visual-studio-code)](https://marketplace.visualstudio.com/items?itemName=d-biehl.robotcode)
[![Installs](https://img.shields.io/visual-studio-marketplace/i/d-biehl.robotcode?style=flat)](https://marketplace.visualstudio.com/items?itemName=d-biehl.robotcode)
[![Build Status](https://img.shields.io/github/actions/workflow/status/robotcodedev/robotcode/build-test-package-publish.yml?branch=main&style=flat&logo=github)](https://github.com/robotcodedev/robotcode/actions?query=workflow:build_test_package_publish)
[![License](https://img.shields.io/github/license/robotcodedev/robotcode?style=flat&logo=apache)](https://github.com/robotcodedev/robotcode/blob/master/LICENSE)
[![PyPI - Version](https://img.shields.io/pypi/v/robotcode.svg?style=flat)](https://pypi.org/project/robotcode)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/robotcode.svg?style=flat)](https://pypi.org/project/robotcode)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/robotcode.svg?style=flat&label=downloads)](https://pypi.org/project/robotcode/)

----

[[toc]]

An [extension](https://marketplace.visualstudio.com/VSCode) which brings support for [RobotFramework](https://robotframework.org/)
to [Visual Studio Code](https://code.visualstudio.com/), including [features](#features) like code completion, debugging, test explorer, refactoring and more!

## Features

With RobotCode you can edit your code with auto-completion, code navigation, syntax checking and many more.
Here is a list of Features:

- [Autocomplete and IntelliSense](#Autocomplete-and-IntelliSense)
- [Code Navigation](#code-navigation)
- [Diagnostics and Linting](#diagnostics-and-linting)
- [Code Formatting](#code-formatting)
- [Running and Debugging](#running-and-debugging)
- [Multi-root Workspace folders](#multi-root-workspace-folders)
- Find implementations and references of keywords, variables, libraries, resource and variable files
  - Show codelenses for keyword definitions
- Test Explorer
- Refactorings
  - renaming keywords, variables, tags

### Autocomplete and IntelliSense

Autocompletion for:
- Libraries with parameters
- Resources,
- Variables
- Keywords with parameters
- Namespaces

![Autocomplete Libraries and Keywords](./../images/autocomplete1.gif)

Autocompletion supports all supported variables types
  - local variables
  - variables from resource files
  - variables from variables file (.py and .yaml)
    - static and dynamic
  - command line variables
  - builtin variables

![Autocomplete Variables](./../images/autocomplete2.gif)

### Code Navigation

- Symbols
- Goto definitions and implementations
  - Keywords
  - Variables
  - Libraries
  - Resources
- Find references
  - Keywords
  - Variables
  - Imports
    - Libraries
    - Resources
    - Variables
  - Tags
- Errors and Warnings

### Diagnostics and Linting

RobotCode analyse your code and show diagnostics for:

- Syntax Errors
- Unknown keywords
- Duplicate keywords
- Missing libraries, resource and variable imports
- Duplicate libraries, resource and variable imports
- ... and many more

For most things RobotCode uses the installed RobotFramework version to parse and analyse the code, so you get the same errors as when you run it.


Get additional code analysis with [Robocop](https://robocop.readthedocs.io/). Just install it in your python environment.

### Code Formatting

RobotCode can format your code with the internal RobotFramework robot.tidy tool (deprecated), but also with [Robotidy](https://robotidy.readthedocs.io/). Just install it.

### Running and Debugging

RobotCode supports running and debugging of RobotFramework testcases and tasks out of the box, directly from the definition of the test or suite.

![Running Tests](./../images/running_tests.gif)

In the debug console you can see all log messages of the current run and navigate to the keyword the message was written by.

### Multi-root Workspace folders

RobotCodes support for [Multi-root Workspaces](https://code.visualstudio.com/docs/editor/multi-root-workspaces), enables loading and editing different Robotframework projects/folders with different RobotFramework/Python environments and settings at the same time or you can share the same RobotFramework/Python environment and settings for all folders in the workspace.
