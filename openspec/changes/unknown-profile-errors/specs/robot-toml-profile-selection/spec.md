## Purpose

Defines how robotcode commands select the profiles of `robot.toml` by name or pattern, from the command line, the environment, `default-profiles` and `inherits`, and what they do when a name selects no profile.

## ADDED Requirements

### Requirement: A name that selects no profile stops the command

When a name or pattern of a profile selects no profile, robotcode commands SHALL stop with an error that names it, before they run anything. This holds for names from `-p`/`--profile`, also when an editor passes its selection that way, and from `ROBOTCODE_PROFILES`, `default-profiles` and `inherits`. Commands that pass on Robot Framework's exit codes SHALL exit with 252. `robotcode profiles list` SHALL report the error and list the profiles anyway.

#### Scenario: Mistyped profile on the command line

- **WHEN** `robotcode -p missing run` runs in a project that has no profile `missing`
- **THEN** it reports "Can't find any configuration profiles matching the pattern 'missing'.", runs no test and exits with 252

#### Scenario: Pattern without a match

- **WHEN** `robotcode -p "browser-*" discover tests` runs in a project that has no profile whose name starts with `browser-`
- **THEN** it reports the error for `browser-*`, lists no tests and exits with an error

#### Scenario: Default profile that does not exist

- **WHEN** `robot.toml` sets `default-profiles = ["typo"]`, has no profile `typo`, and `robotcode run` runs without `-p`
- **THEN** it reports the error for `typo`, runs no test and exits with 252

#### Scenario: Inherited profile that does not exist

- **WHEN** the profile `ci` sets `inherits = ["typo"]`, there is no profile `typo`, and `robotcode -p ci run` runs
- **THEN** it reports the error for `typo`, runs no test and exits with 252

#### Scenario: Listing the profiles

- **WHEN** `robotcode -p missing profiles list` runs
- **THEN** it reports the error for `missing`, lists the profiles of the configuration and exits with 0

### Requirement: An error in an enabled condition is reported

When the `enabled` condition of a selected profile cannot be evaluated, robotcode commands SHALL report the error once and go on without that profile.

#### Scenario: Condition with invalid syntax

- **WHEN** the selected profile `ci` sets `enabled = { if = 'environ.get("CI") = "true"' }` and `robotcode -p ci run` runs
- **THEN** it reports that the condition of `ci` cannot be evaluated, once, and runs the tests without the settings of `ci`
