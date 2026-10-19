# Design

## Context

See proposal.md for the motivation. The state that shapes the approach, checked on 2026-10-18:

- **Versions of builds without a tag** (`scripts/tools.py`): `get_current_version_from_git()` asks commitizen for the last tag (`cz version --project --tag`), counts the first-parent commits since it with `git rev-list`, and returns the next version with that count as `-dev.N`. At a tagged commit the count is 0, and it returns the tag's version. In runs without a tag, the step "update versions from git" writes this version into `package.json` (`npm version`), the `pyproject.toml` files and `intellij-client/gradle.properties`.
- **Packaging** (`scripts/package.py`):
  - It installs the build's Python packages into `bundled/libs`, then runs `npx vsce package [--pre-release] -o ./dist`, with `--pre-release` when the version has a pre-release label.
  - The artifact `vscode-package` of the last green run on `main` is `robotcode-2.8.0-dev.483.vsix`. Its manifest has the identity version 2.8.0-dev.483 and the property `Microsoft.VisualStudio.Code.PreRelease`. It bundles `robotcode_core-2.8.0.dev483.dist-info`, and `robotcode/cli/__version__.py` says `2.8.0-dev.483`.
- **Release uploads** (`scripts/publish.py`, only on version tags): `vsce publish` for versions without a pre-release label, and `ovsx publish` always. Both go through `run()`, which doesn't fail on errors.
- **Nightly dev builds** (`.github/workflows/publish-dev.yml`, `scripts/publish_dev.py`, from `intellij-marketplace-publish`):
  - It runs at 02:23 and by hand, with `actions: read` and `contents: read`, Python and Hatch only.
  - It finds the latest successful push run on `main` with `gh run list`, downloads `intellij-package`, and skips a release version.
  - It also skips a version that the channel `dev` already lists, and otherwise uploads with `publish_jetbrains_plugin()`.
