# Spec Delta

## ADDED Requirements

### Requirement: What is in effect under a profile

The skill SHALL send an agent to `robotcode [-p <name>] profiles show` for what is in effect under a profile, and SHALL describe `robotcode config show` as the configuration as written, with the files merged and without profiles applied.

#### Scenario: A setting under a profile
- **WHEN** an agent is asked which output directory a run with the profile `ci` uses
- **THEN** it runs `robotcode -p ci profiles show` or `robotcode -p ci --dry robot`, not only `robotcode -p ci config show`

### Requirement: A debug run and the recorded run

The skill SHALL say that a debug run replaces the output file of the last run, and how to keep it: `--output NONE --log NONE --report NONE`.

#### Scenario: Debugging one test of a finished run
- **WHEN** an agent is asked to step through a failed test and afterwards to report on the last full run
- **THEN** its answer reports all tests of that run, not only the one it debugged

### Requirement: The skill's commands work as written

A command the skill shows SHALL work as written in a project with the default user configuration. The skill SHALL say that `--output` is relative to the output directory while `-o`, `--rerunfailed` and `rebot` take paths from the project root, and that Robot Framework's own options go before a path.

#### Scenario: A pinned run
- **WHEN** an agent is asked to keep a run's results in a file of their own and to rerun only the failures
- **THEN** the rerun finds that file, and the file is not in `results/results/`

#### Scenario: Options and a path
- **WHEN** the skill shows a command with a path and Robot Framework's options
- **THEN** the options come before the path

### Requirement: What the skill says matches the tool

A statement of the skill about a command, an option, an exit code or a message SHALL hold for the current tool. This covers at least: `discover tests` lists no tasks, `analyze code` without a path checks the whole project, `enabled` only applies to a profile that is selected, and a longname from `results` holds only for a run with the same paths.

#### Scenario: Tasks
- **WHEN** an agent is asked which tasks a project has
- **THEN** it runs `robotcode discover tasks` or `robotcode discover all`

### Requirement: The most important guidance comes first

The body of `SKILL.md` SHALL have about 5000 tokens at most, and running a test, selecting it, reading the results and debugging SHALL come before the other sections, because an agent may keep only the start of the file.

#### Scenario: After compaction
- **WHEN** only the first 5000 tokens of `SKILL.md` are left in an agent's context
- **THEN** they hold how to run, select, read the results of and debug a test

### Requirement: The description starts with the key use case

The `description` of the skill SHALL start with what the skill does and SHALL stay under the limit of 1024 characters with room to spare.

#### Scenario: Work on Robot Framework
- **WHEN** an agent other than a Haiku model is asked one of the cases on Robot Framework without the skill being named
- **THEN** it loads the skill

#### Scenario: Other work
- **WHEN** an agent is asked for something that has nothing to do with Robot Framework, in a project with `.robot` files
- **THEN** it doesn't load the skill

### Requirement: The evals cover what the skill teaches

Each reference of the skill SHALL be opened by at least one case of the evals, apart from `install.md`, which a case on a missing extra opens. A case SHALL be able to require that the skill doesn't load. The harness SHALL be able to run a case without the skill, for a comparison.

#### Scenario: A case in which the skill must not load
- **WHEN** a case expects no skill and the agent loads it
- **THEN** the case fails

#### Scenario: A run without the skill
- **WHEN** the harness runs with `--no-skill`
- **THEN** the agent has no copy of the skill, and the case isn't failed for not loading it

#### Scenario: Haiku in a case without a skill
- **WHEN** a case expects no skill and the model is a Haiku model
- **THEN** the prompt doesn't name the skill
