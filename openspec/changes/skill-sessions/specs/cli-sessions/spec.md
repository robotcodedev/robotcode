# Spec Delta

## ADDED Requirements

### Requirement: Sandboxes in the guide on sessions

The guide on sessions SHALL say that sessions work without any setting when the whole agent runs in one sandbox, such as a container, a dev container or a virtual machine, and that nothing outside that sandbox sees them. It SHALL say that they don't work where each command of an agent has a sandbox of its own, and what an agent does there instead. It SHALL NOT describe settings or rules that lead out of a sandbox or open it.

#### Scenario: One sandbox around the whole agent
- **WHEN** a reader looks up whether sessions work in a container
- **THEN** the guide says that they work without any setting and that an agent's own sandbox for each command has to be off in there

#### Scenario: A sandbox for each command
- **WHEN** a reader looks up why `session start` exits with code 252 in the sandbox of an agent
- **THEN** the guide says that a session can't outlive the command that started it there, and that an agent with a tool that writes to a running command drives `robotcode repl` or `robotcode robot-debug` in its terminal

#### Scenario: What was checked
- **WHEN** a reader looks up on which systems this holds
- **THEN** the guide names Linux and Windows and says that macOS is not checked
