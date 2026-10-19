# Proposal

## Why

Two workflows upload RobotCode to the stores:
- the `publish` job of `build-test-package-publish.yml` uploads releases on version tags to the VS Code Marketplace, Open VSX, PyPI and the JetBrains Marketplace;
- `publish-dev.yml` uploads the nightly dev builds.

Open VSX's trusted publishing, which replaces stored tokens with a token the workflow gets from GitHub, trusts exactly one workflow file per extension. With two workflows, only one of them could publish that way. The trusted publishing that the VS Code Marketplace has announced is also configured for a repository and a workflow.

Also, a failed release upload goes unnoticed: `scripts/publish.py` swallows the errors of `vsce`, `ovsx` and `hatch publish`, and the job stays green.

## What Changes

- All publishing moves into one workflow, `publish.yml` (the renamed `publish-dev.yml`, now named "publish"):
  - every night and on a manual start, it publishes the dev builds as now;
  - after a successful build of a version tag, it creates the GitHub release with the packages of that build and uploads the release to the VS Code Marketplace, Open VSX, PyPI and the JetBrains Marketplace, with the same rules as before.
- The build workflow `build-test-package-publish.yml` becomes `build-test-package.yml`, named "build test and package", and loses its `publish` job.
- The publish workflow publishes a release only for a successful build of a version tag pushed to this repository, never for a build of a pull request or of a push to a branch.
- A failed release upload no longer goes unnoticed. The upload still tries every other store, also when creating the GitHub release failed, then fails the job, and the log shows the store's answer.
- Every release upload skips a version that its store already has, so a re-run of the release job after a failure uploads only what is missing.
- The README badge, the CI workflow named in `CONTRIBUTING.md`, the run lookup of the dev builds and the open changes `agent-plugin-release` and `intellij-ui-tests` follow the new names.

Not part of this change:
- trusted publishing (OIDC) for any store, which gets a change of its own;
- the order in which `hatch publish` uploads the Python packages.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `release-publishing`:
  - adds when and by which workflow a release is published, that only version tags of this repository publish one, that a failed release upload fails the run without stopping the other uploads, and that a re-run uploads only what is missing;
  - changes the JetBrains requirement "A version tag publishes the JetBrains plugin to the Marketplace": the uploaded file is the one the tag's build packaged, not one the uploading run packaged.

  The capability is a main spec since `vscode-dev-builds` was archived. The JetBrains requirement that this change modifies comes with `intellij-marketplace-publish`, which isn't archived yet.

## Impact

- `.github/workflows/build-test-package-publish.yml` → `build-test-package.yml`: the new name; the `publish` job removed.
- `.github/workflows/publish-dev.yml` → `publish.yml`:
  - the new name;
  - the `workflow_run` trigger;
  - a release job with the steps of the old `publish` job, whose upload also runs when only the GitHub release failed.
- `scripts/publish.py`: every upload is tried and skips a version its store already has, and failures fail the script at the end. The lookup of the JetBrains versions moves here from `scripts/publish_dev.py`. The PyPI credentials come from environment variables instead of the command line.
- `scripts/publish_dev.py`: looks up the runs of `build-test-package.yml`.
- `README.md`: the build status badge and its link.
- `CONTRIBUTING.md`: the file name of the CI workflow.
- `openspec/changes/agent-plugin-release` and `openspec/changes/intellij-ui-tests`: the workflow and job they name.
- GitHub lists the earlier runs under the old workflow names. The dev builds find a successful run of `build-test-package.yml` only after its first green run on `main`.
