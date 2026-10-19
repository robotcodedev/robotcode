# Proposal

## Why

The IntelliJ plugin declares `require-restart="false"`, so the IDE tries to install, update and uninstall it without a restart. RobotCode can't be unloaded cleanly yet. When the harness IDE reloaded the plugin on 2026-10-19, it first removed RobotCode's extensions: file types, status bar widget and actions. It then reported "Plugin dev.robotcode.robotcode4ij is not unload-safe because class loader cannot be unloaded" and did not load the new version. Until a restart the IDE ran without RobotCode, and afterwards the file type index no longer recognized the Robot Framework files until it was deleted. A build of HEAD showed the same.

## What Changes

- `plugin.xml` declares `require-restart="true"`. Installing, updating and uninstalling RobotCode then ask for a restart of the IDE, and the change takes effect after it. Until then the installed version keeps working.
- The installation steps of the PyCharm guide say that PyCharm asks for a restart.
- While developing, the IDE started by `./gradlew runIde` no longer reloads a rebuilt plugin by itself; the sandbox IDE has to be restarted.

Not part of this change: finding and fixing the class loader leak that keeps the plugin from unloading, which would make an update without restart possible again.

## Capabilities

### New Capabilities

- `intellij-plugin-installation`: how installing, updating and uninstalling the IntelliJ plugin take effect.

### Modified Capabilities

_None._

## Impact

- `intellij-client/src/main/resources/META-INF/plugin.xml`: the attribute of `<idea-plugin>`.
- A platform test that the loaded plugin requires a restart.
- `docs/src/content/docs/getting-started/pycharm.mdx`: the installation steps.
- The plugin's users: every install, update and uninstall of RobotCode asks for a restart.
- Contributors: the auto-reload of `runIde` and of the harness's `runIdeForUiTests` stops for RobotCode.
