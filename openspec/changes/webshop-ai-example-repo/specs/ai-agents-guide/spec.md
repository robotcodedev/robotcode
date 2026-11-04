# Spec Delta

## ADDED Requirements

### Requirement: The example project is public

The example project of the sessions SHALL be public in the repository `robotcodedev/webshop-ai-example`, in the state the sessions start from, and the overview of Working with the Agent and Briefing the Agent SHALL link to it.

#### Scenario: Finding the code
- **WHEN** a reader opens `/guides/ai-agents/working-with-the-agent/` or `/guides/ai-agents/briefing/`
- **THEN** the page links to `robotcodedev/webshop-ai-example`

#### Scenario: Differences from the recordings
- **WHEN** a reader opens `/guides/ai-agents/working-with-the-agent/`
- **THEN** the page says that some things in the example project are wrong on purpose and that its CI workflow only starts by hand there, unlike in the sessions

#### Scenario: Running it from a clean clone
- **WHEN** a reader clones the repository and follows its README
- **THEN** `robotcode robot` runs 13 tests, of which only `Login Works` fails
- **AND** `robotcode analyze code` reports the unknown keyword `Submit Ordr`
- **AND** `robotcode session` is available

#### Scenario: The README doesn't give the answers
- **WHEN** an agent working in the repository reads its README
- **THEN** the README says that some things are wrong on purpose, without naming them

#### Scenario: A push runs no tests
- **WHEN** someone pushes to the repository
- **THEN** no workflow starts, and the workflow in `.github/workflows/tests.yml` can be started by hand
