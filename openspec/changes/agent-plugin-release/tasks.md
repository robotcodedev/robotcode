# Tasks

Start only after the 2.8.0 release (design.md, Migration Plan). Section 0 holds the manual steps for 2.8.0 itself. Do them before anything else.

## 0. Manual steps after the 2.8.0 release

- [ ] 0.1 After the RobotCode 2.8.0 release is published, read the SHA from `chat-plugins/.upstream.json` at the tag `v2.8.0` (expected: `0b82cd9`). Tag it signed in the plugin repository as `robotcode--v2.8.0` (`git tag -s robotcode--v2.8.0 <sha> -m "robotcode plugin for RobotCode 2.8.0"`) and push the tag. Verify that `git ls-remote --tags origin robotcode--v2.8.0` shows the tag on that SHA and that the plugin repo's `main` points to it.
- [ ] 0.2 Create `next` from the plugin repository's `main` and push it (`git push origin main:refs/heads/next`). Check out `next` locally for further plugin work. Verify that `git ls-remote --heads origin next` lists the branch.

## 1. Release script

- [ ] 1.1 Create `scripts/chat_plugin_release.py` with the shared helpers. They read the SHA from `chat-plugins/.upstream.json`, resolve the plugin checkout through `sync_chat_plugin`'s default location or `--source <path>`, detect a SemVer prerelease with `semantic-version`, and run git. Verify that `python scripts/chat_plugin_release.py --help` lists the subcommands `check`, `prepare` and `verify-published`.
- [ ] 1.2 Implement `check`, taking the version from `CZ_PRE_NEW_VERSION` or an argument. It checks the plugin versions in `plugin.json` and `SKILL.md`, the sync state (reusing `sync_chat_plugin`'s tree comparison), that the recorded SHA is on the local `next`, and that the checkout exists. Each failure gets a message naming the fix. Prereleases exit 0. Verify locally as in 2.1.
- [ ] 1.3 Implement `prepare`, taking the version from `CZ_POST_CURRENT_VERSION` or an argument. It creates the annotated tag `robotcode--vX.Y.Z` with `git tag -a` (signing per git config) and fast-forwards local `main` after `merge-base --is-ancestor`: `merge --ff-only` if `main` is checked out, `update-ref` with the old value otherwise. It is idempotent, refuses a tag on another commit or a non-fast-forward `main`, and prints the push command. Prereleases exit 0. Verify locally as in 2.2.
- [ ] 1.4 Implement `verify-published <version> [--remote <url>]` with the default `https://github.com/robotcodedev/robotframework-agent-plugins.git`. It runs `git ls-remote` for `refs/heads/main` and the tag, compares the peeled tag commit and `main` with the recorded SHA, and names what is missing and that the plugin repo has to be pushed before re-running the job. Verify locally as in 2.3.
- [ ] 1.5 Add `check-chat-plugin-release`, `prepare-chat-plugin-release` and `verify-chat-plugin-release` to `[envs.build.scripts]` in `hatch.toml`, passing `{args}`. Verify that `hatch run build:check-chat-plugin-release --help` works.

## 2. Local verification

All trials run against a throwaway clone of the plugin repository in the scratchpad, passed with `--source`. Nothing is committed and no robotcode file is changed.

- [ ] 2.1 Try `check`. A ready plugin passes. These cases each fail with the matching message: a wrong version (passed as argument, e.g. `check 2.9.9`), an out-of-sync copy (a changed file in the clone), the SHA not on `next` (`next` reset in the clone), and a missing checkout (`--source` to a non-existent path). A prerelease (`check 2.9.0-rc.0`) exits 0 without checking.
- [ ] 2.2 Try `prepare` in the clone. Verify:
  - a fresh preparation with `main` not checked out and with `main` checked out (tag on the recorded SHA, `main` fast-forwarded, push command printed);
  - a second run changes nothing;
  - a tag on another commit is refused;
  - a `main` that cannot be fast-forwarded is refused, with tag and `main` unchanged;
  - a prerelease does nothing.
- [ ] 2.3 Try `verify-published` against a local bare repository passed as `--remote`. A published release passes; a missing tag, a tag on another commit and a `main` elsewhere each fail with a message naming what is missing.

## 3. Wiring

- [ ] 3.1 In `pyproject.toml` `[tool.commitizen]`, add `"hatch run build:check-chat-plugin-release"` as the first `pre_bump_hooks` entry and `post_bump_hooks = ["hatch run build:prepare-chat-plugin-release"]`. Verify with a throwaway branch that `hatch run build:bump --dry-run` still works and that a deliberately wrong vendored version makes `hatch run build:bump` abort before committing. Delete the branch and any tag afterwards.
- [ ] 3.2 In `.github/workflows/build-test-package-publish.yml`, add the step "verify agent plugin release" to the `publish` job directly before "create github release". It runs `hatch -q run build:verify-chat-plugin-release ${{ steps.get_release_informations.outputs.release_version }}` under `if: github.ref_type == 'tag' && startsWith(github.ref, 'refs/tags/v') && steps.get_release_informations.outputs.is_prelease == 'false'`. Verify that the workflow file still parses as YAML and that the step sits before "create github release".
- [ ] 3.3 Run `hatch run build:verify-chat-plugin-release 2.8.0` locally against the real plugin repository and verify that it passes for the published 2.8.0 release.

## 4. Documentation

- [ ] 4.1 In `CONTRIBUTING.md` (Build & Release), extend the `hatch run build:bump` entry. It checks that the bundled agent plugin is ready, prepares the plugin tag and `main` locally, and the plugin repository must be pushed together with the release. Also list the three new `build` scripts. Verify that the entry reads correctly in the rendered Markdown.
- [ ] 4.2 In the plugin repository `robotframework-agent-plugins` (separate repo, outside this change's edit root, so ask before editing), rewrite step 3 of "Releasing the `robotcode` Plugin" in `CONTRIBUTING.md`. It is prepared by the RobotCode bump, pushed by the maintainer and enforced by the publish job, with the current manual commands as fallback. Verify that the section matches the implemented flow.

## 5. Checks

- [ ] 5.1 Run `hatch run lint:all` and verify that it passes.
