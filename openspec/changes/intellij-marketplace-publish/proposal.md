# Proposal

## Why

On every version tag the CI publishes the VS Code extension and the Python packages, and attaches the JetBrains plugin to the GitHub release, but the plugin reaches the JetBrains Marketplace only when the maintainer uploads it by hand. PyCharm and IntelliJ IDEA users get a release later than VS Code users, and prereleases never reach them. The publish step already receives the Marketplace token (`PUBLISH_TOKEN` from the secret `JETBRAINS_MARKETPLACE_TOKEN`), but `scripts/publish.py` doesn't use it.

## What Changes

- On a version tag, the CI uploads the JetBrains plugin to the JetBrains Marketplace: the zip that the package job built, the same file that the GitHub release gets.
- A release version goes to the Marketplace's default channel. A prerelease version, whatever its pre-release label (for example `2.9.0-dev.3`), goes to the channel `dev`. Users who want prereleases add `https://plugins.jetbrains.com/plugins/dev/list` as a plugin repository in their IDE.
- Builds without a version tag publish nothing, although their versions carry a `-dev.N` label too.
- The upload happens only after the plugin's tests and the plugin verifier have passed. This change builds on `intellij-ci-tests`, after which the package job waits for the plugin tests on Linux, Windows and macOS, and the publish job waits for the verifier gate in the code-quality job.
- The plugin is uploaded unsigned, as the manual uploads were.
- A rejected upload fails the publish job, and the log shows the Marketplace's answer.

Not part of this change: signing the plugin; publishing builds without a version tag, for example nightly; changing how the plugin is built; the Gradle task `publishPlugin`, which stays as it is for manual use; a description of the channel `dev` in the user docs, which don't describe the VS Code prereleases either.

## Capabilities

### New Capabilities

- `release-publishing`: what the CI publishes when a version is tagged, where, and into which channel. This change adds the JetBrains plugin.

### Modified Capabilities

_None._

## Impact

- `scripts/publish.py`: the upload of `dist/robotcode4ij-<version>.zip` to the Marketplace's upload API, with the channel taken from the version.
- `.github/workflows/build-test-package-publish.yml`: the name of the publish step, which now publishes the plugin too. The step already passes `PUBLISH_TOKEN` and runs only on version tags, and the publish job already needs `code-quality` and `package`.
- The secret `JETBRAINS_MARKETPLACE_TOKEN` (set since 2025-05-28) has to be a valid permanent token of the plugin's owner; the first tag after this change shows whether it is.
- Order: `intellij-ci-tests` has to be implemented first.
