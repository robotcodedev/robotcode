# Spec: cli-reference-generation

## Purpose

Defines which commands and options the generated CLI reference `docs/03_reference/cli.md` documents and in which order, so that it describes the command line that `robotcode --help` shows to users and regenerating it only changes what the command line changed.

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

The options of a command SHALL appear in the same order in `--help` and in the generated CLI reference in every environment. The options shared by `robot`, `robot-debug` and the `discover` commands SHALL appear in the order `--by-longname`, `--exclude-by-longname`, `--version`.

#### Scenario: Regenerating in another environment
- **WHEN** the CLI reference is generated twice with the same RobotCode and Robot Framework versions but in different environments or Python processes
- **THEN** both results are identical

#### Scenario: Shared options of robot
- **WHEN** `robotcode robot --help` is run
- **THEN** `--by-longname` is listed before `--exclude-by-longname`, and `--exclude-by-longname` before `--version`
