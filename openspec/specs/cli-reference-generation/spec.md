# Spec: cli-reference-generation

## Purpose

Defines which commands and options the generated CLI reference `docs/src/content/docs/reference/cli.md` documents and in which order, so that it describes the command line that `robotcode --help` shows to users and regenerating it only changes what the command line changed.

## Requirements

### Requirement: Only visible commands and options are documented

The CLI reference generated from the `robotcode` command tree SHALL document a command or an option only if `--help` shows it. A command hidden from `--help` SHALL appear neither in its group's command list, nor in its group's alias list, nor as a section of its own, and none of its options or subcommands SHALL be documented.

#### Scenario: Hidden top-level command
- **WHEN** the CLI reference is generated
- **THEN** it contains neither a command list entry nor a section for the internal command `debug-launch`
- **AND** the command list of `robotcode` still lists the visible commands such as `debug`, `discover` and `robot`

#### Scenario: Hidden command in a group
- **WHEN** the CLI reference is generated
- **THEN** the command list and the sections of `analyze` contain `cache` and `code` but not `dump-model`

#### Scenario: Hidden option
- **WHEN** the CLI reference is generated
- **THEN** the section of `discover` documents `--diagnostics / --no-diagnostics` but not the internal option `--read-from-stdin`

### Requirement: Options appear in a fixed order

The options of a command SHALL appear in the same order in `--help` and in the generated CLI reference in every environment. The options shared by `robot`, `robot-debug` and the `discover` commands SHALL appear in the order `--by-longname`, `--exclude-by-longname`, `--by-test-metadata`, `--exclude-by-test-metadata`, `--version`. With Robot Framework older than 7.5 installed, where `--by-test-metadata` and `--exclude-by-test-metadata` are not shown, the other three SHALL keep their order.

#### Scenario: Regenerating in another environment
- **WHEN** the CLI reference is generated twice with the same RobotCode and Robot Framework versions but in different environments or Python processes
- **THEN** both results are identical

#### Scenario: Shared options of robot
- **WHEN** `robotcode robot --help` is run on RF 7.5
- **THEN** `--by-longname`, `--exclude-by-longname`, `--by-test-metadata`, `--exclude-by-test-metadata` and `--version` are listed in this order

#### Scenario: Shared options of discover metadata
- **WHEN** `robotcode discover metadata --help` is run on RF 7.5
- **THEN** the shared options are listed in the same order as for `robot`

#### Scenario: Shared options on an older Robot Framework
- **WHEN** `robotcode robot --help` is run on RF 7.4
- **THEN** `--by-longname` is listed before `--exclude-by-longname`, and `--exclude-by-longname` before `--version`

### Requirement: Version-dependent commands and options are marked

A command or option that RobotCode offers only from a certain Robot Framework version on — hidden from `--help` with an older version installed — SHALL be marked with that version in the generated CLI reference, as `(Robot Framework 7.5+)`: an option in its description, a command in its entry of the command list and at the start of its section. Its `--help` SHALL NOT carry the note: there it is only shown when the installed version has it.

#### Scenario: Version-dependent option
- **WHEN** the CLI reference is generated on RF 7.5
- **THEN** the descriptions of `--by-test-metadata` and `--exclude-by-test-metadata` in the sections of `robot`, `discover tests` and `results show`, and of `--show-metadata` in the sections of `discover all` and `results show`, are marked `(Robot Framework 7.5+)`
- **AND** `--by-longname` is not marked

#### Scenario: Version-dependent command
- **WHEN** the CLI reference is generated on RF 7.5
- **THEN** the entry of `metadata` in the command list of `discover` and the section of `discover metadata` are marked `(Robot Framework 7.5+)`

#### Scenario: Help without the note
- **WHEN** `robotcode robot --help` and `robotcode discover metadata --help` run on RF 7.5
- **THEN** neither output mentions a Robot Framework version