- **VS Code Marketplace**:
  - The publishing docs say: only `major.minor.patch`, "semver pre-release tags are not supported", and full semver support "will be available in the future". The requests for it (microsoft/vsmarketplace#264, #50) are open without a timeline.
  - vsce 4.0.0 and 4.0.1-3 reject a version with a pre-release label in `publish`, but not in `package`.
  - Pre-release and release versions must differ. VS Code updates an extension to the highest version available. A user on the pre-release version also gets a higher release and stays eligible for later, higher pre-releases.
  - The Marketplace accepts a release below an existing pre-release: rust-analyzer published the release 0.3.3081 three hours after the pre-release 0.4.3080 (2026-10-12).
  - The documented convention, even minor numbers for releases and odd ones for pre-releases, is what rust-analyzer (`0.3.N` / `0.4.N`) and ms-python (`2026.10.0` / `2026.11.2026101501`) use.
- **Open VSX** accepts versions with a pre-release label. It lists the old `1.3.0-dev.2` to `1.3.0-dev.6` as pre-releases, which `publish.py` uploaded without `--pre-release`.
- **The tools** (vsce 4.0.0, ovsx 1.3.0 in `node_modules`):
  - `vsce package <version> --no-update-package-json` writes the version only into the VSIX: its `package.json`, its manifest and its file name.
  - `vsce publish --packagePath` rejects a version argument. With `--pre-release` it only checks that the VSIX was packaged as a pre-release. `--skip-duplicate` skips a version the Marketplace has.
  - `ovsx publish <file>` ignores `--pre-release` and `--packageVersion` for a packaged file, and has `--skip-duplicate`.
  - vsce reads the token from `VSCE_PAT`, ovsx from `OVSX_PAT`. Both secrets exist.
- **Release cycles**: across the 328 release tags, the longest finished cycle had 176 first-parent commits (2.5.1 → 2.6.0). The one since 2.7.0 had 499 on 2026-10-18. The highest patch number ever released is 28.
- **Hatch 1.18** passes extra command line arguments to a script only where the script has `{args}`. Checked with a probe environment.
- **"What's New"** (`vscode-client/extension/index.ts`): on activation, the extension compares its `packageJSON.version` with the global state `robotcode.lastVersion`. If they differ and `robotcode.showWhatsNewOnUpdate` is on, it shows the notification. Then it stores the current version.

## Goals / Non-Goals

**Goals:**

- The version of a dev build tells which build it is: `2.7.100499` is the build `2.8.0-dev.499`.
- Every minor and major release ranks above the dev builds before it, so users on the pre-release version get it.
- The VSIX in the stores is the file the CI run tested and uploaded as its artifact.

**Non-Goals:**

- Changing builds of tagged commits or the release uploads in `publish.py`, including their `run()` helper.
- Replacing `VSCE_PAT` and `OVSX_PAT`.

## Decisions

### The version: a block per fix release, the dev number inside it

Builds without a tag give the extension `A.B.((C + 1) × 100000 + N)`. `A.B.C` is the version of the last tag, and `N` is the count of first-parent commits since it, the number in `-dev.N`.

- **The last tag as base:** a minor or major release is higher than every dev build before it, so users on the pre-release version get the release and its notification, then the next dev build. It doesn't depend on which version commitizen predicts.
- **`(C + 1) ×`:** N starts at 1 again after every tag. Each fix release opens a new block above the previous one, so the versions keep rising across fix releases. The `+ 1` keeps dev builds away from real patch numbers.
- **100000:** a block holds 99999 commits, 200 times the longest cycle so far. With the highest patch number ever released, 28, the patch stays below 3 million, far below the largest patch number seen on the Marketplace (ms-python's 2026101501). As a power of ten, the leading digits show the block and the last five N.
- **Fix releases** rank below the dev builds before them. With integer versions nothing can rank between 2.7.0 and 2.7.1. Users on the pre-release version already have the fixes from the dev builds.

Alternatives:
- The minor of the predicted next version plus the total commit count (`2.8.3381`). Every release would rank below the dev builds before it. A release that differs from the prediction, for example 2.8.0 after a predicted 3.0.0, would leave pre-release users on the highest dev build.
- The last tag plus the total commit count (`2.7.3381`). It works, but the number doesn't relate to `-dev.N`.
- The last tag plus a fixed offset and N (`2.7.3400 + N`). After a fix release the versions would go down.
- Even and odd minor numbers. RobotCode uses every minor for releases.
- A separate extension for dev builds. Its settings, commands and views would clash with the release extension's.

### The version is set when the VSIX is packaged

For a build without a tag, `package.py` runs `vsce package <version> --no-update-package-json --pre-release`. "Without a tag" means that the commit count since the last tag isn't 0. A new function in `tools.py` computes the version from the same tag and count as `get_current_version_from_git()`, through a shared helper. Builds of a tagged commit are packaged as before.

The repository's `package.json` keeps `2.8.0-dev.499`. The bundled Python packages keep it too, because they are installed from the build's wheels before `vsce package` runs, and vsce changes only the extension's manifest.

Alternatives:
- Setting the version at upload time. vsce rejects a version together with a packaged file, and ovsx ignores it.
- Rewriting the VSIX in the nightly job. The stores would get a file that the CI run didn't upload as its artifact.
- `npm version` with the extension version in "update versions from git". `package.json` would then disagree with the other packages of the build, and `get_version()` reads it when it runs under npm.

### One VSIX for both stores

The VS Code Marketplace and Open VSX get the same file. Open VSX would accept `2.8.0-dev.499`, but that needs a second VSIX and gives one build two numbers. VSCodium and the other editors on Open VSX are built from the VS Code source and update the same way.

### The nightly upload: one step per target in the existing workflow

- `publish_dev.py` takes the target as argument: `jetbrains` (the current behavior) or `vscode`. Each step finds the latest successful run on `main` by itself.
- `vscode`:
  - downloads `vscode-package`;
  - skips a VSIX without the pre-release property, which is the release commit;
  - runs `vsce publish --packagePath <vsix> --pre-release --skip-duplicate`;
  - runs `ovsx publish <vsix> --skip-duplicate`, also when the first upload failed;
  - fails afterwards if either upload failed.
- The workflow sets up Node.js and the node modules before the first upload step. The VS Code step runs with `if: ${{ !cancelled() }}`, so a failed JetBrains upload doesn't skip it. Each step gets only its own secrets.
- The hatch script `publish-dev` gets `{args}`.

Alternatives:
- **One step that publishes everything and collects the errors.** It would use one run for all stores. But the log wouldn't show at a glance which store failed, and every store's code would see every token.
- **Jobs per store.** Each needs its own checkout and setup.
- **Asking the stores for the version first, as for JetBrains.** `--skip-duplicate` does that in both tools.
- **Telling releases apart by the patch number.** That would tie the script to the numbering. The pre-release property is what both stores go by.

Two steps can pick different runs when a run finishes between them. Each still publishes a tested build of `main`.

### "What's New" skips dev builds

The notification doesn't appear when the patch number of the new version is 100000 or more. The extension still stores the version, so the next release is announced again. The threshold also appears in `tools.py`, and each place mentions the other.

Alternative: announce only changes of major or minor. Fix releases would no longer be announced.

## Risks / Trade-offs

- **[`VSCE_PAT` stops working on 2026-12-01]** → The VS Code step fails every night, while Open VSX and JetBrains go on. On tags, `publish.py` fails silently. Moving to another authentication is separate work. The Marketplace team is working on trusted publishing from GitHub Actions (microsoft/vsmarketplace#2121). Entra ID with a managed identity works today.
- **[Fix releases rank below the dev builds before them]** → Users on the pre-release version don't get the fix release itself, only its fixes through the dev builds. If fix and release land between two nightly runs, they get them with the next commit on `main`. The JetBrains channel `dev` behaves the same way.
- **[The Marketplace might hide the pre-release channel while a release is the highest version]** → A Microsoft member said so in microsoft/vsmarketplace#50 in 2023; not checked today. After a minor release this lasts until the next dev build.
- **[Two numbers for one build]** → The status bar shows `2.7.100499`, the language server reports `2.8.0-dev.499`. The block and N relate them.
- **[A prerelease tag as the last tag]** → After `v2.9.0-rc.1`, dev builds would be `2.9.1000NN` and rank above the later 2.9.0. RobotCode hasn't used prerelease tags since `v1.3.0-dev.6` in 2025.

## Migration Plan

After the push, the maintainer starts "publish dev build" by hand and checks:
- the log;
- the pre-release on the VS Code Marketplace and on Open VSX;
- that a second start uploads nothing.

If dev builds have to stop, removing the VS Code step is enough. The published pre-releases rank below the next minor release, so users on the pre-release version get that release.
