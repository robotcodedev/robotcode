# Reference

This reference provides a comprehensive resource for effectively using and configuring the `robotcode` tool in Robot Framework projects. It covers the following areas:

- [**Command Line Interface (CLI)**](cli.md): Detailed guidance on using the `robotcode` CLI to manage tasks such as test execution, code analysis, debugging, and configuration management directly from the command line. Each CLI command is explained with descriptions, options, and examples to illustrate different use cases—from running tests in continuous integration (CI) environments to debugging specific test cases in development.

- [**`robot.toml` Configuration File**](config.md): The `robot.toml` file serves as a centralized configuration for managing settings in Robot Framework projects in a structured, maintainable way. This section provides a complete guide to the available settings in `robot.toml`, including instructions on creating profiles for different environments, extending or inheriting settings, and managing variables, libraries, and dependencies across testing scenarios. With `robot.toml`, teams can efficiently handle project configurations, reduce redundancy, and simplify the setup of complex test environments.

- [**Diagnostic Modifiers**](diagnostics-modifiers.md): Explains how to control static analysis diagnostics (errors, warnings, hints) using inline `# robotcode:` comments and configuration in `robot.toml`. It covers the available modifier actions, their scope within Robot Framework files, and how global and inline settings interact across CLI, language server, and editor integrations.

- [**Analyzing Code**](analyzing-code.md): A task-oriented guide to the `robotcode analyze code` command — static analysis of a Robot Framework project without executing it. Covers the diagnostics it reports, severity remapping, exit codes and masks, the human-readable and machine-readable output formats (JSON, SARIF, GitHub annotations, GitLab Code Quality), and CI recipes for code scanning and build gating.

- [**Analyzing Run Results**](analyzing-results.md): A task-oriented guide to the `robotcode results` family of commands — turning a finished run's `output.xml` into headline counts, per-test listings, full execution traces, tag/suite aggregations, and run-to-run diffs. Covers filtering, search, JSON-for-CI patterns, and the most common day-to-day recipes.

- [**Discovering Tests, Tasks and Suites**](discovering-tests.md): A task-oriented guide to the `robotcode discover` family of commands — turning a project's source files into a tree, flat lists, tag indexes, or a file inventory without ever executing a test. Covers Robot-native and search filters, the `TestItem` JSON schema used by editor integrations, and CI recipes for sharding, tag reports, and parse-error gates.

- [**Interactive Robot Framework REPL**](repl.md): A task-oriented guide to the `robotcode repl` command — a live keyword-driven shell for exploring libraries, prototyping snippets, debugging keyword behaviour and capturing ad-hoc sessions as a normal `output.xml` / `log.html`. Covers the prompt model, state persistence, file-execution and `--inspect` mode, output capture, and recipes for library exploration and CI smoke checks. Also covers the built-in `pdb`-style **command-line debugger** (`robotcode robot-debug`) — breakpoints, stepping, the call stack, per-frame variables, and source listing.

- [**Working with AI Agents**](ai-agents.md): How **RobotCode** lets AI coding agents (GitHub Copilot Chat, Claude Code, Codex, and other Open-Plugins-compatible tools) work through the project's own `robotcode` CLI instead of guessing. Covers the bundled VS Code chat plugin and its toggle, installing the plugin in other agents via the marketplace, what the agent is taught to do (discover, libdoc, REPL, results, analyze on the resolved project), and the CLI's AI-agent detection that keeps captured terminal output clean.

Together, these sections provide the knowledge needed to fully customize `robotcode` for a flexible and efficient testing workflow.
