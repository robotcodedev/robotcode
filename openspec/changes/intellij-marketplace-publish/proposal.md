# Proposal

## Why

On every version tag the CI publishes the VS Code extension and the Python packages, and attaches the JetBrains plugin to the GitHub release, but the plugin reaches the JetBrains Marketplace only when the maintainer uploads it by hand. PyCharm and IntelliJ IDEA users get a release later than VS Code users, and prereleases never reach them. Users who want to try what is on `main` before the next release can't get it in their IDE at all. The publish step already receives the Marketplace token (`PUBLISH_TOKEN` from the secret `JETBRAINS_MARKETPLACE_TOKEN`), but `scripts/publish.py` doesn't use it.

## What Changes

- On a version tag, the CI uploads the JetBrains plugin to the JetBrains Marketplace: the zip that the package job built, the same file that the GitHub release gets.
- A release version goes to the Marketplace's default channel. A prerelease version, whatever its pre-release label (for example `2.9.0-dev.3`), goes to the channel `dev`. Users who want prereleases add `https://plugins.jetbrains.com/plugins/dev/list` as a plugin repository in their IDE.
- Every night, and when the maintainer starts it by hand, a separate workflow uploads the plugin from the latest successful CI run on `main` to the channel `dev`, unless that version is there already. These dev builds carry the versions that the CI already gives builds without a tag, for example `2.8.0-dev.470`.
- Pushes and pull requests upload nothing themselves. A dev build reaches the channel `dev` only through the nightly upload, and the release commit on `main`, whose build carries the release version, is left to the tag.
- An upload happens only after the plugin's tests and the plugin verifier have passed in the run that built the plugin. This change builds on `intellij-ci-tests`, after which the package job waits for the plugin tests on Linux, Windows and macOS, and the publish job waits for the verifier gate in the code-quality job.
- The plugin's change notes stay its changelog section as long as that fits the Marketplace's limit of 65,535 characters. A longer section, such as the one of 2.8.0 with 481 commits, is reduced to the subject lines of the features, bug fixes and performance improvements, with a link to the full list.
- The plugin is uploaded unsigned, as the manual uploads were.
- A rejected upload fails the publish job, and the log shows the Marketplace's answer.

Not part of this change: signing the plugin; changing how the plugin is built, apart from its change notes; the Gradle task `publishPlugin`, which stays as it is for manual use; a description of the channel `dev` in the user docs, which don't describe the VS Code prereleases either.

## Capabilities

### New Capabilities

- `release-publishing`: what the CI publishes when a version is tagged and as dev builds between releases, where, and into which channel. This change adds the JetBrains plugin.

### Modified Capabilities

_None._

## Impact

- `scripts/publish.py`: the upload of `dist/robotcode4ij-<version>.zip` to the Marketplace's upload API, with the channel taken from the version.
- `.github/workflows/build-test-package-publish.yml`: the name of the publish step, which now publishes the plugin too. The step already passes `PUBLISH_TOKEN` and runs only on version tags, and the publish job already needs `code-quality` and `package`.
- New: `.github/workflows/publish-dev.yml` and `scripts/publish_dev.py` with the hatch script `build:publish-dev` in `hatch.toml`, for the nightly dev builds.
- `intellij-client/build.gradle.kts`: the change notes, shortened when the changelog section is too long for the Marketplace.
- The channel `dev` still holds the releases 1.3.0 to 2.7.0 from the manual uploads. If the channel should hold dev builds only, the maintainer removes them on the Marketplace by hand.
- The secret `JETBRAINS_MARKETPLACE_TOKEN` (set since 2025-05-28) has to be a valid permanent token of the plugin's owner; the first tag after this change shows whether it is.
- Order: `intellij-ci-tests` has to be implemented first.
