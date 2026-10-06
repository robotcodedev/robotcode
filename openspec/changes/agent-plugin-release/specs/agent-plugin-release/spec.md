# Spec Delta

## Purpose

Makes every RobotCode release come with the matching release of the bundled `robotcode` agent plugin. The plugin version must match, the synced commit must be tagged `robotcode--vX.Y.Z`, and the plugin repository's `main` must point to it, without keys or tokens.

## ADDED Requirements

### Requirement: Version bump checks that the bundled plugin is ready

Before it commits, `hatch run build:bump` SHALL check the vendored agent plugin for a final release:
- The `version` in `chat-plugins/robotcode/.plugin/plugin.json` and the `metadata.version` in the vendored `SKILL.md` SHALL equal the new RobotCode version.
- `chat-plugins/robotcode/` SHALL be in sync with the plugin in the local plugin repository checkout.
- The commit recorded in `chat-plugins/.upstream.json` SHALL be contained in that checkout's local `next` branch.

If any condition fails, the bump SHALL abort before creating the bump commit and tag. Its message SHALL name the failed condition and the step that fixes it. For a prerelease version, the check SHALL be skipped.

#### Scenario: Plugin ready
- **WHEN** a maintainer runs `hatch run build:bump` for 2.9.0, the vendored plugin has version `2.9.0` in `plugin.json` and `SKILL.md`, is in sync with the local plugin checkout, and its recorded commit is on the local `next`
- **THEN** the bump proceeds

#### Scenario: Plugin version not set
- **WHEN** a maintainer runs `hatch run build:bump` for 2.9.0 and the vendored `plugin.json` still says `2.8.0`
- **THEN** the bump aborts without a commit or tag, and the message says to set the plugin version to `2.9.0` on the plugin repo's `next`, commit it and sync the plugin

#### Scenario: Vendored copy out of sync
- **WHEN** the local plugin checkout has changes to the plugin that `chat-plugins/robotcode/` does not have
- **THEN** the bump aborts, and the message says to run `hatch run build:sync-chat-plugin` and commit the result

#### Scenario: Recorded commit not on next
- **WHEN** the commit in `chat-plugins/.upstream.json` is not contained in the local `next` branch of the plugin checkout
- **THEN** the bump aborts, and the message names the commit and the branch

#### Scenario: Plugin checkout missing
- **WHEN** no plugin repository checkout exists next to the `robotcode` checkout
- **THEN** the bump aborts, and the message names the expected location

#### Scenario: Prerelease
- **WHEN** a maintainer bumps to a prerelease version such as `2.9.0-rc.0`
- **THEN** the plugin check does not run and does not block the bump

### Requirement: Version bump prepares the plugin release locally

After the bump commit and tag of a final release, `hatch run build:bump` SHALL prepare the plugin release in the local plugin checkout without pushing anything:
- It SHALL create the annotated tag `robotcode--vX.Y.Z` on the commit recorded in `chat-plugins/.upstream.json`. The tag SHALL be signed when the maintainer's git configuration signs tags.
- It SHALL fast-forward the local `main` branch to that commit.
- It SHALL print the command that pushes `main` and the tag.

The preparation SHALL be rerunnable by hand for a given version. A tag or `main` that is already in the expected state SHALL be left as it is. It SHALL fail with a message, changing nothing, when the tag exists on a different commit or `main` cannot be fast-forwarded to the commit. For a prerelease version, it SHALL do nothing.

#### Scenario: Prepare after bump
- **WHEN** `hatch run build:bump` creates the RobotCode release 2.9.0 and the recorded commit is `abc1234`
- **THEN** the local plugin checkout has the tag `robotcode--v2.9.0` on `abc1234`, its local `main` points to `abc1234`, nothing was pushed, and the output shows the push command for the plugin repository

#### Scenario: Rerun after a failure
- **WHEN** the preparation failed during the bump and the maintainer runs it again by hand for 2.9.0
- **THEN** it completes the missing parts and leaves the parts that are already done unchanged

#### Scenario: Tag on another commit
- **WHEN** the tag `robotcode--v2.9.0` already exists on a commit other than the recorded one
- **THEN** the preparation fails, names both commits, and changes neither the tag nor `main`

#### Scenario: Main not fast-forwardable
- **WHEN** the local `main` of the plugin checkout contains commits that are not ancestors of the recorded commit
- **THEN** the preparation fails with a message and leaves `main` unchanged

### Requirement: Release publishing requires the public plugin release

For a final RobotCode release, the publish job of the release workflow SHALL check, before it creates the GitHub release and before it publishes any package, two things in the public plugin repository `robotcodedev/robotframework-agent-plugins`: that the tag `robotcode--vX.Y.Z` exists and points to the commit recorded in `chat-plugins/.upstream.json`, and that `main` points to that commit. If either is not the case, the job SHALL fail with a message that names what is missing, and nothing SHALL be published. The check SHALL only read the public repository and SHALL NOT need any key, token or secret. For prereleases, the check SHALL be skipped.

#### Scenario: Plugin release pushed
- **WHEN** the tag `v2.9.0` triggers the release workflow and the plugin repository has `robotcode--v2.9.0` and `main` on the recorded commit
- **THEN** the check passes and the release is published as before

#### Scenario: Plugin release not pushed
- **WHEN** the tag `v2.9.0` triggers the release workflow but the plugin repository has no tag `robotcode--v2.9.0`, or its `main` points elsewhere
- **THEN** the publish job fails before the GitHub release is created and before any package is published, and the log says what is missing and that the plugin repository has to be pushed before the job is re-run

#### Scenario: Prerelease
- **WHEN** a prerelease tag triggers the release workflow
- **THEN** the plugin check does not run
