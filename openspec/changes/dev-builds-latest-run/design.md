# Design

## Context

See proposal.md for the motivation. The state that shapes the approach, checked on 2026-10-19:

- **`scripts/publish_dev.py`:** each target (`jetbrains`, `vscode`, `python`) calls `latest_successful_main_run()`. It runs `gh run list --workflow build-test-package.yml --branch main --event push --status success --limit 1` and downloads that run's artifact. A newer run that failed or is still running is skipped over.
- **The job `dev` of `.github/workflows/publish.yml`:**
  - after the setup, one step per target, each with only its own secrets;
  - the VS Code and the Python steps run with `if: ${{ !cancelled() }}`.
- **`gh run list` without `--status`** lists runs newest first, with `status` (`queued`, `in_progress`, `waiting`, … `completed`) and `conclusion` (`success`, `failure`, `cancelled`, …).
- **Duration of the builds of pushes to `main`**, from start to the last update of the run, over the 18 runs before 2026-10-19: median 64 minutes, longest 110 minutes. Re-runs count into that.
- **The nightly run** started between 07:15 and 07:55 UTC on the last two days instead of 02:23, because GitHub delays scheduled runs.
- **Step outputs** go through the file that `GITHUB_OUTPUT` names. A step reads them with `steps.<id>.outputs.<name>`.

## Goals / Non-Goals

**Goals:**

- All stores get the dev build of the same run in a night.
- A broken `main` produces no dev build, also not an older one.
- A night without a dev build is not a failure of the upload.

**Non-Goals:**

- Signalling a broken `main` through the upload. The build workflow is red already.

## Decisions

### Only the latest run, never an older green one

The upload takes the newest push run on `main` and publishes nothing when it isn't green. The maintainer decided this on 2026-10-19: intermediate pushes during feature work often leave a broken build, and the last green run before it is then an unfinished intermediate state.

Alternative: the most recent successful run, as before. It would keep publishing intermediate states while `main` is broken, and every store could take a different run.

### One step finds the run, the upload steps get its id

The new target `latest-run` of `publish_dev.py` does the following:

1. It lists the newest push run of `build-test-package.yml` on `main`.
2. While that run isn't completed, it lists the newest push run again every 60 seconds, for at most two hours in all. A run that a newer push starts meanwhile thus replaces the one it waited for. The maintainer decided this on 2026-10-19: the run it waited for is no longer the latest once a newer one exists.
3. When the run succeeded, it writes `run-id=<id>` into the file of `GITHUB_OUTPUT` and prints the id. Otherwise it prints why there is no dev build and writes nothing.
4. It ends successfully in both cases. It fails only when `gh` fails.

The poll interval and the limit are module constants.

The job `dev` runs this target as the step `build` after the setup. The three upload steps then:
- get `--run-id ${{ steps.build.outputs.run-id }}`;
- run with `if: ${{ !cancelled() && steps.build.outputs.run-id != '' }}`.

`jetbrains`, `vscode` and `python` require `--run-id` and no longer look up a run. `latest_successful_main_run()` goes away.

Alternatives:
- **Each target finds the latest run itself, with the new rule.** If a run started or finished between the steps, the stores could still get different builds.
- **One step for all stores.** That gives up the separate steps with their own secrets, which `vscode-dev-builds` chose.
- **The lookup as a shell step with `gh` and `jq` in the workflow.** The waiting with a limit is clearer in Python, and the targets stay testable with the same stubs.

### Wait at most two hours

Builds took 64 minutes in the median and 110 at most. Two hours cover a build that starts just before the upload. After that, the next night takes the run, if it is still the latest and green.

The step polls with `gh run list` rather than `gh run watch`. `gh run watch` has no time limit and follows one run only.

Alternatives for a newer run that starts during the wait:
- **Publish the run it waited for.** That publishes a state that a newer push has already replaced.
- **Publish nothing once a newer run exists.** That gives up a night although the newer run might become green in time.

### A night without a dev build ends green

If the latest run failed, was cancelled, or isn't done within the limit, the step `build` ends successfully and the upload steps are skipped. A red nightly run would only repeat what the build workflow already shows.

## Risks / Trade-offs

- **[While `main` stays red, there are no dev builds]** → That's the purpose. The first green push brings them back the next night, or right away with a manual start.
- **[A build that starts just before the upload delays it by up to two hours]** → The job only waits. Nothing else runs in it.
- **[Pushes during the wait keep the upload waiting]** → The two hours count from the start. If pushes keep coming, the night has no dev build, and the next night or a manual start takes the latest run.
- **[The MODIFIED requirements of JetBrains and PyPI need their changes archived first]** → `intellij-marketplace-publish` and `pypi-dev-builds` are archived before this change.

## Migration Plan

After the push, the maintainer starts "publish" by hand:
- while the latest run on `main` is red, the log says that there is no dev build, and nothing is uploaded;
- after a green run, all three steps use the same run id, and the stores get the same build number.
