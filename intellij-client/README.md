# robotcode4ij

[![JETBRAINS Marketplace](https://img.shields.io/jetbrains/plugin/v/26216.svg)](https://plugins.jetbrains.com/plugin/26216)
[![Downloads](https://img.shields.io/jetbrains/plugin/d/26216.svg)](https://plugins.jetbrains.com/plugin/26216)


<!-- Plugin description -->

**RobotCode** is a PyCharm/IntelliJ Plugin that enhances your workflow
with [Robot Framework](https://robotframework.org/).
It provides a rich set of features to help you write, run, and debug your Robot Framework tests directly within your
IDE.

⚠️ **Important Notice** ⚠️
This plugin is currently under active development and is not yet ready for production use. Please note that it may
contain bugs or lack certain features.

We invite you to join the Robot Framework and RobotCode community by reporting issues, suggesting features, and helping
us improve the plugin.

Your feedback is greatly appreciated! 🙂

## Why RobotCode?

**Built on Robot Framework Core**
RobotCode is based on the Robot Framework Core and uses its parser, ensuring complete compatibility and consistency.
This means you get the same syntax validation, error messages, and behavior as if you were running Robot Framework
directly.

**Powered by the Language Server Protocol**
RobotCode is built on the Language Server Protocol (LSP), a modern standard for implementing language support across
multiple editors and IDEs. This ensures a seamless and responsive user experience, while making it easier to maintain
compatibility with evolving IDE features.

**Powerful Command Line Tools**
RobotCode extends the Robot Framework CLI with enhanced tools for test execution, analysis, and debugging. It supports [
`robot.toml`](https://robotcode.io/03_reference/) configurations, integrates a Debug Adapter Protocol (DAP) compatible
debugger, and provides an interactive REPL environment for experimenting with Robot Framework commands. Modular and
flexible, these tools streamline your workflow for both development and production.

## Key Features

- **Smart Code Editing**: Auto-completion, syntax highlighting, and seamless navigation.
- **Refactoring**: Easily rename variables, keywords, and arguments across your project.
- **Integrated Debugging**: Debug Robot Framework tests directly within the IDE.
- **Test Management**: Discover, run, and monitor Robot Framework tests without leaving your IDE.
- **Rich Test Reports**: View detailed test results and logs directly in the IDE.
- **Code Analysis**: Leverage tools like [Robocop](https://robocop.readthedocs.io/) for linting and static code
  analysis.
- **Formatting Made Easy**: Use [Robotidy](https://robotidy.readthedocs.io/) for consistent code formatting.
- **Support for `robot.toml`**: Manage your Robot Framework projects with ease.
- **More Features Coming Soon!**

## Requirements

- Python 3.8 or newer
- Robot Framework 4.1 or newer
- PyCharm 2024.3.1 or newer

## Getting Started

1. Install the [RobotCode Plugin](https://plugins.jetbrains.com/plugin/26216) from the JETBRAINS Marketplace.
2. Configure your Robot Framework Python environment
3. Start writing and running your Robot Framework tests!

(Comming soon...)
For a more detailed guide, check out the [Let's get started](https://robotcode.io/02_get_started/) Guide on
the [RobotCode](https://robotcode.io) website.

<!-- Plugin description end -->

## Installation

- Using the IDE built-in plugin system:

  <kbd>Settings/Preferences</kbd> > <kbd>Plugins</kbd> > <kbd>Marketplace</kbd> > <kbd>Search for "RobotCode"</kbd> >
  <kbd>Install</kbd>

- Using JetBrains Marketplace:

  Go to [JetBrains Marketplace](https://plugins.jetbrains.com/plugin/26216) and install it by clicking the <kbd>Install
  to ...</kbd> button in case your IDE is running.

  You can also download the [latest release](https://plugins.jetbrains.com/plugin/26216/versions) from JetBrains
  Marketplace and install it manually using
  <kbd>Settings/Preferences</kbd> > <kbd>Plugins</kbd> > <kbd>⚙️</kbd> > <kbd>Install plugin from disk...</kbd>

- Manually:

  Download the [latest release](https://github.com/robotcodedev/robotcode/releases/latest) and install it manually using
  <kbd>Settings/Preferences</kbd> > <kbd>Plugins</kbd> > <kbd>⚙️</kbd> > <kbd>Install plugin from disk...</kbd>
