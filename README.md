
# RobotCode - Language Support for Robot Framework in Visual Studio Code

[![License](https://img.shields.io/github/license/robotcodedev/robotcode?style=flat&logo=apache)](https://github.com/robotcodedev/robotcode/blob/master/LICENSE)
[![Build Status](https://img.shields.io/github/actions/workflow/status/robotcodedev/robotcode/build-test-package-publish.yml?branch=main&style=flat&logo=github)](https://github.com/robotcodedev/robotcode/actions?query=workflow:build_test_package_publish)

[![VS Code Marketplace](https://img.shields.io/visual-studio-marketplace/v/d-biehl.robotcode?style=flat&label=VS%20Marketplace&logo=visual-studio-code)](https://marketplace.visualstudio.com/items?itemName=d-biehl.robotcode)
[![Installs](https://img.shields.io/visual-studio-marketplace/i/d-biehl.robotcode?style=flat)](https://marketplace.visualstudio.com/items?itemName=d-biehl.robotcode)

[![JETBRAINS Marketplace](https://img.shields.io/jetbrains/plugin/v/26216.svg)](https://plugins.jetbrains.com/plugin/26216)
[![Downloads](https://img.shields.io/jetbrains/plugin/d/26216.svg)](https://plugins.jetbrains.com/plugin/26216)


[![PyPI - Version](https://img.shields.io/pypi/v/robotcode.svg?style=flat)](https://pypi.org/project/robotcode)
[![Python Version](https://img.shields.io/pypi/pyversions/robotcode.svg?style=flat)](https://pypi.org/project/robotcode)
[![Downloads](https://img.shields.io/pypi/dm/robotcode.svg?style=flat&label=downloads)](https://pypi.org/project/robotcode)

---

**RobotCode** is a Visual Studio Code extension that enhances your workflow with [Robot Framework](https://robotframework.org/).
It provides a rich set of features to help you write, run, and debug your Robot Framework tests directly within Visual Studio Code.

## Why RobotCode?

**Built on Robot Framework Core**
RobotCode is based on the Robot Framework Core and uses its parser, ensuring complete compatibility and consistency. This means you get the same syntax validation, error messages, and behavior as if you were running Robot Framework directly.

**Powered by the Language Server Protocol**
RobotCode is built on the Language Server Protocol (LSP), a modern standard for implementing language support across multiple editors and IDEs. This ensures a seamless and responsive user experience, while making it easier to maintain compatibility with evolving IDE features.

**Powerful Command Line Tools**
RobotCode extends the Robot Framework CLI with enhanced tools for test execution, analysis, and debugging. It supports [`robot.toml`](https://robotcode.io/03_reference/) configurations, integrates a Debug Adapter Protocol (DAP) compatible debugger, and provides an interactive REPL environment for experimenting with Robot Framework commands. Modular and flexible, these tools streamline your workflow for both development and production.

## Key Features

- **Code Editing**: Enjoy code auto-completion, navigation and more.
- **IntelliSense**: Get code completion suggestions for keywords, variables, and more.
- **Refactoring**: Rename variables, keywords, arguments and more with ease and project wide.
- **Enhanced Syntax Highlighting**: Easily identify and read your Robot Framework code with support highlight embedded arguments, python expressions, environment variables with default values, and more.
- **Code Snippets**: Quickly insert common Robot Framework code snippets.
- **Test Discovery**: Discover and run Robot Framework test cases directly within VS Code.
- **Test Execution**: Execute Robot Framework test cases and suites directly within VS Code.
- **Test Reports**: View test reports directly within VS Code.
- **Debugging**: Debug your Robot Framework tests with ease.
- **Command Line Tools**: A wide array of tools to assist in setting up and managing Robot Framework environments.
- **Code Analysis with Robocop**: Install [Robocop](https://robocop.readthedocs.io/) for additional code analysis.
- **Code Formatting**: Format your code using Robot Framework’s built-in tools like `robot.tidy` or [Robotidy](https://robotidy.readthedocs.io/).
- **Multi-root Workspace Support**: Manage multiple Robot Framework projects with different Python environments simultaneously.
- **Customizable Settings**: Configure the extension to fit your needs.
- **RobotCode Repl and Notebooks**: Play with Robot Framework in a Jupyter Notebook-like environment.
- **And More!**: Check out the [official documentation](https://robotcode.io) for more details.

## Requirements

- Python 3.8 or newer
- Robot Framework 4.1 or newer
- Visual Studio Code 1.86 or newer

## Getting Started

1. Install the [RobotCode extension](https://marketplace.visualstudio.com/items?itemName=d-biehl.robotcode) from the Visual Studio Marketplace.
2. Configure your Robot Framework environment with the command-line tools provided by the extension.
3. Start writing and running your Robot Framework tests!

For a more detailed guide, check out the [Let's get started](https://robotcode.io/02_get_started/) Guide on the [RobotCode](https://robotcode.io) website.

## Extensions

RobotCode automatically installs the [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python) and the [Python Debugger](https://marketplace.visualstudio.com/items?itemName=ms-python.debugpy) extension. Additional extensions may be required depending on your project needs.

## Documentation

For more details on installation, setup, and usage, refer to the [official RobotCode documentation](https://robotcode.io).

## License

This project is licensed under the [Apache 2.0 License](https://spdx.org/licenses/Apache-2.0.html).
