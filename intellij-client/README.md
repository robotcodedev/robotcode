# RobotCode - The Ultimate Robot Framework Toolset

[![JetBrains Marketplace](https://img.shields.io/jetbrains/plugin/v/26216.svg)](https://plugins.jetbrains.com/plugin/26216)
[![Downloads](https://img.shields.io/jetbrains/plugin/d/26216.svg)](https://plugins.jetbrains.com/plugin/26216)


<!-- Plugin description -->

**Robot Framework support for PyCharm and the IntelliJ Platform.** Build and maintain your test automation and RPA projects in an IDE that understands Robot Framework, from your first keyword to suites that whole teams work on.

## Features

- **Completion** of keywords, arguments, variables, imports, settings and control structures, and parameter info for the arguments of a keyword call.
- **Documentation** of keywords, libraries and resource files on hover and with Quick Documentation.
- **Navigation** to declarations and usages, with the Structure view, breadcrumbs and Go to Symbol.
- **Highlighting by meaning**, adjustable for each kind of element in the color scheme settings.
- **Diagnostics while you type**: keywords and variables that cannot be found, wrong arguments, imports that fail and more, in the open files or in the whole project. With [Robocop](https://robocop.dev/) installed, its findings appear next to RobotCode's.
- **Quick fixes and refactorings**: create a missing keyword or variable, surround steps with `TRY`/`EXCEPT`, extract a keyword, and rename keywords and variables across the project.
- **Formatting** with Robocop's formatter.
- **Running** tests, tasks and suites from the run markers in the editor, from context menus and from run configurations, which also have PyCharm's Python options such as `.env` files.
- **A results tree** for each run, with the log messages and failures of each test, **Rerun Failed Tests**, and the report and log in a built-in preview or a browser.
- **Debugging** with breakpoints, conditions, hit counts and logpoints, stopping at failures, stepping, variables, watches and evaluating keywords and variables while the run is paused, and, with **Attach Python**, of the Python code of libraries in a second session of PyCharm's Python debugger.
- **`robot.toml` configuration**: RobotCode reads the same [`robot.toml`](https://robotcode.io/guides/robot-toml/) in PyCharm, in VS Code and on the command line, so a run in the IDE and a run in CI see the same options. Select its configuration profiles for the project, or run once with another profile.

RobotCode is built on Robot Framework's own parser and developed in close collaboration with the Robot Framework Core team. It is also available for VS Code and as command line tools; [RobotCode in PyCharm and VS Code](https://robotcode.io/guides/pycharm/compared-with-vscode/) compares the plugin with the VS Code extension.

## Requirements

- PyCharm or IntelliJ IDEA 2026.1 or newer; IntelliJ IDEA needs its Python plugin. Other IDEs of the IntelliJ Platform with the Python plugin should work as well, but are not tested.
- A local Python interpreter for the project with Python 3.10 or newer and Robot Framework 5.0 or newer, and Robocop if you want to use it; RobotCode brings its own tools along. Remote interpreters, such as WSL, Docker or SSH, are not supported yet.
- The plugin [LSP4IJ](https://plugins.jetbrains.com/plugin/23257), through which PyCharm talks to RobotCode's language server.

## Getting Started

1. Install RobotCode under **Settings | Plugins | Marketplace**, and LSP4IJ if PyCharm does not install it along, and restart the IDE when it asks you to. Disable other Robot Framework plugins, such as IntelliBot; they do not work together with RobotCode.
2. Open your project and choose a Python interpreter with Robot Framework for it under **Settings | Python | Interpreter**.
3. Open a `.robot` file, or create one with **File | New... | Robot Framework File**; a new suite file starts with a sample test. If the interpreter does not fit, a banner above the file says why.
4. Click the run marker beside a test and choose **Run**.

[Get Started with PyCharm](https://robotcode.io/getting-started/pycharm/) explains these steps in detail, [Configure Your Project](https://robotcode.io/getting-started/configuration/) creates a first `robot.toml` for your project, and the [PyCharm guide](https://robotcode.io/guides/pycharm/) shows how to work with RobotCode in PyCharm.

## Feedback

Report bugs and suggest features in the [issue tracker](https://github.com/robotcodedev/robotcode/issues), and ask questions in the [Discussions](https://github.com/robotcodedev/robotcode/discussions) or in `#robotcode` on the [Robot Framework Slack](https://slack.robotframework.org/).

<!-- Plugin description end -->

## Installation

- **In the IDE:** <kbd>Settings</kbd> > <kbd>Plugins</kbd> > <kbd>Marketplace</kbd> > search for "RobotCode" > <kbd>Install</kbd>.
- **From the [JetBrains Marketplace](https://plugins.jetbrains.com/plugin/26216):** click <kbd>Install to ...</kbd> while your IDE is running, or download a [version](https://plugins.jetbrains.com/plugin/26216/versions) and install it with <kbd>Settings</kbd> > <kbd>Plugins</kbd> > <kbd>⚙️</kbd> > <kbd>Install Plugin from Disk...</kbd>.
- **From GitHub:** download `robotcode4ij-<version>.zip` from the [latest release](https://github.com/robotcodedev/robotcode/releases/latest) and install it with <kbd>Install Plugin from Disk...</kbd>.

## License

This project is licensed under the [Apache 2.0 License](https://spdx.org/licenses/Apache-2.0.html).

## Powered by
[![JetBrains logo.](../docs/src/assets/logos/jetbrains.svg)](https://jb.gg/OpenSourceSupport)
