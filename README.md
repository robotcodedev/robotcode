# RobotCode - The Ultimate Robot Framework Toolset

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

## What is RobotCode?

RobotCode is a comprehensive toolkit for Robot Framework development, offering advanced features to enhance your productivity and streamline your workflow. Whether you're using Visual Studio Code, IntelliJ, or other LSP-compatible editors, RobotCode ensures a consistent and seamless experience.

### Key Advantages:

- **Built on Robot Framework Core**
  RobotCode uses Robot Framework's native parser for syntax validation, error messages, and behavior, ensuring full compatibility and reliability in your projects.

- **Powered by the Language Server Protocol (LSP)**
  By leveraging the LSP, RobotCode provides real-time code navigation, intelligent auto-completion, and refactoring capabilities across various editors and IDEs.

- **Multi-Platform IDE Extensions**
  RobotCode offers robust extensions for Visual Studio Code and IntelliJ Platform, delivering the same high-quality features regardless of your preferred development environment. Thanks to LSP, it also works with editors like Neovim and Sublime Text.

- **Enhanced CLI Tools**
  Extend Robot Framework's command-line capabilities with tools for test execution, debugging, and code analysis. Features include `robot.toml` support, a Debug Adapter Protocol (DAP) debugger, and an interactive REPL for quick experimentation.

With RobotCode, you can focus on building and testing your automation workflows while enjoying an integrated and efficient development experience.


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

### IDE Support

- Visual Studio Code 1.86 or newer
- PyCharm 2024.3.2 or newer or IntelliJ IDEA 2024.3.2 or newer


## Getting Started

### Visual Studio Code

1. **Install the RobotCode Extension**
   Open the [Visual Studio Marketplace](https://marketplace.visualstudio.com/items?itemName=d-biehl.robotcode) and install the RobotCode extension.

2. **Set Up Your Environment**
   Configure your Robot Framework environment using the tools and commands provided by the extension or the `robot.toml` file.

3. **Start Testing**
   Begin writing and running your Robot Framework tests directly in VS Code.

4. **Explore More**
   Visit the [Getting Started Guide](https://robotcode.io/02_get_started/) for detailed setup instructions and advanced features.

**Extensions:**
RobotCode automatically installs the [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python) and the [Python Debugger](https://marketplace.visualstudio.com/items?itemName=ms-python.debugpy) extension. Additional extensions may be required depending on your project needs.


### IntelliJ IDEA or PyCharm

1. **Install the RobotCode Plugin**
   Choose one of the following methods to install the RobotCode plugin in your IDE:

   - **Install via the Built-in Plugin Marketplace**
      Navigate to:
      <kbd>Settings/Preferences</kbd> > <kbd>Plugins</kbd> > <kbd>Marketplace</kbd> > Search for "RobotCode" and click <kbd>Install</kbd>.

   - **Use the JetBrains Marketplace**
      Alternatively, install the plugin directly from the [JetBrains Marketplace](https://plugins.jetbrains.com/plugin/26216). Click the <kbd>Install to ...</kbd> button if your IDE is running.

   - **Manual Installation**
      Download the [latest release](https://github.com/robotcodedev/robotcode/releases/latest) and install it manually:
      <kbd>Settings/Preferences</kbd> > <kbd>Plugins</kbd> > <kbd>⚙️</kbd> > <kbd>Install plugin from disk...</kbd>.

2. **Set Up Your Environment**
   Configure your Robot Framework environment using the tools and commands provided by the plugin or the `robot.toml` file.

3. **Start Testing**
   Begin developing and executing your Robot Framework tests.

4. **Explore More**
   Visit the [Getting Started Guide](https://robotcode.io/02_get_started/) for detailed setup instructions and advanced features.

**Plugins:**
RobotCode automatically installs the [LSP4IJ](https://plugins.jetbrains.com/plugin/23257). Additional plugins may be required depending on your project needs.


## Documentation

For detailed instructions, visit our **[official documentation](https://robotcode.io)**.
Here are some additional resources to help you troubleshoot or learn more:

- **[Q&A](https://github.com/robotcodedev/robotcode/discussions/categories/q-a):** Answers to common questions about RobotCode.
- **[Troubleshooting Guide](https://robotcode.io/04_tip_and_tricks/troubleshooting):** Solutions for setup issues, performance problems, and debugging errors.
- **[Command Line Tools Reference](https://robotcode.io/03_reference/):** Comprehensive documentation on using RobotCode’s CLI tools.
- **[Changelog](https://github.com/robotcodedev/robotcode/blob/main/CHANGELOG.md):** Track changes, updates, and new features in each release.
- **[Support](https://robotcode.io/support/):** Learn how to get help and report issues.


## License

This project is licensed under the [Apache 2.0 License](https://spdx.org/licenses/Apache-2.0.html).

---

## Powered by
[![JetBrains logo.](docs/images/jetbrains.png)](https://jb.gg/OpenSourceSupport)
