# Proposal

## Why

The nightly upload publishes the dev builds of the most recent *successful* run on `main`. Each store looks that run up on its own. While a feature is in progress, a few intermediate pushes often come in, and some of them leave the tests failing because something is still missing. The upload then publishes an older green intermediate state, although `main` is broken right now. And if a run turns green between the steps, the stores can get different builds in the same night.

## What Changes

- Every dev build of a night comes from one run: the latest CI run for a push to `main`. This holds for the VS Code Marketplace and Open VSX, the JetBrains channel `dev` and PyPI.
- If that run is still running, the upload waits for it, at most two hours in all. If a newer push starts a run meanwhile, the upload waits for that one instead.
- If that run doesn't succeed, or isn't done in time, no store gets a dev build that night. The upload says so in its log and still ends successfully. An older green run is never taken.
- The release commit on `main` stays as before: its build carries the release version, so the upload publishes nothing and leaves the version to the tag.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `release-publishing`:
  - adds the requirement that a night's dev builds come from the latest run on `main`;
  - changes the three nightly upload requirements of the VS Code extension, the JetBrains plugin and the Python packages, and the scenarios "Failing plugin test on main" and "Push to main" of the JetBrains plugin.

  The VS Code requirement is in the main spec. The JetBrains and the PyPI requirements come with `intellij-marketplace-publish` and `pypi-dev-builds`, which aren't archived yet.

## Impact

- `scripts/publish_dev.py`:
  - a target `latest-run` finds the latest push run on `main`, waits for it, and hands its id on when it succeeded;
  - the upload targets take the run id as an argument instead of looking a run up themselves.
- `.github/workflows/publish.yml`: the job `dev` gets a first step that determines the run. The three upload steps run only when it found one, with its id.
- While `main` stays red, there are no dev builds. That's the purpose of this change.
- Order: archive after `intellij-marketplace-publish` and `pypi-dev-builds`, whose requirements this change modifies.
