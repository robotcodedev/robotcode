## Purpose

Defines how robotcode commands select the profiles of `robot.toml` by name or pattern, from the command line, the environment, an editor's selection, `default-profiles` and `inherits`, and what they do when a name selects no profile.

## ADDED Requirements

### Requirement: A name that selects no profile stops the command

When a name or pattern of a profile selects no profile, robotcode commands SHALL stop with an error before they run anything. This holds for names from `-p`/`--profile`, also when an editor passes its selection that way, and from `ROBOTCODE_PROFILES` and `inherits`. Commands that pass on Robot Framework's exit codes SHALL exit with 252.

#### Scenario: Mistyped profile on the command line

- **WHEN** `robotcode -p missing run` runs in a project that has no profile `missing`
- **THEN** it reports the error for `missing`, runs no test and exits with 252

#### Scenario: Pattern without a match

- **WHEN** `robotcode -p "browser-*" discover tests` runs in a project that has no profile whose name starts with `browser-`
- **THEN** it reports the error for `browser-*`, lists no tests and exits with an error

#### Scenario: Inherited profile that does not exist

- **WHEN** the profile `ci` sets `inherits = ["typo"]`, there is no profile `typo`, and `robotcode -p ci run` runs
- **THEN** it reports the error for `typo`, runs no test and exits with 252

#### Scenario: Profile in VS Code's user settings

- **WHEN** the user settings of VS Code set `robotcode.profiles` to `["ci"]`, and the `robot.toml` of a workspace folder defines no profile `ci`
- **THEN** the discovery of that folder stops with the error for `ci`

### Requirement: A default profile that does not exist is reported

When a name or pattern in `default-profiles` selects no profile, robotcode commands SHALL report the error and go on without it.

#### Scenario: Default profile that does not exist

- **WHEN** `robot.toml` sets `default-profiles = ["typo"]`, has no profile `typo`, and `robotcode run` runs without `-p`
- **THEN** it reports the error for `typo` and runs the tests with the configuration without `typo`

#### Scenario: Default profile of the user configuration

- **WHEN** the user configuration sets `default-profiles = ["mine"]` and defines the profile `mine`, the `robot.toml` of a project defines its own profiles, and `robotcode run` runs there without `-p`
- **THEN** it reports the error for `mine` and runs the tests

### Requirement: An exact name selects its profile

A name that is the name of a profile SHALL select that profile, also when it contains `*`, `?` or `[`. Only other names SHALL be matched as patterns.

#### Scenario: Profile name with brackets

- **WHEN** `robot.toml` defines the profile `ci[eu]` and `robotcode -p "ci[eu]" run` runs
- **THEN** the run uses the settings of `ci[eu]`

### Requirement: Each name that selects no profile is reported once

A name or pattern that selects no profile SHALL be reported once for each place it comes from, also when several selected profiles inherit it or the selection names it twice.

#### Scenario: Missing profile inherited on two paths

- **WHEN** the profiles `chrome` and `firefox` both inherit `base`, `base` sets `inherits = ["comon"]`, there is no profile `comon`, and `robotcode -p chrome -p firefox profiles list` runs
- **THEN** it reports the error for `comon` once

#### Scenario: Name selected twice

- **WHEN** `robotcode -p typo -p typo --format json profiles list` runs in a project without a profile `typo`
- **THEN** its JSON output names `typo` once as a name of the selection that selects no profile

### Requirement: A profile that inherits itself is an error

A pattern in `inherits` SHALL NOT match the profile that has it. When a profile inherits itself, directly or through other profiles, robotcode commands SHALL stop with an error that names the profiles on the way, before they run anything. Commands that pass on Robot Framework's exit codes SHALL exit with 252.

#### Scenario: Pattern that matches the profile itself

- **WHEN** `robot.toml` defines the profiles `ci-base` and `ci-linux`, `ci-linux` sets `inherits = ["ci-*"]`, and `robotcode -p ci-linux run` runs
- **THEN** the run uses the settings of `ci-base` and `ci-linux`

#### Scenario: Two profiles that inherit each other

- **WHEN** the profile `a` sets `inherits = ["b"]`, the profile `b` sets `inherits = ["a"]`, and `robotcode -p a run` runs
- **THEN** it reports "The profile 'a' inherits itself: a -> b -> a.", runs no test and exits with 252

### Requirement: The profile list goes on and names such names

`robotcode profiles list` SHALL report a name that selects no profile and list the profiles anyway. Its JSON output SHALL name the names and patterns of the selection that select no profile.

#### Scenario: Listing the profiles

- **WHEN** `robotcode -p missing -p ci --format json profiles list` runs in a project that defines the profile `ci`
- **THEN** it reports the error for `missing`, lists the profiles of the configuration with `ci` selected, names `missing` as a name of the selection that selects no profile, and exits with 0

### Requirement: The error names the name

The error for a name or pattern that selects no profile SHALL name it and nothing else, whether it comes from the selection, `default-profiles` or `inherits`.

#### Scenario: Name of the selection

- **WHEN** `robot.toml` defines the profiles `ci` and `dev`, and `robotcode -p typo run` runs
- **THEN** the error is "No profile matches 'typo'."

#### Scenario: Name in default-profiles

- **WHEN** `robot.toml` defines the profiles `ci` and `dev`, sets `default-profiles = ["typo"]`, and `robotcode run` runs without `-p`
- **THEN** the reported error is "No profile matches 'typo'."

#### Scenario: Name in inherits

- **WHEN** `robot.toml` defines the profiles `ci` and `dev`, `ci` sets `inherits = ["typo"]`, and `robotcode -p ci run` runs
- **THEN** the error is "No profile matches 'typo'."

### Requirement: An error in an enabled condition is reported

When the `enabled` condition of a selected profile cannot be evaluated, robotcode commands SHALL report the error once and go on without that profile.

#### Scenario: Condition with invalid syntax

- **WHEN** the selected profile `ci` sets `enabled = { if = 'environ.get("CI") = "true"' }` and `robotcode -p ci run` runs
- **THEN** it reports that the condition of `ci` cannot be evaluated, once, and runs the tests without the settings of `ci`
