# Spec Delta

## MODIFIED Requirements

### Requirement: Troubleshooting AI agents

Troubleshooting SHALL describe, by symptom, what helps when the agent answers without `robotcode`, loads `robotcode` although another skill fits better or skips it although it fits, uses another environment than the project's, re-runs a failing test or uses the REPL instead of debugging it, writes a test when it was asked to try something out, or when the plugin from the marketplace behaves differently from the one in VS Code.

#### Scenario: Agent answers without robotcode
- **WHEN** a reader looks up why the agent answers from general knowledge
- **THEN** the page says to name the subject or the skill `robotcode` in the request, and in VS Code to check `robotcode.ai.enableChatPlugins`

#### Scenario: Agent picks the wrong skill
- **WHEN** a reader looks up why the agent loads `robotcode` although another skill fits better, or skips it although it fits
- **THEN** the page says that agents choose from a list of skills of limited size, and that descriptions in it can be shortened or dropped when it overflows
- **AND** the page says what helps: naming the skill in the request, removing or turning off skills that aren't needed and, where the agent allows it, raising the limit
- **AND** the page describes this for agents in general, with Claude Code only as an example
