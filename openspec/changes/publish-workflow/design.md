# Design

## Context

See proposal.md for the motivation. The state that shapes the approach, checked on 2026-10-18:

- **The build workflow** (`build-test-package-publish.yml`, "build test package and publish"):
  - It runs for pushes to `main`, for tags `v*`, for pull requests to `main` and by hand.
  - Its jobs: `test`, `test-jetbrains`, `publish-test-results`, `code-quality`, `package` and `publish`. `publish` needs `code-quality` and `package`.
  - **The `publish` job:**
    - checks out with `fetch-depth: 0`, then sets up Python 3.10, Hatch, Java, Gradle, Node.js and the node modules;
    - downloads the artifacts `vscode-package`, `python-packages`, `wheel-packages` and `intellij-package` into `dist/`;
    - reads the release notes, the prerelease flag and the version through `build:extract-release-notes`, `build:is-prerelease` and `build:get-release-version`.
  - Only on tags, it then:
    - creates the GitHub release with `softprops/action-gh-release@v3`;
    - runs `hatch -q run build:publish` with `VSCE_PAT`, `OVSX_PAT`, `PYPI_USERNAME`, `PYPI_PASSWORD` and `PUBLISH_TOKEN`.
  - Java and Gradle aren't used there: the JetBrains upload is a `curl` call.
- **The dev workflow** (`publish-dev.yml`, "publish dev build", from `intellij-marketplace-publish` and `vscode-dev-builds`):
  - It runs at 02:23 and by hand, with `actions: read` and `contents: read` and a workflow-level `concurrency` group `publish-dev`.
  - One step per target runs `build:publish-dev jetbrains` or `build:publish-dev vscode`.
  - `scripts/publish_dev.py` finds the latest successful push run of `build-test-package-publish.yml` on `main`.
- **`scripts/publish.py`:**
  - `vsce publish` runs only for versions without a pre-release label. `ovsx publish`, `hatch publish` and the JetBrains upload run always.
  - The first three go through `run()`, which neither checks the exit code nor lets an exception through. Only the JetBrains upload uses `check=True`.
  - `hatch publish` gets the PyPI user and password on its command line. Hatch also reads them from `HATCH_INDEX_USER` and `HATCH_INDEX_AUTH`.
- **`workflow_run`** (GitHub Actions):
  - It starts a workflow when another workflow, named by its `name:`, completes. It uses the triggered workflow's file from the default branch.
  - The run has the repository's secrets, also when the completed run was for a pull request from a fork.
  - Its event carries the completed run's `id`, `conclusion`, `event`, `head_branch`, `head_sha` and `head_repository`. For a tag push, `head_branch` is the tag name: the run of `v2.7.0` lists `v2.7.0` as its branch.
- **`softprops/action-gh-release`** takes the tag from `tag_name`, which defaults to `github.ref_name`. In a `workflow_run` run, that is the default branch. If the tag has a release already, the action updates it, and `overwrite_files`, true by default, replaces files of the same name.
- **The JetBrains Marketplace** lists the versions of a channel at `https://plugins.jetbrains.com/api/plugins/26216/updates?channel=<channel>`. An empty channel is the default channel (2.7.0, 2.5.1, …), and `dev` the dev channel. `vsce publish` and `ovsx publish` skip a version the store has with `--skip-duplicate`, as the dev builds use them.
- **A re-run** of a workflow run uses the commit and the workflow file of the original run. A job reads the secrets when it starts, so a replaced token reaches a re-run.
- **`actions/download-artifact`** downloads the artifacts of another run with `run-id` and `github-token`, which need `actions: read`.
- **`concurrency`**: a group holds one running and one pending run. A newly queued run replaces the pending one.
- **Branch protection of `main`** requires checks by job name only. Renaming a workflow file doesn't touch them.

## Goals / Non-Goals

**Goals:**

- One workflow file creates every GitHub release and makes every upload to a store.
- The release packages are the files the tag's build made and tested.
- Nothing a pull request or a fork does can start an upload.

**Non-Goals:**

- Trusted publishing. It gets its own change, which then only has to register `publish.yml`.
- One step per store for releases.

## Decisions

### One publish workflow with a `dev` and a `release` job

`publish-dev.yml` becomes `publish.yml`, named "publish". It has three triggers: `schedule`, `workflow_dispatch` and `workflow_run` for "build test and package" with `types: [completed]`.
- The job `dev` keeps today's steps and runs for the schedule and manual starts.
- The new job `release` runs for `workflow_run`.

Alternatives:
- **A reusable workflow that both workflows call.** Open VSX checks the claim `workflow_ref`, and in a reusable workflow that names the calling workflow. Two callers would still be two workflows.
- **A tag trigger in `publish.yml` that waits for the tag's build.** It would have to poll the build run.
- **Dev builds from the build workflow.** That would run the whole test matrix every night, or publish on every push instead of once a night.

### The release job only runs for a successful build of a version tag of this repository

The job's `if` requires all of:
- `github.event_name == 'workflow_run'`;
- `github.event.workflow_run.conclusion == 'success'`;
- `github.event.workflow_run.event == 'push'`;
- `startsWith(github.event.workflow_run.head_branch, 'v')`;
- `github.event.workflow_run.head_repository.full_name == github.repository`.

