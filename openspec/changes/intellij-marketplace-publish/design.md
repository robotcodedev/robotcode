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

## Goals / Non-Goals

**Goals:**

- The plugin file that was tested, verified and attached to the GitHub release is the file the Marketplace gets.
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

### No signing

The plugin is uploaded unsigned, as the maintainer decided; the `signing` block in `build.gradle.kts` stays as it is.

Alternative: signing with a certificate, which needs three more secrets. It can come later and would sign the zip in the package job, so this upload would not change.

### The gate comes from intellij-ci-tests

This change adds no `needs`. The publish job already needs `code-quality`, which runs the verifier gate, and `package`. After `intellij-ci-tests`, `package` also needs `test-jetbrains`.

## Risks / Trade-offs

- [The secret holds an expired token, or no permanent token of the plugin's owner] → The first tag after the change shows it in the failed step. The maintainer creates a new permanent token under "My Tokens" in the Marketplace profile, updates the secret, and uploads that version by hand from the GitHub release.
- [The upload fails while the other packages are already published] → The step fails visibly. The zip from the GitHub release can be uploaded by hand, as today.
- [Two channel rules] → The mapping in `build.gradle.kts` only applies to a manual `publishPlugin`. For RobotCode's `-dev.N` prereleases both rules give `dev`.
- [Unsigned plugin] → According to JetBrains, the IDE shows a warning on installation. That is the state of the manual uploads so far, and signing can be added later in the package job.
- [The Marketplace processes an update after the upload] → The job reports the upload. When the version becomes available depends on the Marketplace's processing, as for manual uploads.
- Side finding, not part of this change: `run()` in `publish.py` prints failed uploads of `vsce`, `ovsx` and `hatch publish` without failing the job.

## Migration Plan

1. Implement `intellij-ci-tests` first.
2. Before the first tag after this change, check that `JETBRAINS_MARKETPLACE_TOKEN` holds a valid permanent token.
3. From then on, don't upload by hand.

Rollback: remove the upload from `publish.py`.
