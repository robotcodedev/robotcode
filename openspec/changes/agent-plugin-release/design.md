# Design

## Context

- A RobotCode release starts with `hatch run build:bump`, which runs `cz bump` in the `build` hatch env. `[tool.commitizen]` uses `version_provider = "scm"` and already has `pre_bump_hooks` (`update-git-versions`, `update-changelog`, `git add .`). commitizen runs `pre_bump_hooks` before the bump commit and `post_bump_hooks` after the commit and tag. A failing pre-bump hook aborts the bump with `RunHookError`. Hooks get the versions as environment variables: `CZ_PRE_NEW_VERSION`, and `CZ_POST_CURRENT_VERSION` after the bump.
- Pushing the `vX.Y.Z` tag starts `build-test-package-publish.yml`. Its `publish` job creates the GitHub release and then publishes the packages. It already computes `is_prelease` and `release_version` and has hatch installed.
- `scripts/sync_chat_plugin.py` mirrors `plugins/robotcode/` of a local plugin checkout (default: the sibling directory `../robotframework-agent-plugins`) into `chat-plugins/robotcode/`. It writes the source `HEAD` into `chat-plugins/.upstream.json` and has a `--check` mode.
- The plugin repository's release rules (version = RobotCode version, `next` for development, `main` = released, tags `robotcode--vX.Y.Z`) are documented in its CONTRIBUTING.

## Goals / Non-Goals

**Goals:**
- None of the plugin release steps can be forgotten without the bump or the publish job stopping.
- No keys, tokens or secrets in either repository.
- The bump only works locally. Publishing happens when the maintainer pushes.

**Non-Goals:**
- Automating the steps before the bump (setting the plugin version on `next`, committing, syncing). Their result goes into the release packages, so the maintainer does them. The check enforces them.
- Pushing anything from the bump or from CI.
- Handling prereleases or older release lines.

## Decisions

**D1: Local hooks plus a read-only CI gate, no credentials.**
The bump prepares the tag and `main` locally with the maintainer's git setup. The maintainer pushes. The publish job only reads the public plugin repository and refuses to publish without the plugin release.
Alternatives:
- *A deploy key or token in robotcode's CI that pushes to the plugin repo:* needs a secret, and its tags would be unsigned.
- *A scheduled workflow in the plugin repo:* needs no secret, but GitHub disables scheduled workflows in public repositories after 60 days without activity, and the plugin repo had no commits from June to September 2026.
- *Pushing from the post-bump hook:* would publish the plugin before the maintainer decided to publish the release.

**D2: One script with three subcommands, run through `build` env scripts.**
`scripts/chat_plugin_release.py` has the subcommands `check` (pre-bump), `prepare` (post-bump) and `verify-published` (CI). They share reading `.upstream.json`, the plugin repo location and the version handling. `hatch.toml` gets `check-chat-plugin-release`, `prepare-chat-plugin-release` and `verify-chat-plugin-release`. The commitizen hooks call `hatch run build:…`, like the existing hooks. The check is the **first** `pre_bump_hooks` entry, so it fails before `update-git-versions` and `update-changelog` change files.
- The script imports `sync_chat_plugin` (it is in the same `scripts/` directory, which is on `sys.path` when a script runs). It reuses that module's default plugin location and its tree comparison, so the sync check and the sync itself cannot diverge.
- `check` and `prepare` take `--source <path>` like `sync_chat_plugin.py`, defaulting to the sibling checkout. The hooks use the default. By hand, a throwaway clone can be passed, so local trials never create tags in the real plugin checkout.
- *Rejected:* three separate scripts. They would duplicate the helpers.

**D3: The version comes from commitizen, with a CLI argument as fallback.**
`check` reads `CZ_PRE_NEW_VERSION` and `prepare` reads `CZ_POST_CURRENT_VERSION`. Both accept the version as an argument, so they can be run by hand, for example to rerun `prepare` after a failure. `verify-published` gets the version from the workflow's `release_version` output. A version with a SemVer prerelease part (`semantic-version`, already a `build` dependency) makes `check` and `prepare` exit successfully without doing anything. The workflow step skips prereleases through its `if:` condition.

**D4: Tag signing follows git configuration.**
`prepare` creates the tag with `git tag -a`. With `tag.gpgSign = true`, which the maintainer has set, git signs it, as with the existing `robotcode--v2.6.0`…`v2.7.0` tags. Local trials and machines without a signing key still work.
- *Rejected:* `-s`. It forces a key everywhere.

**D5: Fast-forward `main` only after an explicit ancestry check.**
`prepare` checks with `git merge-base --is-ancestor main <sha>` and refuses otherwise.
- If `main` is the checked-out branch of the plugin checkout, it uses `git merge --ff-only <sha>`.
- Otherwise it uses `git update-ref refs/heads/main <sha> <old>`, so a concurrent change to `main` makes the update fail instead of overwriting it.

An existing tag on the right commit and a `main` already at the commit count as done (idempotent rerun).

**D6: The CI gate uses `git ls-remote` over HTTPS.**
`verify-published` lists `refs/heads/main` and `refs/tags/robotcode--vX.Y.Z` of `https://github.com/robotcodedev/robotframework-agent-plugins.git`. It compares the peeled tag commit (`^{}`) and `main` with the SHA from the checked-out `chat-plugins/.upstream.json`. The remote URL is a parameter with this default, so it can be tried against a local bare repository.
- The step runs as `hatch -q run build:verify-chat-plugin-release <version>` directly before "create github release". A failure there leaves the GitHub release and all packages unpublished. After pushing the plugin repo, "Re-run failed jobs" repeats only `publish`, which downloads the already built artifacts.

## Risks / Trade-offs

- [The post-bump preparation fails after commitizen created the bump commit and tag] → The message says to rerun `hatch run build:prepare-chat-plugin-release X.Y.Z`. If it is forgotten, the publish gate stops the release.
- [The maintainer pushes robotcode but forgets the plugin repo] → The publish job fails before publishing and says what to push. The cost is one re-run of the job.
- [A bug in the gate can only be fixed with a new commit and tag, because the workflow runs in the version of the tagged commit] → Try `verify-published` locally against a local bare repository for every failure case. Before the first release that uses it, run it by hand against the real repository for the already published `2.8.0`.
- [The plugin checkout is missing or somewhere else on the maintainer's machine] → The check aborts and names the expected location. The hooks use the same default as `sync-chat-plugin`, and other locations work only by hand with `--source`.
- [Re-running the publish job of an older release after `main` has moved on fails the gate] → Accepted. Older releases are not republished.

## Migration Plan

1. Release 2.8.0 without this change. The plugin version `2.8.0` is already set and synced (`chat-plugins/.upstream.json` → `0b82cd9`). After the bump, tag `0b82cd9` as `robotcode--v2.8.0` by hand (signed) and push the tag. `main` is already at `0b82cd9`. Create `next` from `main` and push it.
2. Implement this change on `main` of robotcode. From then on, plugin changes go to the plugin repo's `next`.
3. The first release after 2.8.0 uses the hooks and the gate.

Rollback: remove the hook entries from `[tool.commitizen]` and the workflow step. The script can stay as a manual tool.
