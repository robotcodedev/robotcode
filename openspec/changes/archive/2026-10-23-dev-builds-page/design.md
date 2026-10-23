# Design

## Context

See proposal.md for the motivation. What the dev builds are is specified in `release-publishing`, `vscode-update-notification` and `intellij-update-notification`.

**Versions:**
- **VS Code extension:** a version with a patch number of 100000 or more, such as `2.7.100499`. The VS Code Marketplace accepts no semver pre-release versions.
- **PyCharm plugin:** `2.8.0-dev.631`.
- **Python packages:** `2.8.0.dev631`, a development release in the sense of PEP 440.

All three come from the same CI run. Neither the extension nor the plugin shows its What's New notification for a dev build.

**Checked on 2026-10-23:**
- PyPI has `2.8.0.dev548` and `2.8.0.dev631` of `robotcode`, and 2.7.0 as the latest release.
- `https://plugins.jetbrains.com/plugins/dev/26216` redirects to `.../plugins/list?channel=dev&pluginId=26216` and lists RobotCode `2.8.0-dev.631`. This is the URL form the JetBrains Marketplace documentation gives for a custom channel: `https://plugins.jetbrains.com/plugins/<channel>/<pluginId>`.
- `https://plugins.jetbrains.com/plugins/dev/list` answers 400 without a build number. With the build number that an IDE sends (`?build=PY-261.22158.182`), it lists the channel `dev` of every plugin that has one: 10 entries, other plugins among them. The change `intellij-marketplace-publish` names this URL.
- **How the IDE compares versions** (`VersionComparatorUtil`, see the design of `intellij-marketplace-publish`): `2.8.0-dev.631` counts as newer than `2.8.0`. In PEP 440 and for VS Code, the release counts as newer.

**Editors and Python packages:** the VS Code extension and the PyCharm plugin bring their own RobotCode Python packages, and a dev build of the extension or the plugin brings the dev versions. The `.devN` versions on PyPI matter only for the command line, for the CI and for other editors.

## Goals / Non-Goals

**Goals:**

- For each tool, one way in and one way back that a user can follow without knowing how the dev builds are published.

**Non-Goals:**

- Explaining the version scheme beyond what a user needs to recognize a dev build.
- Instructions for other tools, such as pipx or Poetry, and for `uv tool install` or `uvx`: RobotCode runs in the project's environment, next to its Robot Framework and libraries. The page shows pip and uv (`uv add`, `uv pip install`), at the maintainer's request.

## Decisions

### A page of its own in Getting Started

`docs/src/content/docs/getting-started/dev-builds.md`, title "Try the Dev Builds", sidebar label "Dev Builds", `sidebar.order` 40, between Neovim (30) and Configuration (90). Getting Started holds the pages for setting up an editor or tool (`documentation-site`, "Pages sorted into areas"), and switching to the dev builds is part of setting it up. The page is plain Markdown with one section per tool, so that each section has an anchor of its own. The Getting Started overview lists the page by itself.

Alternatives:
- A section on each editor's Get Started page: the PyPI part would have no page of its own, and the reader looking for dev builds would have to know which page to look on.
- Tabs (`.mdx`): the sections would have no anchors of their own, and the README could not link one tool directly.

### The page's content

- **Intro:**
  - a new dev build comes out in the night after `main` has changed, from the latest CI run of `main`, if that run has passed; a night without changes brings none (`release-publishing`, and the change `dev-builds-latest-run`);
  - it brings fixes and features before the next release, and can still contain bugs;
  - it shows no What's New notification.
- **VS Code:**
  - in the Extensions view, **Switch to Pre-Release Version** on RobotCode; VS Code then updates to every new dev build;
  - **Switch to Release Version** goes back to the newest release;
  - VSCodium and other editors that use Open VSX get the same pre-release there.
- **PyCharm:**
  - add `https://plugins.jetbrains.com/plugins/dev/26216` under **Settings | Plugins**, gear icon, **Manage Plugin Repositories...**;
  - then update RobotCode or install it;
  - to go back, remove the repository. Because the IDE counts a dev build as newer than the release with the same version number, it keeps the dev build until a newer release appears. Uninstalling RobotCode and installing it again from the Marketplace switches at once.
- **Python packages:**
  - pin the exact dev version, for example `pip install "robotcode[runner,analyze]==2.8.0.dev631"`; the newest one is in the release history on PyPI;
  - with uv, the same pin in `uv add` for a project that uv manages, or in `uv pip install` for an environment;
  - as the alternative for the newest dev version without its number, `pip install --pre` and uv's `--prerelease allow`, with the caveat that they allow pre-releases of every package; `uv add` then writes the found version as the lower bound, such as `>=2.8.0.dev631`;
  - to go back with pip, `pip install --upgrade` without `--pre`: pip takes the newest release, also when its version number is lower than the dev version's (checked with pip 26.2.1). With uv, pin the release: `uv add …==2.7.0` or `uv pip install …==2.7.0`; `uv pip install --upgrade` keeps the dev version. In a uv project, putting back a version range keeps the dev version in `uv.lock`, because it matches the range; `uv sync --upgrade-package robotcode` then installs the newest release.
  - Each of these ways has its own code block.
- **Reporting:** name the version from the extension's or plugin's details, or `robotcode --version`, in the issue.

### The plugin's own channel URL, not the channel list

`https://plugins.jetbrains.com/plugins/dev/26216` subscribes the IDE to RobotCode's channel `dev` only. `https://plugins.jetbrains.com/plugins/dev/list` would also bring the dev builds of every other installed plugin that publishes a channel named `dev` (see Context).

### An exact version first, allowing pre-releases as the alternative

`--pre`, and uv's `--prerelease allow`, let the installer choose pre-releases of every package it installs, Robot Framework's release candidates among them. A pinned dev version allows a pre-release only where the pin asks for one, so the page leads with the pin. At the maintainer's request it also shows both options, as the way to the newest dev version without looking up its number, and names their caveat. On 2026-10-23 both installed Robot Framework 7.5, because its newest pre-release, 7.5rc1, is older than the release. RobotCode's packages require each other in exactly the same version, so the pin takes all of them along (`release-publishing`, "A dev version of robotcode is published only together with the packages it requires").

### Labels from the sources

The page names the labels of VS Code 1.127, the extension's minimum version, and of PyCharm 2026.1, the plugin's minimum version. The labels are checked in the sources at these versions (microsoft/vscode, JetBrains/intellij-community) instead of in a running IDE.

## Risks / Trade-offs

- [A newer IDE version renames a label] → The page names the labels of the minimum versions. A rename shows up when someone follows the page; it is a one-word fix.
- [A PyCharm user stays on a dev build after removing the repository] → The page says so and gives the way to switch at once.
- [Users try dev builds and report bugs that `main` has already fixed] → The page asks for the version in the report.
