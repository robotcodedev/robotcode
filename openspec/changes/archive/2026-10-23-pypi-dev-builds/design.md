# Design

## Context

See proposal.md for the motivation. The state that shapes the approach, checked on 2026-10-18:

- **The artifacts of every build** of `build-test-package.yml` (named after `publish-workflow`):
  - `python-packages` holds the 12 sdists, `wheel-packages` the 12 wheels.
  - In run 39063898654, the wheels were `robotcode-2.8.0.dev483-py3-none-any.whl` and `robotcode_<package>-2.8.0.dev483-py3-none-any.whl`. On PyPI, the sdists are named the same way, for example `robotcode-2.7.0.tar.gz` and `robotcode_core-2.7.0.tar.gz`.
  - The wheel of `robotcode` pins its dependencies exactly, for example `Requires-Dist: robotcode-core==2.8.0-dev.483`.
- **PyPI:**
  - `https://pypi.org/pypi/<project>/<version>/json` answers 200 for a version it has (`robotcode` 1.3.0.dev6, from an old prerelease tag) and 404 otherwise (`robotcode` 2.8.0.dev508).
  - The 12 files of 2.7.0 together have about 1.4 MB.
  - Projects have a size limit of 10 GB.
- **`hatch publish [ARTIFACTS]...`:**
  - It reads the credentials from `HATCH_INDEX_USER` and `HATCH_INDEX_AUTH`.
  - It skips files the index has ("already exists"), uploads in the given order, and stops at the first failed upload.
- **The build environment** of Hatch has `packaging`, which parses PEP 440 versions (`Version("2.8.0.dev508").is_prerelease` is true).
- **Installers:**
  - pip chooses development releases only with `--pre` or a pin that names one.
  - uv prefers releases and falls back to a pre-release only when no release fits, so a pin works there too.
- **The job `dev` of `publish.yml`** (from `publish-workflow`): each target is a step of its own, `build:publish-dev jetbrains` and `build:publish-dev vscode`. The second runs with `if: ${{ !cancelled() }}`, and each step gets only its own secrets.
- **`scripts/publish_dev.py`:** each target finds the latest successful push run on `main`, downloads its artifact into `dist/` and skips releases. JetBrains asks the store for the version first; VS Code uses `--skip-duplicate`.

## Goals / Non-Goals

**Goals:**

- The dev version on PyPI has the same number as the dev builds in the other stores.
- A dev version of `robotcode` on PyPI can always be installed.
- A PyPI problem and a problem of another store don't block each other.

**Non-Goals:**

- Uploading only when the Python packages changed. The maintainer decided against it on 2026-10-18; it would have saved about 20 % of the uploads (91 instead of 116 days in the year up to then).
- Cleaning up old dev versions on PyPI.

## Decisions

### A third target `python` in `publish_dev.py`

1. It downloads the artifacts `python-packages` and `wheel-packages` of the latest successful push run on `main` into `dist/`, with one `gh run download` per artifact, as for the other targets.
2. It reads the version from the wheel `robotcode-<version>-py3-none-any.whl` with `packaging.version.Version`. A version that isn't a pre-release is skipped with a message.
3. If PyPI answers the version of `robotcode` with 200, it ends with a message. The project `robotcode` is uploaded last, so its version on PyPI means the version is complete.
4. Otherwise it runs `hatch publish` with the files of the eleven `robotcode_*` packages, and only after that succeeded, `hatch publish` with the two files of `robotcode`. The credentials go into `HATCH_INDEX_USER` and `HATCH_INDEX_AUTH`, from `PYPI_USERNAME` and `PYPI_PASSWORD`.
5. A failed call ends the script with an error that names PyPI.

Alternatives:
- **Asking PyPI for each of the 12 projects.** Twelve requests, where `robotcode` alone tells the answer.
- **One `hatch publish` for all files.** It uploads in directory order, so `robotcode` can come before the packages it requires.
- **TestPyPI or a separate index.** Users would need an extra index URL. On PyPI, development releases stay out of normal installs anyway.

### Its own step in the job `dev`

`hatch -q run build:publish-dev python` comes after the VS Code step. It has `if: ${{ !cancelled() }}` and the secrets `GH_TOKEN`, `GH_REPO`, `PYPI_USERNAME` and `PYPI_PASSWORD`, so a failure of another store doesn't skip it, and its failure doesn't skip theirs.

### No version mapping

PEP 440 already orders the dev versions right: `2.8.0.dev508 < 2.8.0`, and after a fix release `2.7.1.dev3 < 2.7.1`. The dev number stays the same as in `2.8.0-dev.508` and `2.7.100508`.

## Risks / Trade-offs

- **[The release history on PyPI grows]** → Up to one dev version per project and day with a new build. That is about 1,400 entries a year over the 12 projects, at about 1.4 MB per build. Removing them is only possible by hand on PyPI.
- **[PyPI frowns on nightly builds]** → Its support names them as a reason to refuse a larger size limit. At these sizes the project stays far below the default 10 GB.
- **[The PyPI token is now used every night]** → The same secret as for releases, now also in the job `dev`. The trusted-publishing change can replace it.
- **[`pip install --pre robotcode` also takes pre-releases of the dependencies]**, for example release candidates of Robot Framework → A pin like `robotcode[all]==2.8.0.dev508` avoids that. Describing it in the user docs is outside this change.
- **[An upload stops between the packages and `robotcode`]** → The version isn't installable until the next run uploads `robotcode`. The run before already failed visibly.

## Migration Plan

After `publish-workflow`:
1. Push the change and start "publish" by hand.
2. Check:
   - all 12 projects have the dev version on PyPI;
   - a second start uploads nothing;
   - `pip install robotcode` in a scratch environment still installs the release, and `pip install "robotcode[all]==<dev version>"` installs the dev version.

The old development releases `1.3.0.dev1` to `1.3.0.dev6` stay on PyPI. To stop the uploads, removing the step is enough. The published dev versions rank below the next release, so they don't get in the way.
