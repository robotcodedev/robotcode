# Reference

This reference provides a comprehensive resource for effectively using and configuring the `robotcode` tool in Robot Framework projects. It covers the following areas:

- [**Command Line Interface (CLI)**](cli.md): Detailed guidance on using the `robotcode` CLI to manage tasks such as test execution, code analysis, debugging, and configuration management directly from the command line. Each CLI command is explained with descriptions, options, and examples to illustrate different use cases—from running tests in continuous integration (CI) environments to debugging specific test cases in development.

- [**`robot.toml` Configuration File**](config.md): The `robot.toml` file serves as a centralized configuration for managing settings in Robot Framework projects in a structured, maintainable way. This section provides a complete guide to the available settings in `robot.toml`, including instructions on creating profiles for different environments, extending or inheriting settings, and managing variables, libraries, and dependencies across testing scenarios. With `robot.toml`, teams can efficiently handle project configurations, reduce redundancy, and simplify the setup of complex test environments.

- [**Diagnostic Modifiers**](diagnostics-modifiers.md): Explains how to control static analysis diagnostics (errors, warnings, hints) using inline `# robotcode:` comments and configuration in `robot.toml`. It covers the available modifier actions, their scope within Robot Framework files, and how global and inline settings interact across CLI, language server, and editor integrations.

- [**Analyzing Run Results**](analyzing-results.md): A task-oriented guide to the `robotcode results` family of commands — turning a finished run's `output.xml` into headline counts, per-test listings, full execution traces, tag/suite aggregations, and run-to-run diffs. Covers filtering, search, JSON-for-CI patterns, and the most common day-to-day recipes.

- [**Discovering Tests, Tasks and Suites**](discovering-tests.md): A task-oriented guide to the `robotcode discover` family of commands — turning a project's source files into a tree, flat lists, tag indexes, or a file inventory without ever executing a test. Covers Robot-native and search filters, the `TestItem` JSON schema used by editor integrations, and CI recipes for sharding, tag reports, and parse-error gates.

- [**Interactive Robot Framework REPL**](repl.md): A task-oriented guide to the `robotcode repl` command — a live keyword-driven shell for exploring libraries, prototyping snippets, debugging keyword behaviour and capturing ad-hoc sessions as a normal `output.xml` / `log.html`. Covers the prompt model, state persistence, file-execution and `--inspect` mode, output capture, and recipes for library exploration and CI smoke checks.

Together, these sections provide the knowledge needed to fully customize `robotcode` for a flexible and efficient testing workflow.
