# Design

## Context

See proposal.md for the motivation. The state that shapes the approach:

- **The workflow** (`.github/workflows/build-test-package-publish.yml`):
  - `package` runs `hatch run build:package` and uploads `intellij-client/build/distributions/robotcode4ij-<version>.zip` as the artifact `intellij-package`.
  - `publish` needs `code-quality` and `package`. It downloads all packages into `dist/`, creates the GitHub release with `dist/*`, and runs `hatch run build:publish` with `VSCE_PAT`, `OVSX_PAT`, `PYPI_USERNAME`, `PYPI_PASSWORD` and `PUBLISH_TOKEN` (from the secret `JETBRAINS_MARKETPLACE_TOKEN`). Both steps run only for tags `v*`.
  - In runs without a tag, the step "update versions from git" writes a `-dev.N` version into `package.json`, the `pyproject.toml` files and `intellij-client/gradle.properties`; for `main` on 2026-10-16 that was `2.8.0-dev.466` (`scripts/tools.py`, commitizen with `version_scheme = "semver2"`).
- **`scripts/publish.py`** runs `vsce publish` only for versions without a pre-release label, and `ovsx publish` and `hatch publish` always. Its helper `run()` calls `subprocess.run` without `check` and catches every exception, so a failed upload is only printed and the job stays green.
- **The plugin build**:
  - `scripts/package.py` installs `bundled/libs` with pip before it runs `gradle buildPlugin`, and the sandbox copies `bundled/**` into the plugin.
  - `build.gradle.kts` configures `publishing`: the token comes from `PUBLISH_TOKEN`, and the channel is the version's pre-release label (`dev` → `dev`, `alpha` → `alpha`, none → `default`).
  - It also configures `signing` from three environment variables that the workflow doesn't set, and makes `publishPlugin` depend on `patchChangelog`.
- **The Marketplace's upload API** (Marketplace docs, "Plugin upload API"):
  - `POST https://plugins.jetbrains.com/api/updates/upload` with `Authorization: Bearer <permanent token>` and the form fields:
    - `xmlId`, the `<id>` of plugin.xml (`dev.robotcode.robotcode4ij`), or instead `pluginId` (26216);
    - `file`;
    - `channel`, where an empty channel means the default one.
  - At most 400 MB per upload; the plugin zip of v2.7.0 has 3.8 MB.
- **Channels** (Plugin SDK docs, "Publishing a Plugin"): a channel can have any name. Users add `https://plugins.jetbrains.com/plugins/<channel>/list` as a plugin repository in their IDE. The first publication of a plugin must be uploaded by hand, which happened long ago.
- **Signing** (Plugin SDK docs, "Plugin Signing"): signing by the author is optional. The docs say that without it "a warning dialog will appear in the IDE during installation". Uploading the author's public key to the Marketplace is "not available yet".
- **`intellij-ci-tests`**, which this change builds on:
  - `package` will need the new job `test-jetbrains`, with the plugin tests on Linux, Windows and macOS;
  - `code-quality` will run the plugin verifier as a gate.
- **Versions of builds on `main`:** every build without a tag gets `X.Y.Z-dev.N`, the next version and the number of first-parent commits since the last tag. The release commit itself, pushed to `main` together with its tag, builds the release version, because no commit follows the tag.
- **The channel `dev` on 2026-10-17** (public API `https://plugins.jetbrains.com/api/plugins/26216/updates?channel=dev`): 1.3.0-dev.4 and 1.3.0-dev.5 from June 2025, and the releases 1.3.0 to 2.7.0 except 2.2.0. The maintainer uploaded each release by hand into the default channel and seconds later into `dev`.
- **How other plugins publish dev builds without a tag:**
  - IdeaVim (JetBrains): a TeamCity build "Publish Dev Build" runs daily at 02:00 on `master`. The version is the next minor version with `-dev.<commits since the last release>`, the channel `Dev`.
  - LSP4IJ (Red Hat): the GitHub workflow "Publish Nightly Build" runs daily at 01:00 and by hand. It skips the upload when `HEAD` hasn't changed since the last night (an `actions/cache` entry keyed on the commit), builds the plugin again with a timestamp version (`0.21.1-<date>-<time>`) and publishes it to `nightly` with `publishPlugin`, without running the tests.
  - The IntelliJ Platform Plugin Template publishes only from GitHub releases, that is from tags.
- **How the IDE compares versions** (`VersionComparatorUtil` in intellij-community): it splits a version into numbers and words. `dev` is a word it doesn't know, which ranks above the end of a version, so `2.8.0-dev.466` counts as newer than `2.8.0`. `alpha`, `beta`, `rc`, `eap`, `pre`, `preview` and `snapshot` rank below the end, so with them the release would count as newer.

## Goals / Non-Goals

**Goals:**