The build workflow runs on pushes only for `main` and for tags `v*`, so a push run whose branch starts with `v` is a version tag.

A `branches` filter on the trigger would save the skipped runs, but it isn't documented for tags and doesn't replace the check. So every build run starts a `publish` run whose jobs are all skipped.

### The release job takes over the steps of the old `publish` job

- **Permissions:** `actions: read` for the download and `contents: write` for the GitHub release. The job sets them itself; the workflow keeps `actions: read` and `contents: read`.
- **Checkout:** `ref: ${{ github.event.workflow_run.head_sha }}` with `fetch-depth: 0`. The version scripts then see the tag, and the scripts of the tag's commit do the upload.
- **Setup:** Python 3.10, Hatch, Node.js 26 with the current npm and the node modules. Java and Gradle are dropped.
- **Artifacts:** `actions/download-artifact` downloads the four artifacts with `run-id: ${{ github.event.workflow_run.id }}` into `dist/`.
- **GitHub release:** created with `tag_name: ${{ github.event.workflow_run.head_branch }}`. Name, prerelease flag, release notes and files stay as before.
- **Upload:** `hatch -q run build:publish` with the same five secrets as before, without the tag condition, because the job runs only for tags.
- **Concurrency:** the group `publish-release-<tag>`, so that two runs for the same tag don't upload at once and runs for different tags don't replace each other.

### The upload also runs when only the GitHub release failed

The upload step gets `if: ${{ !cancelled() && steps.get_release_informations.outcome == 'success' }}`. It runs after a failed GitHub release step, but not after a failed download or release information step, because then it has nothing to upload.

Alternatives:
- **`!cancelled()` alone.** The step would also run after a failed download.
- **The uploads before the GitHub release.** Users could then get the version before its release notes are on GitHub.

### Concurrency of the dev job

The group `publish-dev` moves from the workflow to the job `dev`. At workflow level, every build's `workflow_run` run would queue in it and could replace a pending nightly run.

### `publish.py` tries every upload and fails at the end

`run()` is replaced by a helper that runs an upload with `check=True`. It catches `subprocess.SubprocessError`, prints the failure and records the store. The JetBrains upload goes through the same helper. After the last upload, the script ends with an error that names the failed stores, as `publish_dev.py vscode` does.

`hatch publish` gets the PyPI credentials from `HATCH_INDEX_USER` and `HATCH_INDEX_AUTH`, set from `PYPI_USERNAME` and `PYPI_PASSWORD`. That way they appear neither on its command line nor in an error message that prints the command.

Every upload skips a version its store has, so that a re-run of the release job uploads only what is missing:
- `vsce publish` and `ovsx publish` get `--skip-duplicate`;
- `hatch publish` skips files PyPI has anyway;
- before the JetBrains upload, the script looks up the versions of the upload's channel and skips a listed version.

The lookup moves from `publish_dev.py` into `publish.py`, with the channel as parameter, and both scripts use it.

Alternative: one job per store. GitHub could then re-run only the failed job, and each job would see only its own token, but every job needs its own checkout, setup and download. The trusted-publishing change can revisit this.

### The build workflow becomes "build test and package"

`build-test-package-publish.yml` becomes `build-test-package.yml`, named "build test and package", without the `publish` job. The following follow the rename:
- `publish_dev.py`;
- the README badge and its link (to `actions/workflows/build-test-package.yml`);
- the workflow named in `CONTRIBUTING.md`;
- the open changes `agent-plugin-release` (its task 3.2 then targets the job `release` in `publish.yml`) and `intellij-ui-tests`.

## Risks / Trade-offs

- **[A release now needs the whole build run to succeed]** → `workflow_run` reports one conclusion for the run. A failure in `publish-test-results` now also stops a release, which the old `publish` job ignored.
- **[A skipped `publish` run per build]** → The Actions list gets one skipped run for every build. The trigger can't filter more safely, see the decision above.
- **[The release job runs from the default branch's `publish.yml`]** → Changes to it can only be tried on `main`. The next version tag is the first real run. If an upload fails there because of a token or a store, the maintainer fixes that and re-runs the release job, which uploads only what is missing. A fix in the workflow or in the scripts doesn't reach a re-run, because it uses the workflow file of the original run and the scripts of the tag's commit. Then the maintainer publishes the missing part by hand, as before `intellij-marketplace-publish`.
- **[No successful run of `build-test-package.yml` right after the rename]** → The nightly upload fails until the first green build of the new file on `main`. The commit with the rename starts that build.
- **[The MODIFIED requirement needs the JetBrains requirement in the main spec]** → `release-publishing` is a main spec since `vscode-dev-builds` was archived, but the JetBrains requirement comes with `intellij-marketplace-publish`. So that change has to be archived first. `openspec validate` already reports this as information.

## Migration Plan

1. Push the change. Check that the build runs as "build test and package" and that the `publish` run it starts skips both jobs.
2. Start "publish" by hand and check that the dev job finds the run of `build-test-package.yml`.
3. At the next version tag, check the GitHub release and the uploads in the log of the release job.

If an upload fails at a tag, the maintainer fixes its cause, for example replaces a token, and re-runs the release job; it uploads only what is missing. If the failure needs a fix in the workflow or in the scripts, the maintainer publishes the missing part by hand, from the GitHub release or the build's artifacts, and fixes the job before the next tag.
