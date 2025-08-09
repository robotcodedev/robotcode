# What is RobotCode?

**RobotCode**
Is a set of tools and extensions and plugins for working with [Robot Framework](https://robotframework.org/) in different IDEs, editors and on the command line.


**Built on Robot Framework Core**
RobotCode is based on the Robot Framework Core and uses its parser, ensuring complete compatibility and consistency. This means you get the same syntax validation, error messages, and behavior as if you were running Robot Framework directly.

**Powered by the Language Server Protocol**
RobotCode is built on the Language Server Protocol (LSP), a modern standard for implementing language support across multiple editors and IDEs. This ensures a seamless and responsive user experience, while making it easier to maintain compatibility with evolving IDE features.

**Extensions for Visual Studio Code and the IntelliJ Platform**
RobotCode is available for Visual Studio Code, IntelliJ Platform. This ensures that you can use the same features and tools across different IDEs and editors.
Because the extensions are based on the same codebase, you can expect the same level of quality and features across all platforms.
(Because it is based on the Language Server Protocol, it is also possible to use it in other editors that support the LSP, like Neovim, Sublime Text, and more.)

**Powerful Command Line Tools**
RobotCode extends the Robot Framework CLI with enhanced tools for test execution, code analysis and debugging. It supports [`robot.toml`](https://robotcode.io/03_reference/) configurations, integrates a Debug Adapter Protocol (DAP) compatible debugger, and provides an interactive REPL environment for experimenting with Robot Framework commands. Modular and flexible, these tools streamline your workflow for both development and production.

## Key Features

### Autocomplete and IntelliSense

- **Comprehensive Autocompletion:** Say goodbye to tedious typing! RobotCode provides autocompletion for libraries, resources, variables, and keywords, ensuring you always have the right tools at your fingertips. This includes support for local variables, resources, file-based variables (like Python and YAML), and command line variables, both static and dynamic.
- **Context-Aware Suggestions:** IntelliSense offers context-sensitive suggestions, helping you code faster with fewer errors. It’s perfect for those moments when you can’t quite remember the exact syntax.

![Autocomplete Libraries and Keywords](images/autocomplete1.gif)

### Code Navigation

- **Quick Symbol Navigation:** Easily move through your code with RobotCode’s symbol navigation, allowing you to jump straight to definitions, implementations, or references for keywords, variables, libraries, and resources.
- **Error and Warning Diagnostics:** Stay on top of your code quality with real-time diagnostics that highlight errors and warnings as you code, so you can fix issues before they escalate.

### Diagnostics and Linting

- **Real-Time Code Analysis:** RobotCode continuously monitors your code for syntax errors, unknown keywords, and issues with library or resource imports. This proactive approach helps you catch and resolve problems early in the development process.
- **Seamless Integration with Robot Framework:** RobotCode uses the version of Robot Framework installed in your environment for diagnostics, ensuring accuracy and consistency with your actual test runs.
- **Enhanced Linting with Robocop:** For developers who want to go further, RobotCode integrates with [Robocop](https://robocop.readthedocs.io/) to provide even more detailed analysis and linting, giving you insights into how to optimize your code.

### Code Formatting and Tidying

- **Automatic Code Formatting:** Keep your code clean and consistent with RobotCode’s formatting tools. You can choose to use the built-in `robot.tidy` tool (now deprecated) or the more powerful [Robotidy](https://robotidy.readthedocs.io/). With just a few clicks, your code is neatly organized and ready for review.
- **Customizable Formatting Options:** Tailor the formatting rules to suit your project’s needs, ensuring that your codebase remains consistent and easy to read.

### Running and Debugging

- **Integrated Testing and Debugging:** RobotCode allows you to run and debug your Robot Framework test cases directly from within Visual Studio Code. This tight integration means you can execute tests, set breakpoints, and step through code without leaving the editor.
- **Real-Time Log Navigation:** While debugging, RobotCode provides a live view of log messages in the debug console, allowing you to quickly identify and navigate to the source of any issues.

![Running Tests](images/running_tests.gif)

### Multi-root Workspace Support

- **Manage Multiple Projects Seamlessly:** With support for [Multi-root Workspaces](https://code.visualstudio.com/docs/editor/multi-root-workspaces), RobotCode allows you to work on multiple Robot Framework projects simultaneously, each with its own settings and Python environments. Whether you prefer to have separate environments or share the same one across projects, RobotCode offers the flexibility to match your workflow.
- **Smooth Workflow Transitions:** Easily switch between different projects and configurations without losing your place or context, making it easier to manage complex development environments and large codebases.

### Debug Adapter Protocol (DAP) Compatible Debugger

- **Robust Debugging Capabilities:** RobotCode integrates a Debug Adapter Protocol (DAP) compatible debugger, enabling you to debug your Robot Framework tests with ease. Set breakpoints, step through code, inspect variables, and more, all from within your favorite editor.
- Every IDE that supports the DAP can be used with RobotCode to debug Robot Framework tests.

### Robot Framework Repl and Notebooks

- **Interactive REPL Environment:** Experiment with Robot Framework commands in an interactive Read-Eval-Print Loop (REPL) environment, perfect for testing out new ideas or troubleshooting issues on the fly.
- **Jupyter Notebook-Like Experience:** Enjoy the flexibility of a Jupyter Notebook-like environment for working with Robot Framework code, allowing you to explore, test, and iterate quickly and efficiently.
(direct integration with Jupyter Notebooks is planned for a future release.)

### Command Line Tools

- **Enhanced Robot Framework CLI:** RobotCode extends the Robot Framework CLI with enhanced tools for test execution, code analysis, and debugging.

### Configure your Robot Framework environment with `robot.toml`

- **Flexible Configuration Options:** RobotCode supports the use of [`robot.toml`](https://robotcode.io/03_reference/) configuration files, allowing you to customize your Robot Framework environment with ease. Define settings for test execution in the development, production, or testing environments, and switch between configurations effortlessly.
- **Consistent Environment Management:** By using `robot.toml`, you can ensure that your Robot Framework settings are consistent across different projects and environments, reducing the risk of errors and simplifying the development process.
- **Version Control Integration:** Store your `robot.toml` files in version control systems like Git, enabling you to share configurations with your team and maintain a history of changes over time.
- **CI/CD Pipeline Integration**: Use `robot.toml` to define your test execution settings in CI/CD pipelines, ensuring that your tests run consistently across different environments and platforms.


---

**RobotCode** isn’t just a tool—it’s your coding partner. With its powerful features and seamless integration, RobotCode helps you be more productive and enjoy your coding experience. Whether you’re a seasoned Robot Framework user or just getting started, RobotCode is here to help you build, test, and deploy with confidence. Let's create something amazing together!