- The plugin file that was tested, verified and attached to the GitHub release is the file the Marketplace gets.
- Between releases, the channel `dev` gets the latest tested and verified build of `main` once a day, without a tag.
- A problem with the Marketplace can't keep the VS Code extension and the Python packages from being published.
- A failed Marketplace upload shows up as a failed job.

**Non-Goals:**

- Changing how the existing uploads report failures. That `run()` swallows them is a separate finding, see Risks.
- Separate jobs per marketplace or registry.

## Decisions

### Upload the packaged zip through the Marketplace's API

`scripts/publish.py` uploads `dist/robotcode4ij-<version>.zip` with `curl` to the upload API:
- The token goes into the `Authorization` header from the environment variable `PUBLISH_TOKEN`. The shell expands it, so it isn't part of the command line that the script prints.
- The form fields are `xmlId=dev.robotcode.robotcode4ij`, the file, and the channel.
- `curl --fail-with-body` ends with an error on an HTTP error status and prints the Marketplace's answer.

Alternatives:
- `gradle publishPlugin` in the publish job. It builds the plugin again, without the `bundled/libs` that `package.py` installs first, so the upload would not be the tested zip from the GitHub release. It also runs `patchChangelog`, which rewrites `CHANGELOG.md`.
- `publishPlugin` with its `archiveFile` set to the downloaded zip. That still needs a configured Gradle project in the publish job and still runs `patchChangelog`, for what is one HTTP upload.
- An upload written in Python. The `build` environment has no HTTP client library (its dependencies are GitPython, semantic-version, commitizen and git-cliff), and multipart encoding with the standard library takes more code than one `curl` call. `curl` is installed on GitHub's Ubuntu runners.

### The channel comes from the version

A version with a pre-release label goes to `dev`. Otherwise the field stays empty, which means the default channel. `publish.py` already reads the version with `get_version()` and checks `version.prerelease` to skip `vsce publish` for prereleases.

Alternative: the label as the channel name, as `build.gradle.kts` does for `publishPlugin`. The maintainer wants every prerelease in `dev`.

### The upload comes last and fails the step

The Marketplace upload runs after `vsce`, `ovsx` and `hatch publish`, so a problem with the token or the Marketplace can't hold back the VS Code extension and the Python packages. Unlike those uploads it doesn't go through `run()`. It calls `subprocess.run` with `check=True`, so a rejected upload fails the step. The maintainer then sees that the plugin didn't arrive, and can upload the zip from the GitHub release by hand, as before.

Alternatives:
- The upload first. A Marketplace outage would then hold back the other releases.
- A job of its own, which could be rerun alone. It would need its own checkout, Python environment and the version logic of `publish.py`.

### Dev builds: every night the latest green build of main

The maintainer decided on 2026-10-17 that the channel `dev` gets dev builds without a tag, and that releases go to the default channel only.

- **Workflow:** `.github/workflows/publish-dev.yml` runs on a schedule at 02:23 UTC and by `workflow_dispatch`. GitHub delays scheduled runs at the start of an hour under load, so the minute is not 0. It needs `actions: read` for the runs and artifacts of the build workflow and `contents: read`, and a `concurrency` group keeps a manual start and the schedule from uploading at the same time.
- **`scripts/publish_dev.py`** (`hatch run build:publish-dev`):
  - `gh run list` finds the most recent run of `build-test-package-publish.yml` for a push to `main` that succeeded; `gh run download` puts its artifact `intellij-package` into `dist/`.
  - The version comes from the file name. A version without a pre-release label is skipped: it comes from the release commit, and its tag publishes it.
  - The version is also skipped when the Marketplace's public API lists it in the channel `dev`.
  - Otherwise `publish_jetbrains_plugin()` uploads it, which sends a version with a pre-release label to `dev`.
- **Version:** the build's `X.Y.Z-dev.N` stays, the same version as the VS Code extension and the Python packages of that build, and the same scheme as IdeaVim's dev builds. The IDE counts it as newer than the release with the same `X.Y.Z`, so a dev user isn't offered 2.8.0 itself, but the first dev build after it. IdeaVim and LSP4IJ have the same property.

Alternatives:
- An upload from every successful push, in the publish job of the build workflow. It needs fewer parts, but would upload several times a day: on 2026-10-16, 6 pushes to `main`, 3 of them successful.
- A nightly build of its own, like LSP4IJ's. It would not run the tests, and would not upload the file that the build workflow tested and verified.
- A schedule in the build workflow. It would run the whole test matrix again every night.
- LSP4IJ's cache entry for the last commit instead of asking the Marketplace. The Marketplace's list also covers a failed upload, which the next night retries, and versions uploaded by hand.
- A timestamp version, or a label that the IDE ranks below the release, such as `eap`. The plugin would then carry a different version than the VS Code extension and the Python packages of the same build.

