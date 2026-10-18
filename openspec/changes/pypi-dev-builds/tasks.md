# Tasks

Implement this change after `publish-workflow`.

## 1. Upload script

- [ ] 1.1 Give `scripts/publish_dev.py` the target `python`, as described in design.md:
  - It downloads `python-packages` and `wheel-packages` of the latest successful push run on `main` into `dist/`.
  - It reads the version from the wheel of `robotcode` with `packaging.version.Version`, and skips a release version and a version that PyPI has for `robotcode`, each with a message.
  - Otherwise it uploads the eleven `robotcode_*` packages with `hatch publish`, and after that succeeded, the files of `robotcode`.
  - The credentials go into `HATCH_INDEX_USER` and `HATCH_INDEX_AUTH`, from `PYPI_USERNAME` and `PYPI_PASSWORD`.
  - A failed upload ends with an error that names PyPI.

  Verify with stubs for `gh` and `hatch` early on `PATH` that record their arguments and environment, dummy secrets and the PyPI lookup replaced in the test:
  - for a dev version that PyPI doesn't have, `hatch publish` first gets the 22 files of the eleven packages and then the two files of `robotcode`;
  - a version that PyPI has, and the release version 2.8.0, upload nothing and end successfully;
  - with a failing first `hatch publish`, `robotcode` isn't uploaded, and the script exits with an error that names PyPI;
  - no command line and no output contains a secret, and `hatch` gets the credentials from its environment;
  - the PyPI lookup works against the real API for `robotcode` 1.3.0.dev6 (found) and 2.8.0.dev1 (not found);
  - `hatch run lint:style` and `hatch run lint:typing` pass.

## 2. Publish workflow

- [ ] 2.1 In the job `dev` of `.github/workflows/publish.yml`, add after the VS Code step the step `hatch -q run build:publish-dev python`, with `if: ${{ !cancelled() }}` and the environment `GH_TOKEN`, `GH_REPO`, `PYPI_USERNAME` and `PYPI_PASSWORD`. Verify that the file parses as YAML, and that only this step gets the PyPI secrets.

## 3. Verification with the maintainer

- [ ] 3.1 After the push, the maintainer starts "publish" by hand. Check:
  - the log shows PyPI's answers;
  - all 12 projects list the dev version of the latest successful run on `main`;
  - a second start uploads nothing;
  - in a scratch environment, `pip install robotcode` installs the latest release, and `pip install "robotcode[all]==<dev version>"` installs the dev version of all packages.

  Check the first scheduled run after that.

## Workflow follow-up

- Archive the change after `intellij-marketplace-publish`, `vscode-dev-builds` and `publish-workflow`.
