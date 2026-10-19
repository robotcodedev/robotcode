# Tasks

This change builds on the target `python` that `pypi-dev-builds` adds to `scripts/publish_dev.py`. That target is implemented; only the archiving has to wait, see below.

## 1. Run lookup

- [x] 1.1 In `scripts/publish_dev.py`, add the target `latest-run`, as described in design.md:
  - it lists the newest push run of `build-test-package.yml` on `main`;
  - while that run isn't completed, it polls it with `gh run view` every 60 seconds for at most two hours;
  - if the run succeeded, it writes `run-id=<id>` into the file of `GITHUB_OUTPUT`, when set, and prints the id; otherwise it prints why there is no dev build;
  - it ends successfully in both cases.

  Give `jetbrains`, `vscode` and `python` the required option `--run-id` and remove `latest_successful_main_run()`. Keep the poll interval and the limit in module constants.

  Verify with the stubs for `gh`, `npx`, `hatch` and `curl` from the earlier changes, with the constants replaced in the test:
  - a succeeded newest run is written to the output file;
  - a failed or cancelled newest run writes nothing and ends successfully, also when an older run succeeded;
  - a run that is in progress and then succeeds is waited for and then written;
  - a run that doesn't complete within the limit writes nothing;
  - the three upload targets download the artifacts of the given run id;
  - the existing stub tests pass with `--run-id`;
  - `hatch run lint:style` and `hatch run lint:typing` pass.

- [x] 1.2 Let `latest-run` follow a newer run: while the latest run isn't completed, it lists the newest push run on `main` again every 60 seconds instead of reading the first one with `gh run view`. The two hours count from the start.

  Verify with the stubs of 1.1:
  - a newer run that starts while the first one runs is waited for and handed on, and the result of the first one is ignored;
  - a newer run that fails hands nothing on, also when the first one succeeded;
  - runs that keep replacing each other until the limit hand nothing on;
  - the other cases of 1.1 still pass;
  - `hatch run lint:style` and `hatch run lint:typing` pass.

## 2. Publish workflow

- [x] 2.1 In the job `dev` of `.github/workflows/publish.yml`, add after the setup the step with `id: build` that runs `hatch -q run build:publish-dev latest-run` with `GH_TOKEN` and `GH_REPO`. Pass `--run-id ${{ steps.build.outputs.run-id }}` to the three upload steps, and give each of them `if: ${{ !cancelled() && steps.build.outputs.run-id != '' }}`. Verify that the file parses as YAML, that every upload step has the condition and the option, and that the secrets of each step are unchanged.

## 3. Verification with the maintainer

- [ ] 3.1 After the push, the maintainer starts "publish" by hand. Check:
  - while the latest run on `main` is red, the log says that there is no dev build, the upload steps are skipped, and the run is green;
  - after a green run, the step `build` logs its id, and all three upload steps use that id, so the stores get the same build number.

## Workflow follow-up

- Archive this change after `intellij-marketplace-publish` and `pypi-dev-builds`, whose requirements it modifies.
