# Tasks

## 1. Version of VS Code dev builds

- [x] 1.1 In `scripts/tools.py`, move the lookup of the last tag, its version and the first-parent commit count since it out of `get_current_version_from_git()` into a helper that both use. Add a function that returns the extension version `A.B.((C + 1) × 100000 + N)` for a commit after the last tag, and nothing for a tagged commit. Keep the 100000 in a constant whose comment points to `vscode-client/extension/index.ts`.

  Verify:
  - In the repository, the function returns `2.7.1<N as five digits>`, with N from `git rev-list --count --first-parent v2.7.0..HEAD`, and `get_version()` still returns `2.8.0-dev.<N>`.
  - In a scratchpad clone, checked out at `v2.7.0`, it returns nothing.
  - In the same clone, with a local tag `v2.7.1` and one commit after it, it returns `2.7.200001`.
  - `hatch run lint:style` and `hatch run lint:typing` pass.
- [x] 1.2 In `scripts/package.py`, package the extension with `npx vsce package <version> --no-update-package-json --pre-release -o ./dist` when the function from 1.1 returns a version, and as before otherwise.

  Verify the command as `package.py` builds it, with the output in the scratchpad:
  - the VSIX is named `robotcode-<version>.vsix`;
  - the identity version in its `extension.vsixmanifest` and the version in its `extension/package.json` are that version;
  - the manifest has the property `Microsoft.VisualStudio.Code.PreRelease`;
  - `git diff package.json` stays empty;
  - `hatch run lint:style` and `hatch run lint:typing` pass.

## 2. Nightly upload

- [x] 2.1 Give `scripts/publish_dev.py` a required target argument (argparse), `jetbrains` or `vscode`, and the hatch script `publish-dev` in `hatch.toml` the placeholder `{args}`.
  - `jetbrains` keeps the current behavior.
  - `vscode` downloads the artifact `vscode-package` of the most recent successful run on `main` into `dist/`, expects exactly one `robotcode-*.vsix`, and skips with a message a VSIX whose manifest lacks the pre-release property.
  - Otherwise it runs `npx vsce publish --packagePath <vsix> --pre-release --skip-duplicate`, then `npx ovsx publish <vsix> --skip-duplicate` also when the first failed. It ends with an error that names the failed stores.

  Verify with stubs for `gh`, `npx` and `curl` early on `PATH` that record their arguments, and dummy tokens:
  - a pre-release VSIX is uploaded with both commands, in this order, with the downloaded file;
  - a VSIX without the property uploads nothing, and the script ends successfully;
  - with a failing `vsce`, `ovsx` is still called, and the script exits with an error that names the VS Code Marketplace;
  - `jetbrains` uploads 2.8.0-dev.470 with `channel=dev` and skips the release version 2.8.0, as before;
  - without a target, argparse ends with its usage message;
  - `hatch run lint:style` and `hatch run lint:typing` pass.
- [x] 2.2 In `.github/workflows/publish-dev.yml`, before the upload steps, set up Node.js 26 with the npm cache, update npm and install the node modules, as the build workflow does. Then add two steps:
  - `hatch -q run build:publish-dev jetbrains` with `GH_TOKEN`, `GH_REPO` and `PUBLISH_TOKEN`;
  - `hatch -q run build:publish-dev vscode` with `if: ${{ !cancelled() }}`, `GH_TOKEN`, `GH_REPO`, `VSCE_PAT` and `OVSX_PAT`.

  Verify that the file parses as YAML, and that each upload step gets only its own secrets.

## 3. "What's New" for dev builds

- [x] 3.1 In `vscode-client/extension/index.ts`, don't show the "What's New" notification when the patch number of the extension's version is 100000 or more, and still store the version in `robotcode.lastVersion`. A comment points to the constant in `scripts/tools.py`. Verify that `npm run lint` and `npm run compile` pass.

## 4. Verification with the maintainer

- [ ] 4.1 After the push, check the artifact `vscode-package` of the next run on `main`:
  - it holds `robotcode-2.7.1NNNNN.vsix`, whose manifest and `extension/package.json` carry that version;
  - its manifest has the property `Microsoft.VisualStudio.Code.PreRelease`;
  - its `extension/bundled/libs/robotcode/cli/__version__.py` holds the run's `2.8.0-dev.N`.
- [ ] 4.2 The maintainer starts "publish dev build" by hand. Check:
  - the log shows the answers of the VS Code Marketplace and Open VSX;
  - both stores list the version as a pre-release;
  - the JetBrains step behaves as before;
  - a second start uploads nothing.

  Check the first scheduled run the next day.

## Workflow follow-up

- Archive the change after the verification. The capability `release-publishing` comes from `intellij-marketplace-publish`. This change only adds requirements and carries the same Purpose, so either change can be archived first.
