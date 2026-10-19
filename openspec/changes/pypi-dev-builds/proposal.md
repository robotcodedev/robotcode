# Proposal

## Why

Between two releases, the latest tested build of `main` reaches VS Code, VSCodium and JetBrains users every night as a dev build, but not the Python packages on PyPI. Users of the `robotcode` command line, for example `robotcode analyze` or `robotcode runner` in a CI pipeline, can't try a fix before it is released.

## What Changes

- Every night, and when the maintainer starts it by hand, the publish workflow also uploads the Python packages of the latest successful build of `main` to PyPI, unless PyPI has that version already. This works like the dev builds of the VS Code extension and the JetBrains plugin. With no new build since the last upload, nothing is uploaded.
- The dev versions are the ones every build without a tag already gives its Python packages, for example `2.8.0.dev508`. That is the same number as the VS Code dev build `2.7.100508` and the JetBrains dev build `2.8.0-dev.508`. A release version is skipped, its tag publishes it.
- The eleven packages that `robotcode` depends on are uploaded first, and the package `robotcode` itself last, only if they all arrived. So a dev version of `robotcode` is never on PyPI without the exact versions it requires.
- The upload is a step of its own. A failure at PyPI doesn't keep the other stores from getting their dev builds, and a failure at another store doesn't stop the PyPI upload.
- Users get a dev version only when they ask for it: `pip install robotcode` keeps installing the latest release.

Not part of this change:
- trusted publishing (OIDC) for PyPI;
- a description of the dev versions in the user docs, which don't describe the other dev builds either.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `release-publishing`: adds the nightly upload of the Python dev versions to PyPI. The capability is a main spec since `vscode-dev-builds` was archived; `intellij-marketplace-publish` and `publish-workflow`, not archived yet, add to it too. This change only adds requirements.

## Impact

- `scripts/publish_dev.py`: the target `python`. It downloads the artifacts `python-packages` and `wheel-packages`, looks up the version on PyPI, and uploads with `hatch publish`, the package `robotcode` last.
- `.github/workflows/publish.yml` (from `publish-workflow`): a third upload step in the job `dev`, with the secrets `PYPI_USERNAME` and `PYPI_PASSWORD`.
- `hatch.toml`: the build environment declares `packaging`, which `publish_dev.py` now imports, instead of getting it only through another dependency.
- PyPI gets a dev version of each of the 12 projects on every day with a new build of `main`. In the year up to 2026-10-18, that would have been 116 days.
- Order: implement after `publish-workflow`, which creates `publish.yml` and its job `dev`.
