# Spec Delta

## ADDED Requirements

### Requirement: A release is published after the build of its tag succeeded

When the build of a version tag succeeds, the CI SHALL create the GitHub release of that version with the packages this build made. It SHALL then upload them to the VS Code Marketplace, Open VSX, PyPI and the JetBrains Marketplace, under the rules for releases and prereleases. A build that fails SHALL publish nothing.

#### Scenario: Release tag

- **WHEN** the tag `v2.9.0` is pushed and its build succeeds
- **THEN** the GitHub release `v2.9.0` holds the VSIX, the Python packages and the JetBrains plugin of that build, and the stores receive version 2.9.0 from these files

#### Scenario: Failed build

- **WHEN** the tag `v2.9.0` is pushed and a test of its build fails
- **THEN** no GitHub release is created and no store receives version 2.9.0

### Requirement: Only a version tag of this repository publishes a release

The CI SHALL create a GitHub release and upload a release to the stores only for a build of a version tag pushed to this repository. Builds of pull requests, of pushes to branches and of manual starts SHALL NOT publish a release.

#### Scenario: Pull request from a fork

- **WHEN** the build of a pull request from a fork succeeds
- **THEN** nothing is published

#### Scenario: Push to main

- **WHEN** the build of a push to `main` succeeds
- **THEN** no release is published, and the build only becomes a dev build through the nightly upload

### Requirement: Releases and dev builds are published by one workflow

Every upload of a release or a dev build to a store, and every GitHub release, SHALL come from the same workflow file, `publish.yml`, so that a store that trusts a single workflow file of the repository can accept all of them.

#### Scenario: Release and dev build

- **WHEN** version 2.9.0 is released, and later the dev build 2.9.100003 is published
- **THEN** both uploads to Open VSX come from runs of `publish.yml`

### Requirement: A failed release upload doesn't stop the other uploads

When a store rejects the upload of a release, or the GitHub release can't be created, the CI SHALL still upload the release to the other stores. Afterwards it SHALL fail the run and show the response in the log.

#### Scenario: Rejected VS Code Marketplace token

- **WHEN** the VS Code Marketplace rejects the token during the upload of release 2.9.0
- **THEN** Open VSX, PyPI and the JetBrains Marketplace still receive 2.9.0, and the run fails with the Marketplace's error message in its log

#### Scenario: Failed GitHub release

- **WHEN** creating the GitHub release of 2.9.0 fails
- **THEN** the VS Code Marketplace, Open VSX, PyPI and the JetBrains Marketplace still receive 2.9.0, and the run fails

### Requirement: A re-run of a release uploads only what is missing

When the publishing of a release runs again, the CI SHALL skip every store that already has the version and SHALL update the existing GitHub release, so that a re-run after a failed upload only uploads what is missing.

#### Scenario: Re-run after a failed upload

- **WHEN** the upload of 2.9.0 to PyPI failed, and the maintainer replaced the PyPI token and re-ran the release job
- **THEN** PyPI receives 2.9.0, the other stores are skipped because they have it, and the run succeeds

#### Scenario: Re-run of a complete release

- **WHEN** every store has 2.9.0, and the release job runs again
- **THEN** nothing is uploaded, and the run succeeds

## MODIFIED Requirements

### Requirement: A version tag publishes the JetBrains plugin to the Marketplace

When the build of a version tag succeeds, the CI SHALL upload the JetBrains plugin to the JetBrains Marketplace. It SHALL upload the plugin file that this build packaged, which is also the file that the GitHub release of the version holds.

#### Scenario: Release tag

- **WHEN** the tag `v2.9.0` is pushed and its build succeeds
- **THEN** the JetBrains Marketplace has received version 2.9.0 of the plugin, and it is the same file as `robotcode4ij-2.9.0.zip` in the GitHub release of `v2.9.0`
