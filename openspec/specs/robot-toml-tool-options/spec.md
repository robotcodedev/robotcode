# robot-toml-tool-options Specification

## Purpose

Defines how the options of `robotcode rebot`, `robotcode libdoc` and `robotcode testdoc` come together from their tables in `robot.toml`, the settings outside of these tables, the selected profiles and later configuration files.

## Requirements

### Requirement: A tool table wins over the settings outside of it

For `robotcode rebot`, `robotcode libdoc` and `robotcode testdoc`, a setting in the command's table (`[rebot]`, `[libdoc]`, `[testdoc]`) SHALL win over the same setting outside of the table. An `extend-` setting in the table SHALL add to the value that the command takes from outside of the table, following the same rules as `extend-` settings elsewhere in `robot.toml`.

#### Scenario: The rebot table wins
- **WHEN** `robot.toml` contains `output-dir = "results"` and `[rebot]` with `output-dir = "merged"`, and `robotcode rebot output.xml` is run
- **THEN** `rebot` gets `--outputdir merged`

#### Scenario: The libdoc table wins
- **WHEN** `robot.toml` contains `python-path = ["libraries"]` and `[libdoc]` with `python-path = ["doc-libraries"]`, and `robotcode libdoc MyLibrary out.html` is run
- **THEN** `libdoc` gets only `doc-libraries` as Python path

#### Scenario: The testdoc table wins
- **WHEN** `robot.toml` contains `name = "Shop"` and `[testdoc]` with `name = "Shop Tests"`, and `robotcode testdoc tests out.html` is run
- **THEN** `testdoc` gets `--name "Shop Tests"`

#### Scenario: An extend- setting in the table adds
- **WHEN** `robot.toml` contains `tag-stat-include = ["smoke"]` and `[rebot]` with `extend-tag-stat-include = ["api"]`, and `robotcode rebot output.xml` is run
- **THEN** `rebot` gets the tag statistics includes `smoke` and `api`

#### Scenario: Without the setting in the table
- **WHEN** `robot.toml` contains `output-dir = "results"` and a `[rebot]` table without `output-dir`, and `robotcode rebot output.xml` is run
- **THEN** `rebot` gets `--outputdir results`

### Requirement: rebot takes the settings that Robot Framework passes to rebot

Of the settings outside of `[rebot]`, `robotcode rebot` SHALL take the ones that `rebot` knows, except those that Robot Framework itself does not pass from `robot` to `rebot` after a run: `includes`, `excludes`, `tests`, `suites`, `parse-include`, `name`, `doc`, `metadata`, `set-tag`, `output`, `log-level`, `timestamp-outputs`, `console` and `quiet`. As Robot Framework does, `run-empty-suite` SHALL reach `rebot` as `process-empty-suite`. The same settings in `[rebot]` SHALL reach `rebot`.

#### Scenario: Settings that do not reach rebot
- **WHEN** `robot.toml` contains `includes = ["smoke"]`, `name = "Shop"`, `output = "output.xml"` and `log-level = "DEBUG"` outside of `[rebot]`, and `robotcode rebot output.xml` is run
- **THEN** `rebot` gets none of `--include`, `--name`, `--output` and `--loglevel`

#### Scenario: Settings that reach rebot
- **WHEN** `robot.toml` contains `report-title = "Nightly"` and `python-path = ["libraries"]` outside of `[rebot]`, and `robotcode rebot output.xml` is run
- **THEN** `rebot` gets `--reporttitle Nightly` and `--pythonpath libraries`

#### Scenario: Tasks and run-empty-suite reach rebot
- **WHEN** `robot.toml` contains `tasks = ["Process*"]`, `tests = ["Login*"]` and `run-empty-suite = true` outside of `[rebot]`, and `robotcode rebot output.xml` is run
- **THEN** `rebot` gets `--task Process*` and `--processemptysuite`, but no `--test`

#### Scenario: process-empty-suite in the rebot table wins
- **WHEN** `robot.toml` contains `run-empty-suite = true` and `[rebot]` with `process-empty-suite = false`, and `robotcode rebot output.xml` is run
- **THEN** `rebot` does not process empty suites

#### Scenario: The same settings in the rebot table
- **WHEN** `robot.toml` contains `[rebot]` with `name = "Merged"` and `includes = ["smoke"]`, and `robotcode rebot output.xml` is run
- **THEN** `rebot` gets `--name Merged` and `--include smoke`

### Requirement: libdoc takes only the Python path from outside its table

