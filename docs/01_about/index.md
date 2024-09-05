# What is RobotCode?

**RobotCode** is your all-in-one extension for working with the [Robot Framework](https://robotframework.org/) in [Visual Studio Code](https://code.visualstudio.com/). Whether you're writing, testing, or debugging, RobotCode provides a comprehensive toolkit that makes every aspect of your development process smoother and more efficient.

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

### Code Formatting

- **Automatic Code Formatting:** Keep your code clean and consistent with RobotCode’s formatting tools. You can choose to use the built-in `robot.tidy` tool (now deprecated) or the more powerful [Robotidy](https://robotidy.readthedocs.io/). With just a few clicks, your code is neatly organized and ready for review.
- **Customizable Formatting Options:** Tailor the formatting rules to suit your project’s needs, ensuring that your codebase remains consistent and easy to read.

### Running and Debugging

- **Integrated Testing and Debugging:** RobotCode allows you to run and debug your Robot Framework test cases directly from within Visual Studio Code. This tight integration means you can execute tests, set breakpoints, and step through code without leaving the editor.
- **Real-Time Log Navigation:** While debugging, RobotCode provides a live view of log messages in the debug console, allowing you to quickly identify and navigate to the source of any issues.

![Running Tests](images/running_tests.gif)

### Multi-root Workspace Support

- **Manage Multiple Projects Seamlessly:** With support for [Multi-root Workspaces](https://code.visualstudio.com/docs/editor/multi-root-workspaces), RobotCode allows you to work on multiple Robot Framework projects simultaneously, each with its own settings and Python environments. Whether you prefer to have separate environments or share the same one across projects, RobotCode offers the flexibility to match your workflow.
- **Smooth Workflow Transitions:** Easily switch between different projects and configurations without losing your place or context, making it easier to manage complex development environments and large codebases.

---

**RobotCode** isn’t just a tool—it’s your coding partner. With its powerful features and seamless integration, RobotCode helps you be more productive and enjoy your coding experience. Whether you’re a seasoned Robot Framework user or just getting started, RobotCode is here to help you build, test, and deploy with confidence. Let's create something amazing together!
