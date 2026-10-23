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

### Requirement: Dev builds of main are published to PyPI every night

Every night, and when the maintainer starts it by hand, the CI SHALL upload the Python packages of the most recent successful CI run on `main` to PyPI, unless PyPI has that version already. A release version SHALL NOT be uploaded this way.

#### Scenario: New dev build

- **WHEN** the most recent successful run on `main` built the Python packages 2.8.0.dev508, and PyPI doesn't have them
- **THEN** the nightly upload publishes version 2.8.0.dev508 of all 12 projects, `robotcode` and the eleven `robotcode-*` packages

#### Scenario: Nothing new since the last upload

- **WHEN** PyPI already has the version of the most recent successful run on `main`
- **THEN** the nightly upload uploads nothing and succeeds

#### Scenario: Release commit on main

- **WHEN** the most recent successful run on `main` built the release version 2.8.0 from the release commit
- **THEN** the nightly upload uploads nothing, and the version reaches PyPI through its tag

### Requirement: A dev version of robotcode is published only together with the packages it requires

The nightly upload SHALL upload the package `robotcode` after the eleven packages it depends on, and only when all of them are on PyPI in that version, so that installing a dev version of `robotcode` never fails for a missing dependency.

#### Scenario: Failed upload of a dependency

- **WHEN** the upload of `robotcode-core` 2.8.0.dev508 fails
- **THEN** `robotcode` 2.8.0.dev508 isn't uploaded, and the run fails

#### Scenario: The next upload completes the version

- **WHEN** an earlier upload of 2.8.0.dev508 stopped after some of the packages, and the nightly upload runs again for that version
- **THEN** it uploads the missing packages and then `robotcode`, and leaves the packages that PyPI has already

### Requirement: Users get a Python dev version only on request

The Python dev versions SHALL be development releases in the sense of PEP 440, so that installers choose them only when asked to.

#### Scenario: Plain install

- **WHEN** version 2.8.0.dev508 is on PyPI, and a user runs `pip install robotcode`
- **THEN** pip installs the latest release, not 2.8.0.dev508

#### Scenario: Install of a dev version

- **WHEN** a user runs `pip install "robotcode[all]==2.8.0.dev508"`
- **THEN** pip installs `robotcode` and all its packages in version 2.8.0.dev508

### Requirement: A failed PyPI upload doesn't stop the other dev build uploads

When PyPI rejects the upload of a dev build, the nightly upload SHALL still upload the dev build to the other stores, and a failure at another store SHALL NOT stop the upload to PyPI. Afterwards the run SHALL fail and show the response in the log.

#### Scenario: Rejected PyPI token

- **WHEN** PyPI rejects the token during the nightly upload
- **THEN** the VS Code Marketplace, Open VSX and the JetBrains channel `dev` still get the dev build, and the run fails with PyPI's error message in its log

#### Scenario: Failed upload to another store

- **WHEN** the JetBrains Marketplace rejects the upload of the plugin during the nightly upload
- **THEN** PyPI still gets the Python packages of the dev build, and the run fails

### Requirement: The documentation tells users how to get the dev builds

robotcode.io SHALL have a page in Getting Started that explains, for the VS Code extension, the PyCharm plugin and the Python packages, how a user switches to the dev builds, how they go back to the releases, and what the version of a dev build looks like. The README SHALL link to that page.

#### Scenario: PyCharm user subscribes to the dev builds

- **WHEN** a PyCharm user follows the page
- **THEN** they add the plugin repository of RobotCode's channel `dev`, and the IDE offers the newest dev build of RobotCode, but no dev builds of other plugins

#### Scenario: VS Code user goes back to the release

- **WHEN** a VS Code user on a dev build follows the page's way back
- **THEN** VS Code installs the newest release version of the extension

#### Scenario: Python dev version without other pre-releases

- **WHEN** a user installs a Python dev version by naming it, as the page shows for pip and for uv
- **THEN** the installer installs that dev version of `robotcode` and of its packages, and releases of all other dependencies, such as Robot Framework

#### Scenario: README link

- **WHEN** a reader looks for ways to help in the README
- **THEN** "Get Involved" links to the page