Of the settings outside of `[libdoc]`, `robotcode libdoc` SHALL take only `python-path`. In particular, `name` and `quiet` outside of `[libdoc]`, which are `robot` options, SHALL NOT reach `libdoc`.

#### Scenario: The suite name does not name the library
- **WHEN** `robot.toml` contains `name = "Shop Tests"` and `quiet = true` outside of `[libdoc]`, and `robotcode libdoc Collections out.html` is run
- **THEN** `libdoc` gets neither `--name` nor `--quiet`

#### Scenario: The Python path reaches libdoc
- **WHEN** `robot.toml` contains `python-path = ["libraries"]` outside of `[libdoc]`, and `robotcode libdoc MyLibrary out.html` is run
- **THEN** `libdoc` gets `--pythonpath libraries`

### Requirement: testdoc takes the settings it shares with robot

Of the settings outside of `[testdoc]`, `robotcode testdoc` SHALL take the ones it shares with `robot`: `name`, `doc`, `metadata`, `set-tag`, `tests`, `suites`, `includes` and `excludes`.

#### Scenario: Shared settings reach testdoc
- **WHEN** `robot.toml` contains `name = "Shop"` and `includes = ["smoke"]` and no `[testdoc]` table, and `robotcode testdoc tests out.html` is run
- **THEN** `testdoc` gets `--name Shop` and `--include smoke`

### Requirement: extend- tables change a tool table

`robot.toml`, `.robot.toml`, `pyproject.toml` and the user configuration SHALL accept `extend-rebot`, `extend-libdoc` and `extend-testdoc`, outside of profiles, in a profile and in `extend-profiles`. Such a table SHALL change the table of the same command that comes before it: a setting in it replaces the one of that table, and an `extend-` setting in it adds to it. A plain `[rebot]`, `[libdoc]` or `[testdoc]` SHALL keep replacing the whole table that comes before it.

#### Scenario: extend-rebot in a later file
- **WHEN** `robot.toml` contains `[rebot]` with `merge = true`, `.robot.toml` contains `[extend-rebot]` with `report-title = "Mine"`, and `robotcode rebot output.xml` is run
- **THEN** `rebot` gets `--merge` and `--reporttitle Mine`

#### Scenario: extend-rebot in a profile
- **WHEN** `robot.toml` contains `[rebot]` with `merge = true` and `[profiles.ci.extend-rebot]` with `log-title = "CI"`, and `robotcode -p ci rebot output.xml` is run
- **THEN** `rebot` gets `--merge` and `--logtitle CI`

#### Scenario: extend-rebot in extend-profiles
- **WHEN** `robot.toml` contains `[profiles.ci.rebot]` with `merge = true`, `.robot.toml` contains `[extend-profiles.ci.extend-rebot]` with `log-title = "Mine"`, and `robotcode -p ci rebot output.xml` is run
- **THEN** `rebot` gets `--merge` and `--logtitle Mine`

#### Scenario: An extend- setting in an extend- table adds
- **WHEN** `robot.toml` contains `tag-stat-include = ["smoke"]` and `[rebot]` with `merge = true`, `.robot.toml` contains `[extend-rebot]` with `extend-tag-stat-include = ["api"]`, and `robotcode rebot output.xml` is run
- **THEN** `rebot` gets `--merge` and the tag statistics includes `smoke` and `api`

#### Scenario: extend-libdoc and extend-testdoc in a later file
- **WHEN** `robot.toml` contains `[libdoc]` with `format = "HTML"` and `[testdoc]` with `title = "Shop"`, `.robot.toml` contains `[extend-libdoc]` with `theme = "DARK"` and `[extend-testdoc]` with `name = "Shop Tests"`, and `robotcode libdoc` and `robotcode testdoc` are run
- **THEN** `libdoc` gets `--format HTML` and `--theme DARK`
- **AND** `testdoc` gets `--title Shop` and `--name "Shop Tests"`

#### Scenario: A plain table replaces the table before it
- **WHEN** `robot.toml` contains `[rebot]` with `merge = true`, `.robot.toml` contains `[rebot]` with `report-title = "Mine"`, and `robotcode rebot output.xml` is run
- **THEN** `rebot` gets `--reporttitle Mine` and no `--merge`

#### Scenario: Selecting a profile does not change the configuration
- **WHEN** a profile with `extend-rebot` is applied and the configuration is combined again without that profile
- **THEN** the `[rebot]` table of the second result has none of the profile's settings
