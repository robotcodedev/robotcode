# Spec Delta

## Purpose

Defines how the IntelliJ plugin runs the RobotCode language server: how the server is started, connected, stopped and restarted, what the plugin hands it at start, and where its output and its cache go.

## ADDED Requirements

### Requirement: Extra arguments on the language server command line

The language server's command line SHALL carry the language server extra args as global `robotcode` options: after the `robotcode` entry point, before the plugin's own global options, and before the `language-server` subcommand. The robotcode extra args SHALL NOT appear on the language server's command line.

#### Scenario: Language server arguments

- **WHEN** the language server extra args are `--log --log-level INFO` and the language server starts
- **THEN** its command line has `--log --log-level INFO` right after the `robotcode` entry point, followed by the plugin's `--no-color` and `--no-pager` and later by `language-server`

#### Scenario: Robotcode arguments stay off the language server

- **WHEN** the robotcode extra args are `--log` and the language server extra args are empty
- **THEN** the language server's command line contains no `--log`
