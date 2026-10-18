# Spec Delta

## ADDED Requirements

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