### Change notes that the Marketplace accepts

The first manual run of "publish dev build" (2026-10-17) reached the Marketplace, which rejected the plugin: "The value of the '<change-notes>' parameter is too long. Its length is 209290 which is more than maximum 65535 characters long."

- **Where the change notes come from:** `build.gradle.kts` renders the changelog section of the plugin's version, or the unreleased section for a dev build, as HTML. The package job regenerates `CHANGELOG.md` with git-cliff first, so for 2.8.0-dev.479 the section held all 481 commits since v2.7.0, each with its commit message body:

  | Section | Characters | Entries |
  |---|---|---|
  | Features | 41,281 | 64 |
  | Bug Fixes | 51,472 | 92 |
  | Documentation | 109,760 | 262, 215 of them `openspec` |
  | Performance | 1,514 | 3 |
  | Refactor | 4,595 | 9 |

  The change notes of 2.7.0, 16 commits after 2.6.2, had 5,524 characters. The section of the release 2.8.0 holds the same entries as the dev build, so its upload would fail too, by hand as well.
- **Decision** (maintainer, 2026-10-17): when the rendered section has at most 65,535 characters, it stays the change notes. Otherwise the change notes list only Features, Bug Fixes and Performance, each entry reduced to its first line, the subject with its commit link, and end with a sentence that links to the full list: the commit history of `main` for the unreleased section, `CHANGELOG.md` for a release. If that is still too long, entries are dropped from the end. For 2.8.0-dev.479 this gives about 32,000 characters.
- **Releases too:** the package job builds the zip for tags with the same `build.gradle.kts`, and the publish job uploads that zip unchanged, so a release with a long section gets the same short change notes.
- The section headings that git-cliff writes carry an ordering prefix (`<!-- 0 -->Features`), so the sections are matched by the text after it.

Alternatives:
- Always the short form. Small releases would lose the commit message bodies, which are written for users.
- Only a sentence and the link when the section is too long. The release 2.8.0 and nearly every dev build would show no list.
- Leaving `openspec` commits out of the changelog in `cliff.toml`. That changes `CHANGELOG.md` and the GitHub release notes, and Features and Bug Fixes alone exceed the limit already.

### No signing

The plugin is uploaded unsigned, as the maintainer decided; the `signing` block in `build.gradle.kts` stays as it is.

Alternative: signing with a certificate, which needs three more secrets. It can come later and would sign the zip in the package job, so this upload would not change.

### The gate comes from intellij-ci-tests

This change adds no `needs`. The publish job already needs `code-quality`, which runs the verifier gate, and `package`. After `intellij-ci-tests`, `package` also needs `test-jetbrains`. The nightly upload takes the plugin only from a run that succeeded, so all jobs of that run passed, the plugin tests and the verifier gate among them.

## Risks / Trade-offs

- [The secret holds an expired token, or no permanent token of the plugin's owner] → The first tag after the change shows it in the failed step. The maintainer creates a new permanent token under "My Tokens" in the Marketplace profile, updates the secret, and uploads that version by hand from the GitHub release.
- [The upload fails while the other packages are already published] → The step fails visibly. The zip from the GitHub release can be uploaded by hand, as today.
- [Two channel rules] → The mapping in `build.gradle.kts` only applies to a manual `publishPlugin`. For RobotCode's `-dev.N` prereleases both rules give `dev`.
- [Unsigned plugin] → According to JetBrains, the IDE shows a warning on installation. That is the state of the manual uploads so far, and signing can be added later in the package job.
- [The Marketplace processes an update after the upload] → The job reports the upload. When the version becomes available depends on the Marketplace's processing, as for manual uploads.
- [The Marketplace's list doesn't show an upload yet, and a manual start uploads the same version again] → The Marketplace rejects the second upload and the run fails visibly; the first upload stays.
- [No run on `main` succeeds for a while] → The nightly upload finds the last successful build already in `dev` and uploads nothing. After 90 days the artifact expires; the download then fails and the run fails visibly.
- [GitHub disables the schedules of a public repository after 60 days without activity] → Not a concern while RobotCode is developed; a manual start still works.
- [The channel `dev` holds the releases from the manual uploads] → They don't affect the uploads. The maintainer removes them by hand if the channel should hold dev builds only.
- Side finding, not part of this change: `run()` in `publish.py` prints failed uploads of `vsce`, `ovsx` and `hatch publish` without failing the job.

## Migration Plan

1. Implement `intellij-ci-tests` first.
2. Before the first tag after this change, check that `JETBRAINS_MARKETPLACE_TOKEN` holds a valid permanent token.
3. After the push, start "publish dev build" by hand once; it publishes the latest successful build of `main` to `dev`.
4. From then on, don't upload by hand.

Rollback: remove the upload from `publish.py`, and the workflow `publish-dev.yml`.
