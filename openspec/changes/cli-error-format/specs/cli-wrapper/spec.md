## MODIFIED Requirements

### Requirement: Debug and REPL servers report an error of the configuration after they start

When the configuration of `debug` or `repl-server` cannot be loaded, the command SHALL start its server as it does without the error and SHALL report the error once: `debug` in its debug session, before the session ends, and `repl-server` after its server has started.

#### Scenario: Debug session with a profile that does not exist

- **WHEN** `robotcode -p typo debug --no-wait-for-client` runs in a project that defines no profile `typo`
- **THEN** robotcode starts the debug server, shows `[ ERROR ] No profile matches 'typo'.` once before the session ends, and exits with 252

#### Scenario: REPL server with a profile that does not exist

- **WHEN** `robotcode -p typo repl-server` runs in a project that defines no profile `typo`
- **THEN** robotcode starts the REPL server, shows `[ ERROR ] No profile matches 'typo'.` once and exits with 252
