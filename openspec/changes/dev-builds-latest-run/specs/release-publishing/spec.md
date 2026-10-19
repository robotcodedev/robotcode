# Spec Delta

## ADDED Requirements

### Requirement: A night's dev builds come from the latest run on main

Every night, and when the maintainer starts it by hand, the CI SHALL take the latest CI run for a push to `main`, wait up to two hours if it is still running, and publish the dev builds of all stores from that one run. If that run doesn't succeed, or isn't done in time, no store SHALL get a dev build from this upload.

#### Scenario: Same build in every store

- **WHEN** the latest run on `main` succeeded and built the dev build with the number 527
- **THEN** the JetBrains channel `dev` gets 2.8.0-dev.527, the VS Code Marketplace and Open VSX get 2.7.100527, and PyPI gets 2.8.0.dev527, all from that run

#### Scenario: Broken latest build

- **WHEN** the latest run on `main` failed, and an earlier run succeeded
- **THEN** no store gets a dev build, and the upload says so in its log and ends successfully

#### Scenario: Build still running

- **WHEN** the latest run on `main` is still running when the upload starts, and it succeeds an hour later
- **THEN** the upload waits for it and then publishes its dev builds

#### Scenario: Build not done in time

- **WHEN** the latest run on `main` is still running two hours after the upload started
- **THEN** no store gets a dev build from this upload, and the next night takes the run if it succeeded and is still the latest

## MODIFIED Requirements

### Requirement: Dev builds of main are published to the VS Code Marketplace and Open VSX every night

Every night, and when the maintainer starts it by hand, the CI SHALL upload the VSIX of the latest CI run on `main` to the VS Code Marketplace and to Open VSX, when that run succeeded and unless the store has that version already. Both stores SHALL get the VSIX that run built. A VSIX that isn't packaged as a pre-release SHALL NOT be uploaded this way.

#### Scenario: New dev build

- **WHEN** the latest run on `main` succeeded and built the VS Code extension 2.7.100499, and neither store has it
- **THEN** the nightly upload publishes that run's VSIX to both stores as a pre-release

#### Scenario: Nothing new since the last upload

- **WHEN** both stores already have the version of the latest run on `main`
- **THEN** the nightly upload uploads nothing and succeeds

#### Scenario: Release commit on main

- **WHEN** the latest run on `main` built the release version 2.8.0 from the release commit
- **THEN** the nightly upload uploads nothing, and the version reaches the stores through its tag

#### Scenario: Push to main

- **WHEN** a push to `main` builds the VS Code extension 2.7.100499
- **THEN** the run itself uploads nothing to either store, and the next nightly upload publishes 2.7.100499 if the run succeeded and is still the latest run on `main`

### Requirement: Dev builds of main are published to the channel dev every night

Every night, and when the maintainer starts it by hand, the CI SHALL upload the plugin of the latest CI run on `main` to the channel `dev`, when that run succeeded and unless the channel has that version already. It SHALL NOT upload a version without a pre-release label this way.

#### Scenario: New dev build

- **WHEN** the latest run on `main` succeeded and built version 2.8.0-dev.470, and the channel `dev` doesn't have it
- **THEN** the nightly upload puts 2.8.0-dev.470 into the channel `dev`

#### Scenario: Nothing new since the last upload

- **WHEN** the channel `dev` already has the version of the latest run on `main`
- **THEN** the nightly upload uploads nothing and succeeds

#### Scenario: Release commit on main

- **WHEN** the latest run on `main` built the release version 2.8.0 from the release commit
- **THEN** the nightly upload uploads nothing, and the version reaches the Marketplace through its tag

### Requirement: Only a tested and verified plugin is published

The CI SHALL upload a plugin file to the Marketplace only after the plugin's unit tests and the plugin verifier's checks have passed in the run that built that file.

#### Scenario: Failing plugin test on a tag

- **WHEN** one of the plugin's unit tests fails in the run for a version tag
- **THEN** the run uploads nothing to the Marketplace

#### Scenario: Verifier problem on a tag

- **WHEN** the plugin verifier reports a problem at a failure level the build configures in the run for a version tag
- **THEN** the run uploads nothing to the Marketplace

#### Scenario: Failing plugin test on main

- **WHEN** one of the plugin's unit tests fails in the latest run on `main`
- **THEN** the nightly upload uploads no plugin, also when an earlier run on `main` succeeded

### Requirement: Dev builds of main are published to PyPI every night

Every night, and when the maintainer starts it by hand, the CI SHALL upload the Python packages of the latest CI run on `main` to PyPI, when that run succeeded and unless PyPI has that version already. A release version SHALL NOT be uploaded this way.

#### Scenario: New dev build

- **WHEN** the latest run on `main` succeeded and built the Python packages 2.8.0.dev508, and PyPI doesn't have them
- **THEN** the nightly upload publishes version 2.8.0.dev508 of all 12 projects, `robotcode` and the eleven `robotcode-*` packages

#### Scenario: Nothing new since the last upload

- **WHEN** PyPI already has the version of the latest run on `main`
- **THEN** the nightly upload uploads nothing and succeeds

#### Scenario: Release commit on main

- **WHEN** the latest run on `main` built the release version 2.8.0 from the release commit
- **THEN** the nightly upload uploads nothing, and the version reaches PyPI through its tag
