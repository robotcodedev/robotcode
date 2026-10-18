# Proposal

## Why

Between two releases, PyCharm and IntelliJ IDEA users can get the latest tested build of `main` every night from the JetBrains channel `dev`. VS Code users can't: the CI publishes the VS Code extension only on version tags. Its builds on `main` carry versions like `2.8.0-dev.499`, which the VS Code Marketplace rejects, because it accepts only `major.minor.patch`.

## What Changes

- Every night, and when the maintainer starts it by hand, the existing workflow "publish dev build" also publishes the VS Code extension of the latest successful CI run on `main` as a pre-release. It goes to the VS Code Marketplace and to Open VSX, unless that version is there already.
- Builds without a tag give the extension a version the Marketplace accepts. With `A.B.C` as the version of the last tag and `N` as the number of first-parent commits since that tag, the version is `A.B.((C + 1) × 100000 + N)`. For example, `2.8.0-dev.499` becomes `2.7.100499`, and after a fix release 2.7.1 the builds continue at `2.7.200001`. N is the same number as in `-dev.N`.
- Only the extension's own version changes. The Python packages bundled in the extension, the Python packages built for PyPI and the JetBrains plugin keep `2.8.0-dev.499`.
- Both stores get the same VSIX file, the one the CI run built and tested.
- Builds of a tagged commit keep their version, so the release commit on `main` builds the release version as before. The nightly upload skips it, and the version reaches the stores through its tag, as for the JetBrains plugin.
- A failed upload to one store fails the workflow, but doesn't keep the other store or the JetBrains plugin from getting the dev build.
- The extension no longer shows its "What's New" notification after an update to a dev build. After an update to a release it shows it as before.

Not part of this change:
- dev releases of the Python packages on PyPI;
- authentication without the stored tokens `VSCE_PAT` and `OVSX_PAT`;
- publishing prerelease tags to the VS Code Marketplace;
- a description of pre-releases in the user docs.

## Capabilities

### New Capabilities

- `vscode-update-notification`: when the VS Code extension tells the user that it was updated and points to what's new.

### Modified Capabilities

- `release-publishing`: adds the VS Code extension's dev builds, their version, and their nightly upload to the VS Code Marketplace and Open VSX. The capability is introduced by the change `intellij-marketplace-publish`, which isn't archived yet. This change only adds requirements.

## Impact

- `scripts/tools.py`: the version of a VS Code dev build, from the last tag and the commits since it.
- `scripts/package.py`: `vsce package` with that version, `--no-update-package-json` and `--pre-release` for builds without a tag.
- `scripts/publish_dev.py`: a target argument (`jetbrains`, `vscode`) and the upload of the VSIX with `vsce publish` and `ovsx publish`.
- `hatch.toml`: the script `publish-dev` passes its arguments on.
- `.github/workflows/publish-dev.yml`:
  - Node.js and the node modules for `vsce` and `ovsx`;
  - one step per target, the second running also when the first failed;
  - the secrets `VSCE_PAT` and `OVSX_PAT`.
- `vscode-client/extension/index.ts`: no "What's New" notification for dev builds.
- `VSCE_PAT` has to be a global Azure DevOps token, as the VS Code docs require for Marketplace tokens, and global tokens stop working on 2026-12-01. From then on, the VS Code Marketplace upload fails both here and on version tags, until the publishing uses another authentication.
