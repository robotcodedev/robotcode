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

### Requirement: A failed upload of a dev build doesn't stop the other uploads

When a store rejects the upload of a dev build, the nightly upload SHALL still upload the dev build to the other stores, including the JetBrains plugin to the channel `dev`. Afterwards it SHALL fail the run and show the store's response in the log.

#### Scenario: Rejected VS Code Marketplace token

- **WHEN** the VS Code Marketplace rejects the token during the nightly upload
- **THEN** Open VSX and the JetBrains channel `dev` still get the dev build, and the run fails with the Marketplace's error message in its log

#### Scenario: Failed JetBrains upload

- **WHEN** the JetBrains Marketplace rejects the upload of the plugin during the nightly upload
- **THEN** the VS Code Marketplace and Open VSX still get the dev build of the VS Code extension, and the run fails

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

### Requirement: Pushes and pull requests publish nothing by themselves

The runs for pushes to `main`, for pull requests and for manual starts of the build workflow SHALL NOT upload the plugin to the Marketplace unless they run for a version tag. A dev build SHALL reach the Marketplace only through the nightly upload.

#### Scenario: Push to main

- **WHEN** a push to `main` builds the plugin as version 2.8.0-dev.466
- **THEN** the run itself uploads nothing to the Marketplace, and the next nightly upload publishes 2.8.0-dev.466 if the run succeeded and is still the latest run on `main`

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

### Requirement: A night's dev builds come from the latest run on main

Every night, and when the maintainer starts it by hand, the CI SHALL wait up to two hours until the latest CI run for a push to `main` is done, following a newer run that starts meanwhile, and publish the dev builds of all stores from that one run. If that run doesn't succeed, or isn't done in time, no store SHALL get a dev build from this upload.

#### Scenario: Same build in every store

- **WHEN** the latest run on `main` succeeded and built the dev build with the number 527
- **THEN** the JetBrains channel `dev` gets 2.8.0-dev.527, the VS Code Marketplace and Open VSX get 2.7.100527, and PyPI gets 2.8.0.dev527, all from that run

#### Scenario: Broken latest build

- **WHEN** the latest run on `main` failed, and an earlier run succeeded
- **THEN** no store gets a dev build, and the upload says so in its log and ends successfully

#### Scenario: Build still running

- **WHEN** the latest run on `main` is still running when the upload starts, and it succeeds an hour later
- **THEN** the upload waits for it and then publishes its dev builds

#### Scenario: Newer build while waiting

- **WHEN** the upload waits for the latest run on `main`, and a push to `main` starts a newer run before that one is done
- **THEN** the upload waits for the newer run and publishes its dev builds if it succeeds, and ignores the result of the run it waited for first

#### Scenario: Build not done in time

- **WHEN** the latest run on `main` is still running two hours after the upload started
- **THEN** no store gets a dev build from this upload, and the next night takes the run if it succeeded and is still the latest
