# Spec Delta

## Purpose

Defines what the CI publishes when a version of RobotCode is tagged, where it publishes it and into which channel, so that every release and prerelease reaches its users without a manual upload.

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
- **THEN** it is uploaded to the channel `dev`, which IDEs get only when they have `https://plugins.jetbrains.com/plugins/dev/list` as a plugin repository, and not to the default channel

#### Scenario: Prerelease with another label

- **WHEN** version 2.9.0-alpha.1 is published
- **THEN** it is uploaded to the channel `dev`, like any other prerelease

### Requirement: Builds without a version tag publish nothing to the Marketplace

Pushes to `main`, pull requests and manual runs without a version tag SHALL NOT upload the plugin to the Marketplace, although the versions of these builds carry a pre-release label too.

#### Scenario: Push to main

- **WHEN** a push to `main` builds the plugin as version 2.8.0-dev.466
- **THEN** the run uploads nothing to the Marketplace, and the channel `dev` keeps its previous version

### Requirement: Only a tested and verified plugin is published

The CI SHALL upload the plugin to the Marketplace only after the plugin's unit tests and the plugin verifier's checks have passed in the same run.

#### Scenario: Failing plugin test on a tag

- **WHEN** one of the plugin's unit tests fails in the run for a version tag
- **THEN** the run uploads nothing to the Marketplace

#### Scenario: Verifier problem on a tag

- **WHEN** the plugin verifier reports a problem at a failure level the build configures in the run for a version tag
- **THEN** the run uploads nothing to the Marketplace

### Requirement: A rejected upload fails the run

When the Marketplace rejects the upload, for example because the token is invalid or the version already exists, the CI SHALL fail the publish job and SHALL show the Marketplace's response in the job's log.

#### Scenario: Invalid token

- **WHEN** the Marketplace token has expired and a version tag is pushed
- **THEN** the publish job fails, and its log shows the Marketplace's error message
