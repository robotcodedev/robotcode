# Spec Delta

## MODIFIED Requirements

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
