# Tasks

## 1. Build workflow

- [x] 1.1 Rename `.github/workflows/build-test-package-publish.yml` to `build-test-package.yml` with `git mv`, set `name: build test and package`, and remove the `publish` job. Verify that the file parses as YAML, that its jobs are `test`, `test-jetbrains`, `publish-test-results`, `code-quality` and `package`, and that none of them needs `publish`.

## 2. Publish script

- [x] 2.1 In `scripts/publish.py`, replace `run()` by a helper that runs an upload with `check=True` and a timeout, catches `subprocess.SubprocessError`, prints the failure and records the store. Run every upload through it, the JetBrains upload too, and end with an error that names the failed stores. Pass the PyPI credentials to `hatch publish` as `HATCH_INDEX_USER` and `HATCH_INDEX_AUTH` from `PYPI_USERNAME` and `PYPI_PASSWORD`, not on the command line.

  Verify with stubs for `npx`, `hatch` and `curl` early on `PATH` that record their arguments and environment, dummy secrets and the version set through `CZ_PRE_NEW_VERSION`:
  - for 2.9.0, the uploads to the VS Code Marketplace, Open VSX, PyPI and the JetBrains Marketplace run in this order, with the files from `dist/`;
  - for 2.9.0-dev.3, the VS Code Marketplace is left out;
  - with a failing `vsce`, the other three still run, and the script exits with an error that names the VS Code Marketplace;
  - no output contains a secret, no command line contains the PyPI credentials, and `hatch` gets them from its environment (the JetBrains token reaches `curl` as an argument that the shell expands, as before);
  - `hatch run lint:style` and `hatch run lint:typing` pass.
- [x] 2.2 In `scripts/publish.py`, let every release upload skip a version its store has:
  - `vsce publish` and `ovsx publish` get `--skip-duplicate`;
  - the lookup of the JetBrains versions moves from `scripts/publish_dev.py` into `scripts/publish.py`, with the channel as parameter (`https://plugins.jetbrains.com/api/plugins/26216/updates?channel=<channel>&size=100`), and both scripts use it;
  - before the JetBrains upload of a release, a version that the upload's channel lists is skipped with a message.

  Verify with the stubs of 2.1 and the lookup replaced in the test:
  - `vsce` and `ovsx` get `--skip-duplicate`;
  - a version that the JetBrains lookup lists isn't uploaded, and the script ends successfully;
  - the stub test of `publish_dev.py` still passes;
  - the lookup works against the real API: 2.7.0 in the default channel, 2.8.0-dev.508 in `dev`;
  - `hatch run lint:style` and `hatch run lint:typing` pass.

## 3. Publish workflow

- [x] 3.1 Rename `.github/workflows/publish-dev.yml` to `publish.yml` with `git mv` and set `name: publish`.
  - Add the trigger `workflow_run` for `build test and package` with `types: [completed]`.
  - Put today's steps into a job `dev` with `if: github.event_name != 'workflow_run'`, and move the concurrency group `publish-dev` from the workflow to that job.
  - In `scripts/publish_dev.py`, look up the runs of `build-test-package.yml`.

  Verify:
  - the file parses as YAML;
  - the stub test of `publish_dev.py` from `vscode-dev-builds` passes with the new workflow file in the `gh run list` call;
  - `hatch run lint:style` passes.
- [x] 3.2 Add the job `release` to `publish.yml`, as described in design.md.
  - Its `if` requires a successful `push` run of a branch starting with `v` from this repository.
  - Permissions: `actions: read` and `contents: write`.
  - Concurrency group `publish-release-${{ github.event.workflow_run.head_branch }}`.
  - Steps: checkout of `head_sha` with `fetch-depth: 0`; Python 3.10; Hatch; Node.js 26 with the current npm and the node modules; the four artifacts of the build run (`run-id`, `github-token`) into `dist/`; the release information; the GitHub release with `tag_name: ${{ github.event.workflow_run.head_branch }}`; `hatch -q run build:publish` with the five secrets.

  Verify that the file parses as YAML, and that every `if`, the `tag_name` and the `run-id` use `github.event.workflow_run` and never `github.ref`.
- [x] 3.3 In the job `release` of `publish.yml`, give the step "publish vsix, python packages and jetbrains plugin" the condition `if: ${{ !cancelled() && steps.get_release_informations.outcome == 'success' }}`, so that it also runs when only the GitHub release step failed. Verify that the file parses as YAML, and that the condition names the id `get_release_informations` of the release information step.

## 4. References

- [x] 4.1 Point the build status badge in `README.md` to `build-test-package.yml`, with the link to `https://github.com/robotcodedev/robotcode/actions/workflows/build-test-package.yml`. Name `build-test-package.yml` as the CI workflow in `CONTRIBUTING.md`. Verify that `build-test-package-publish` appears only in this change and in changes that are archived or already implemented, where it describes the state of their time.
- [x] 4.2 Update the open changes:
  - in `agent-plugin-release`, proposal, design and task 3.2 name the job `release` in `.github/workflows/publish.yml` instead of the `publish` job of the build workflow, and the step still comes directly before "create github release";
  - in `intellij-ui-tests`, the proposal names `build-test-package.yml`.

  Verify that `openspec validate --strict` passes for both.

## 5. Verification with the maintainer

- [ ] 5.1 After the push, check:
  - the build runs as "build test and package";
  - the `publish` run it starts skips both jobs;
  - a manual start of "publish" finds the run of `build-test-package.yml` and uploads nothing new.
- [ ] 5.2 At the next version tag, check:
  - the release job creates the GitHub release with the VSIX, the Python packages and the JetBrains plugin;
  - its log shows the answer of every store, and every store has the version;
  - the runs for untagged builds skipped the release job;
  - a re-run of the release job after the release uploads nothing and ends successfully.

## Workflow follow-up

- Archive this change after `intellij-marketplace-publish`. The MODIFIED requirement needs the JetBrains requirement of that change in the main spec `release-publishing`.
- Trusted publishing (OIDC) gets its own change, which registers `publish.yml` with the stores.
