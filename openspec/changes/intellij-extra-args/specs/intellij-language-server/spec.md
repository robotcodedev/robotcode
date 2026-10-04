# Spec Delta

## Purpose

Defines how the IntelliJ plugin runs the RobotCode language server: how the server is started, connected, stopped and restarted, what the plugin hands it at start, and where its output and its cache go.

## ADDED Requirements

### Requirement: Extra arguments on the language server command line

The language server's command line SHALL carry the additional language server arguments as global `robotcode` options: after the `robotcode` entry point, before the plugin's own global options, and before the `language-server` subcommand. The additional robotcode arguments SHALL NOT appear on the language server's command line.

#### Scenario: Language server arguments

- **WHEN** the additional language server arguments are `--log --log-level INFO` and the language server starts
- **THEN** its command line has `--log --log-level INFO` right after the `robotcode` entry point, followed by the plugin's `--no-color` and `--no-pager` and later by `language-server`

#### Scenario: Robotcode arguments stay off the language server

- **WHEN** the additional robotcode arguments are `--log` and the additional language server arguments are empty
- **THEN** the language server's command line contains no `--log`
