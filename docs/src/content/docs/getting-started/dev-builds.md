---
title: Try the Dev Builds
description: 'Get the dev builds of RobotCode for VS Code, PyCharm and the command line, recognize their versions and go back to the releases.'
sidebar:
  label: Dev Builds
  order: 40
---

Between two releases, RobotCode publishes dev builds of the VS Code extension, the PyCharm plugin and the Python packages, built from the `main` branch. A new one comes out in the night after `main` has changed, if the CI run of its latest state has passed; a night without changes brings none. A dev build brings the newest fixes and features before the next release, and it can still contain bugs. Use it to try out a fix early or to help test the next release.

After an update to a release, RobotCode tells you about it with "RobotCode has been updated to v…" and a **What's New?** button. Dev builds don't show this notification.

## VS Code

1. Open the **Extensions** view and select **RobotCode - Robot Framework Support**.
2. Choose **Switch to Pre-Release Version** on its page.

VS Code installs the newest dev build and from then on updates RobotCode to each new one. A dev build has a patch number of 100000 or more, such as `2.7.100631`, because the VS Code Marketplace does not accept versions such as `2.8.0-dev.631`.

To go back, choose **Switch to Release Version** on the same page. VS Code then installs the newest release.

VSCodium and other editors that install their extensions from Open VSX get the same dev builds there.

## PyCharm

The dev builds of the plugin are in the channel `dev` of the JetBrains Marketplace. PyCharm only offers them after you add that channel as a plugin repository:

1. Open **Settings | Plugins** (<kbd>Ctrl+Alt+S</kbd>, <kbd>Cmd+,</kbd> on macOS), click the gear icon and choose **Manage Plugin Repositories…**.
2. In the **Custom Plugin Repositories** dialog, add `https://plugins.jetbrains.com/plugins/dev/26216` and click **OK**.
3. Update RobotCode on the **Installed** tab, or install it from the **Marketplace** tab, and restart PyCharm when it asks you to.

A dev build of the plugin has a version such as `2.8.0-dev.631`.

To go back, remove the address again in **Manage Plugin Repositories…**. PyCharm counts a dev build as newer than the release with the same version number, `2.8.0-dev.631` as newer than `2.8.0`, so it keeps the dev build until a release with a higher number comes out. To switch to the newest release at once, uninstall RobotCode and install it again from the **Marketplace** tab.

## Command line and other editors

The VS Code extension and the PyCharm plugin bring their own RobotCode packages, and their dev builds bring the matching dev versions. For the command line, a CI pipeline or another editor, the dev builds are on PyPI as development releases, such as `2.8.0.dev631`; the [release history of robotcode on PyPI](https://pypi.org/project/robotcode/#history) lists the newest one.

### Installing a dev version

pip and uv install a dev version when you name it. With pip:

```bash
pip install "robotcode[runner,analyze]==2.8.0.dev631"
```

With uv, add it to a project that uv manages, or install it into an environment with uv's pip interface:

```bash
uv add "robotcode[runner,analyze]==2.8.0.dev631"          # in a project that uv manages
uv pip install "robotcode[runner,analyze]==2.8.0.dev631"  # in an environment
```

The named version brings along the same dev version of the `robotcode-*` packages it needs. `robotcode --version` shows the installed version as `2.8.0-dev.631`.

To get the newest dev version without looking up its number, allow pre-releases instead:

```bash
pip install --pre "robotcode[runner,analyze]"
```

```bash
uv add --prerelease allow "robotcode[runner,analyze]"          # in a project that uv manages
uv pip install --prerelease allow "robotcode[runner,analyze]"  # in an environment
```

These options allow pre-releases of every package, not only of RobotCode: as soon as Robot Framework has a release candidate that is newer than its latest release, they install that as well. `uv add` writes the version it found into `pyproject.toml` as the lower bound, such as `>=2.8.0.dev631`.

### Going back to a release

With pip, upgrade without `--pre`. pip then takes the newest release, even if its version number is lower than the dev version's:

```bash
pip install --upgrade "robotcode[runner,analyze]"
```

With uv, name the release:

```bash
uv add "robotcode[runner,analyze]==2.7.0"          # in a project that uv manages
uv pip install "robotcode[runner,analyze]==2.7.0"  # in an environment
```

In a project that uv manages, putting back a version range such as `>=2.7` is not enough: uv keeps the dev version from `uv.lock`, because it matches the range. Update RobotCode afterwards to get the newest release:

```bash
uv add "robotcode[runner,analyze]>=2.7"
uv sync --upgrade-package robotcode
```

## Reporting problems

Report what you find in the [issue tracker](https://github.com/robotcodedev/robotcode/issues) and name the version of the dev build: VS Code shows it on the extension's page, PyCharm under **Settings | Plugins**, and on the command line `robotcode --version` prints it.
