# Proposal

## Why

Every RobotCode release now has a matching release of the `robotcode` agent plugin in `robotcodedev/robotframework-agent-plugins`. The plugin version must equal the RobotCode version. The vendored copy in `chat-plugins/` must be synced. After the release, the synced commit must be tagged `robotcode--vX.Y.Z` and the plugin repo's `main` fast-forwarded to it. All of these are manual steps that are easy to forget, and the tags for 2.6.0–2.7.0 had to be added after the fact. Forgetting the last step leaves `main`, which agents install from when no ref is given, on an old or unreleased skill.

## What Changes

- `hatch run build:bump` checks before it commits that the vendored plugin is ready for the release. It aborts with instructions if the plugin version does not match the new RobotCode version, if `chat-plugins/` is out of sync with the local plugin checkout, or if the synced commit is not on the plugin repo's local `next` branch. Prereleases are not checked.
- After the bump, the bump also prepares the plugin release in the local plugin checkout. It creates the tag `robotcode--vX.Y.Z` on the synced commit (signed if git is configured to sign tags) and fast-forwards the local `main` to that commit. It then prints the command that pushes both. Nothing is pushed. The preparation can be rerun by hand.
- The publish job of the release workflow checks, read-only and without credentials, that the plugin release is public: the tag exists on GitHub and the plugin repo's `main` points to the synced commit. If either is missing, the job fails before the GitHub release is created and before any package is published. Prereleases are not checked.
- The contributor docs describe the new flow. In the plugin repo, the release step becomes "prepared by the RobotCode bump, pushed by the maintainer, enforced by the publish job", with the manual commands as fallback. RobotCode's CONTRIBUTING mentions the checks at `hatch run build:bump`.

## Capabilities

### New Capabilities
- `agent-plugin-release`: how a RobotCode release guarantees the matching release of the bundled agent plugin. Covers the readiness check at the version bump, the local preparation of the plugin tag and `main`, and the publish gate.

### Modified Capabilities
<!-- none -->

## Impact

- New scripts in `scripts/`: a readiness check (pre-bump), a release preparation (post-bump) and a publish check (CI). Each has a `build` env script in `hatch.toml`.
- `pyproject.toml`: `[tool.commitizen]` gets the check as the first `pre_bump_hooks` entry and the preparation as a `post_bump_hooks` entry.
- `.github/workflows/build-test-package-publish.yml`: one step in the `publish` job, before "create github release".
- `CONTRIBUTING.md` (Build & Release). The plugin repo's `CONTRIBUTING.md` changes in the separate `robotframework-agent-plugins` repository.
- No keys, tokens or secrets. Pushing uses the maintainer's own git credentials, and CI only reads the public plugin repo.
- Maintainer prerequisite at bump time: the plugin repo checked out next to `robotcode` (as `sync_chat_plugin.py` already expects), with a local `next` branch.
- Rollout: implemented after the 2.8.0 release. 2.8.0 is tagged and `next` is created by hand.
