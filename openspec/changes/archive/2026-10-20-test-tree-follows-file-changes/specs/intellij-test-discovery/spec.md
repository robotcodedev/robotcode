## ADDED Requirements

### Requirement: Single-file rediscovery in a project with several paths

The plugin SHALL rediscover a single suite file without a full discovery also when the project has several test paths, from "Paths" on the "Robot" settings page or from `robot.toml`. The tests and tasks of the file SHALL keep their run markers, and a run from a marker SHALL run its test or task.

#### Scenario: Edit in a project with several paths

- **WHEN** `robot.toml` sets `paths = ["electron", "vscode"]` and `run-empty-suite = true`, and the user adds a test to `vscode/open_vs_code.robot`
- **THEN** one discover process runs for that file and no full discovery, and the gutter shows a run marker at the new test

#### Scenario: Run from a marker after the edit

- **WHEN** after that edit the user runs a test of `vscode/open_vs_code.robot` from its run marker
- **THEN** Robot Framework runs that one test
