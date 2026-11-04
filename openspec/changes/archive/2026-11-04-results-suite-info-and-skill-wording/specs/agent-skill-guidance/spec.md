# Spec Delta

## ADDED Requirements

### Requirement: The file of another run

`SKILL.md` SHALL say that the file of a run other than the last one goes with `-o <file>` after the subcommand of `robotcode results`, so that an agent that hasn't opened `references/results.md` names it in a form the command accepts.

#### Scenario: Results in a folder of their own
- **WHEN** an agent runs a suite with its results in a folder of their own and then reads that run
- **THEN** it calls `robotcode results <subcommand> -o <file>`
- **AND** it doesn't call `robotcode results -o <file> <subcommand>` or `robotcode results <subcommand> <file>`

### Requirement: What starting a session prints

Where `SKILL.md` says how the REPL and the debugger run as a session, it SHALL say that `robotcode session start` prints `Started session <ID>.`, and not that it prints the ID alone.

#### Scenario: Starting a session
- **WHEN** an agent reads in `SKILL.md` how to run the REPL or the debugger as a session
- **THEN** the text shows the sentence that holds the ID
