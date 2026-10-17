# Tasks

Implement this change after `intellij-ci-tests`.

## 1. Marketplace upload

- [x] 1.1 Add the upload of the JetBrains plugin to `scripts/publish.py`, after `hatch publish`:
  - `curl --fail-with-body` posts `dist/robotcode4ij-<version>.zip` to `https://plugins.jetbrains.com/api/updates/upload` with the header `Authorization: Bearer $PUBLISH_TOKEN` (expanded by the shell) and the form fields `xmlId=dev.robotcode.robotcode4ij`, `file` and `channel`;
  - `channel` is `dev` when `get_version().prerelease` is set, and empty otherwise;
  - it runs through `subprocess.run` with `check=True` and a timeout, not through `run()`;
  - a missing zip for the version ends the script with a message that names the expected file.

  Verify with a stub `curl` early on `PATH` that records its arguments and a dummy `PUBLISH_TOKEN`, calling only the new upload code:
  - for `2.9.0-dev.3` it posts to `channel=dev`, and for `2.9.0` to an empty channel, with the zip from `dist/` and the `xmlId`;
  - the token never appears in the printed output;
  - a stub that exits with code 22 fails the call;
  - `hatch run lint:style` and `hatch run lint:typing` pass.
- [x] 1.2 Rename the step "publish vsix and python packages" in `.github/workflows/build-test-package-publish.yml` so that its name also covers the JetBrains plugin. Verify that the file still parses as YAML (`python -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" <file>`) and that the step keeps its tag condition and its `PUBLISH_TOKEN`.

## 2. Nightly dev builds

- [x] 2.1 Add `scripts/publish_dev.py` and the hatch script `publish-dev` in `hatch.toml`:
  - `gh run list` finds the most recent successful run of `build-test-package-publish.yml` for a push to `main`; without one, the script ends with a message;
  - `gh run download` puts that run's artifact `intellij-package` into `dist/`, and the version comes from the zip's file name;
  - a version without a pre-release label, or one that `https://plugins.jetbrains.com/api/plugins/26216/updates?channel=dev` lists already, is skipped with a message;
  - otherwise `publish_jetbrains_plugin()` uploads it.

  Verify with stubs for `gh` and `curl` early on `PATH`, a dummy `PUBLISH_TOKEN` and the Marketplace lookup replaced in the test:
  - a successful run with 2.8.0-dev.470 that `dev` doesn't have is downloaded from that run and uploaded with `channel=dev`;
  - a version that `dev` has, and the release version 2.8.0, upload nothing and end successfully;
  - without a successful run the script fails with its message, and the token never appears in the output;
  - the Marketplace lookup works against the real API and returns the versions in `dev`;
  - `hatch run lint:style` passes.
- [x] 2.2 Add `.github/workflows/publish-dev.yml`: a schedule at `23 2 * * *` and `workflow_dispatch`, `permissions` with `actions: read` and `contents: read`, a `concurrency` group, checkout, Python 3.10, Hatch, and `hatch -q run build:publish-dev` with `GH_TOKEN` and `PUBLISH_TOKEN`. Verify that the file parses as YAML.

## 3. Verification

- [ ] 3.1 With the maintainer, after `intellij-ci-tests` is in place and the maintainer pushes the next version tag, check:
  - the publish step's log shows the Marketplace's answer to the upload;
  - the version is on the plugin's Marketplace page in the expected channel, `dev` for a prerelease and the default channel for a release;
  - the uploaded file is the `robotcode4ij-<version>.zip` of the GitHub release;
  - a run on `main` without a tag uploaded nothing, because the publish step was skipped.

  If the token is rejected, the maintainer replaces the secret and uploads that version by hand from the GitHub release.
- [ ] 3.2 With the maintainer, after the push: the maintainer starts "publish dev build" by hand. Check that its log shows the Marketplace's answer, that the channel `dev` then lists the version of the most recent successful run on `main`, and that a second start uploads nothing. Check the first scheduled run the next day.
