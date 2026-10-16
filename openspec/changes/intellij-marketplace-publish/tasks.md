# Tasks

Implement this change after `intellij-ci-tests`.

## 1. Marketplace upload

- [ ] 1.1 Add the upload of the JetBrains plugin to `scripts/publish.py`, after `hatch publish`:
  - `curl --fail-with-body` posts `dist/robotcode4ij-<version>.zip` to `https://plugins.jetbrains.com/api/updates/upload` with the header `Authorization: Bearer $PUBLISH_TOKEN` (expanded by the shell) and the form fields `xmlId=dev.robotcode.robotcode4ij`, `file` and `channel`;
  - `channel` is `dev` when `get_version().prerelease` is set, and empty otherwise;
  - it runs through `subprocess.run` with `check=True` and a timeout, not through `run()`;
  - a missing zip for the version ends the script with a message that names the expected file.

  Verify with a stub `curl` early on `PATH` that records its arguments and a dummy `PUBLISH_TOKEN`, calling only the new upload code:
  - for `2.9.0-dev.3` it posts to `channel=dev`, and for `2.9.0` to an empty channel, with the zip from `dist/` and the `xmlId`;
  - the token never appears in the printed output;
  - a stub that exits with code 22 fails the call;
  - `hatch run lint:style` and `hatch run lint:typing` pass.
- [ ] 1.2 Rename the step "publish vsix and python packages" in `.github/workflows/build-test-package-publish.yml` so that its name also covers the JetBrains plugin. Verify that the file still parses as YAML (`python -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" <file>`) and that the step keeps its tag condition and its `PUBLISH_TOKEN`.

## 2. Verification

- [ ] 2.1 With the maintainer, after `intellij-ci-tests` is in place and the maintainer pushes the next version tag, check:
  - the publish step's log shows the Marketplace's answer to the upload;
  - the version is on the plugin's Marketplace page in the expected channel, `dev` for a prerelease and the default channel for a release;
  - the uploaded file is the `robotcode4ij-<version>.zip` of the GitHub release;
  - a run on `main` without a tag uploaded nothing, because the publish step was skipped.

  If the token is rejected, the maintainer replaces the secret and uploads that version by hand from the GitHub release.
