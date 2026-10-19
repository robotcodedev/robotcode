# release-publishing Specification

## Purpose

Defines what the CI publishes when a version of RobotCode is tagged and as dev builds between releases, where it publishes it and into which channel, so that every release, prerelease and dev build reaches its users without a manual upload.

## Requirements

### Requirement: Builds without a tag give the VS Code extension a version the VS Code Marketplace accepts

A build of a commit without a version tag SHALL give the VS Code extension the version `A.B.((C + 1) × 100000 + N)`. `A.B.C` is the version of the last tag, and `N` is the number of first-parent commits since that tag, the same number as in the build's `-dev.N` version. A build of a tagged commit SHALL keep the tag's version.

#### Scenario: Dev build after a minor release

- **WHEN** the last tag is `v2.7.0`, and the build is 499 commits later with the version 2.8.0-dev.499
- **THEN** the VS Code extension of that build has the version 2.7.100499

#### Scenario: Dev build after a fix release

- **WHEN** the last tag is `v2.7.1`, and the build is of the first commit after it
- **THEN** the VS Code extension has the version 2.7.200001, which is higher than every dev build between 2.7.0 and 2.7.1

#### Scenario: Release commit

- **WHEN** the build is of the commit that the tag `v2.8.0` points to
- **THEN** the VS Code extension has the version 2.8.0

### Requirement: Only the VS Code extension's own version differs

A dev build of the VS Code extension SHALL bundle the RobotCode Python packages with the build's version, the same version that the Python packages and the JetBrains plugin of that build carry.

#### Scenario: Bundled Python packages

- **WHEN** a build without a tag has the version 2.8.0-dev.499
- **THEN** its VS Code extension has the version 2.7.100499, and the RobotCode Python packages bundled in it have the version 2.8.0-dev.499

### Requirement: Dev builds of the VS Code extension are pre-releases

The VSIX of a build without a tag SHALL be packaged as a pre-release, so that the VS Code Marketplace and Open VSX offer it only to users who switched the extension to its pre-release version.

#### Scenario: User on the release version

- **WHEN** the dev build 2.7.100499 is published, and a user has the release version 2.7.0 installed
- **THEN** VS Code keeps 2.7.0 for that user

#### Scenario: User on the pre-release version

- **WHEN** the dev build 2.7.100499 is published, and a user has switched the extension to its pre-release version
- **THEN** VS Code updates the extension to 2.7.100499 for that user

### Requirement: Dev builds of main are published to the VS Code Marketplace and Open VSX every night

Every night, and when the maintainer starts it by hand, the CI SHALL upload the VSIX of the most recent successful CI run on `main` to the VS Code Marketplace and to Open VSX, unless the store has that version already. Both stores SHALL get the VSIX that run built. A VSIX that isn't packaged as a pre-release SHALL NOT be uploaded this way.

#### Scenario: New dev build

- **WHEN** the most recent successful run on `main` built the VS Code extension 2.7.100499, and neither store has it
- **THEN** the nightly upload publishes that run's VSIX to both stores as a pre-release

#### Scenario: Nothing new since the last upload

- **WHEN** both stores already have the version of the most recent successful run on `main`
- **THEN** the nightly upload uploads nothing and succeeds

#### Scenario: Release commit on main

- **WHEN** the most recent successful run on `main` built the release version 2.8.0 from the release commit
- **THEN** the nightly upload uploads nothing, and the version reaches the stores through its tag

#### Scenario: Push to main

- **WHEN** a push to `main` builds the VS Code extension 2.7.100499
- **THEN** the run itself uploads nothing to either store, and the next nightly upload publishes 2.7.100499 if the run succeeded and no newer successful run exists

### Requirement: A failed upload of a dev build doesn't stop the other uploads

When a store rejects the upload of a dev build, the nightly upload SHALL still upload the dev build to the other stores, including the JetBrains plugin to the channel `dev`. Afterwards it SHALL fail the run and show the store's response in the log.

#### Scenario: Rejected VS Code Marketplace token

- **WHEN** the VS Code Marketplace rejects the token during the nightly upload
- **THEN** Open VSX and the JetBrains channel `dev` still get the dev build, and the run fails with the Marketplace's error message in its log

#### Scenario: Failed JetBrains upload

- **WHEN** the JetBrains Marketplace rejects the upload of the plugin during the nightly upload
- **THEN** the VS Code Marketplace and Open VSX still get the dev build of the VS Code extension, and the run fails
