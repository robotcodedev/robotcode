# Spec Delta

## Purpose

Defines what the CI publishes when a version of RobotCode is tagged and as dev builds between releases, where it publishes it and into which channel, so that every release, prerelease and dev build reaches its users without a manual upload.

## ADDED Requirements

### Requirement: A version tag publishes the JetBrains plugin to the Marketplace

When the CI runs for a version tag, it SHALL upload the JetBrains plugin to the JetBrains Marketplace. It SHALL upload the plugin file that the same run packaged, which is also the file that the run attaches to the GitHub release.

#### Scenario: Release tag

- **WHEN** the tag `v2.9.0` is pushed and the run succeeds
- **THEN** the JetBrains Marketplace has received version 2.9.0 of the plugin, and it is the same file as `robotcode4ij-2.9.0.zip` in the GitHub release of `v2.9.0`

### Requirement: Releases go to the default channel, prereleases to the channel dev

The CI SHALL publish a version without a pre-release label to the Marketplace's default channel, and a version with a pre-release label, whatever the label, to the channel `dev`.

#### Scenario: Release version

- **WHEN** version 2.9.0 is published
- **THEN** it is uploaded to the default channel, from which IDEs that use the Marketplace without extra repositories get their updates

#### Scenario: Prerelease with the dev label

- **WHEN** version 2.9.0-dev.3 is published
- **THEN** it is uploaded to the channel `dev`, which IDEs get only when they have RobotCode's channel, `https://plugins.jetbrains.com/plugins/dev/26216`, as a plugin repository, and not to the default channel

#### Scenario: Prerelease with another label

- **WHEN** version 2.9.0-alpha.1 is published
- **THEN** it is uploaded to the channel `dev`, like any other prerelease

### Requirement: Dev builds of main are published to the channel dev every night

Every night, and when the maintainer starts it by hand, the CI SHALL upload the plugin of the most recent successful CI run on `main` to the channel `dev`, unless the channel has that version already. It SHALL NOT upload a version without a pre-release label this way.

#### Scenario: New dev build

- **WHEN** the most recent successful run on `main` built version 2.8.0-dev.470, and the channel `dev` doesn't have it
- **THEN** the nightly upload puts 2.8.0-dev.470 into the channel `dev`

#### Scenario: Nothing new since the last upload

- **WHEN** the channel `dev` already has the version of the most recent successful run on `main`
- **THEN** the nightly upload uploads nothing and succeeds

#### Scenario: Release commit on main

- **WHEN** the most recent successful run on `main` built the release version 2.8.0 from the release commit
- **THEN** the nightly upload uploads nothing, and the version reaches the Marketplace through its tag

### Requirement: Pushes and pull requests publish nothing by themselves

The runs for pushes to `main`, for pull requests and for manual starts of the build workflow SHALL NOT upload the plugin to the Marketplace unless they run for a version tag. A dev build SHALL reach the Marketplace only through the nightly upload.

#### Scenario: Push to main

- **WHEN** a push to `main` builds the plugin as version 2.8.0-dev.466
- **THEN** the run itself uploads nothing to the Marketplace, and the next nightly upload publishes 2.8.0-dev.466 if the run succeeded and no newer successful run exists

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
- **THEN** the nightly upload doesn't take the plugin of that run, but at most the plugin of the most recent successful run

### Requirement: The plugin's change notes fit the Marketplace's limit

The plugin's change notes SHALL be the changelog section of its version when that section has at most 65,535 characters. Otherwise they SHALL list only the features, bug fixes and performance improvements, one line each, shortened at the end if needed, and SHALL link to the full list of changes, so that the Marketplace accepts every release and dev build.

#### Scenario: Small release

- **WHEN** the changelog section of version 2.7.0 has 5,524 characters
- **THEN** the change notes are that section, with the commit message bodies and all its sections

#### Scenario: Large release

- **WHEN** the changelog section of version 2.8.0 is longer than 65,535 characters
- **THEN** the change notes list the subject lines of its features, bug fixes and performance improvements, link to `CHANGELOG.md`, and the Marketplace accepts the upload

#### Scenario: Dev build

- **WHEN** the unreleased changes of a dev build are longer than 65,535 characters
- **THEN** the change notes list the subject lines of the features, bug fixes and performance improvements and link to the commit history of `main`

### Requirement: A rejected upload fails the run

When the Marketplace rejects an upload, for example because the token is invalid or the version already exists, the CI SHALL fail the job that uploads and SHALL show the Marketplace's response in the job's log.

#### Scenario: Invalid token

- **WHEN** the Marketplace token has expired and a version tag is pushed
- **THEN** the publish job fails, and its log shows the Marketplace's error message
