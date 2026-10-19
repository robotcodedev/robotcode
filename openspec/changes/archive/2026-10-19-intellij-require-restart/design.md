# Design

## Context

See proposal.md for the motivation. What the change builds on:

- **plugin.xml:** `<idea-plugin require-restart="false">` in `intellij-client/src/main/resources/META-INF/plugin.xml`.
- **IntelliJ SDK documentation:**
  - `require-restart` is "the boolean value determining whether the plugin installation, update, or uninstallation requires an IDE restart", default `false` (Plugin Configuration File).
  - "If a plugin requires restart … specify `require-restart="true"`" (Dynamic Plugins).
- **Platform behavior** (intellij-community):
  - `DynamicPlugins.checkCanUnloadWithoutRestart` refuses a plugin that requires a restart.
  - The auto-reload of `runIde` tasks (`DynamicPluginVfsListener`, system property `idea.auto.reload.plugins`) only reloads plugins that `DynamicPlugins.checkCanLoadWithoutRestart` accepts.
- **Harness, 2026-10-19:** A changed jar made the auto-reload unload RobotCode:
  - RobotCode's file types, actions and status bar widget factory were removed.
  - The log said "Plugin dev.robotcode.robotcode4ij is not unload-safe because class loader cannot be unloaded".
  - The plugin wasn't loaded again, and RobotCode's classes were missing until the IDE restarted.
  - After the restart the file type index no longer recognized the Robot Framework files, until the index was deleted.
  - A build of HEAD behaved the same. The cause of the leak wasn't investigated.

## Goals / Non-Goals

**Goals:**

- The IDE never loads or unloads RobotCode while it runs, so it can't end up with a half-unloaded plugin.

**Non-Goals:**

- Finding the class loader leak. Once RobotCode unloads cleanly, `require-restart` can go back to `false`.

## Decisions

### Declare the restart in plugin.xml

`<idea-plugin require-restart="true">`. It is the platform's documented way for a plugin that can't be loaded or unloaded while the IDE runs. Every install, update and uninstall then asks for a restart, and the installed version keeps running until then.

Alternatives:
- Fix the leak first: its cause is unknown, and until it is fixed every update risks the half-unloaded state.
- Keep `false`: the IDE keeps trying to load and unload RobotCode while it runs, with the result above.

### Check the declaration with the loaded descriptor

A platform test reads RobotCode's descriptor as the test IDE loaded it. It checks that the descriptor requires a restart and that `DynamicPlugins.checkCanUnloadWithoutRestart` names a reason. Both are platform internals, but only the test uses them. The test catches the attribute being dropped or set back to `false`.

### Developing without auto-reload

The auto-reload of `./gradlew runIde` and of the harness's `runIdeForUiTests` stops for RobotCode, because the platform reloads only plugins that can load without a restart. A rebuilt plugin then runs after the sandbox IDE restarts. The harness starts the IDE fresh for every check anyway.

## Risks / Trade-offs

- [Users have to restart the IDE after installing or updating RobotCode] → The IDE asks for it itself, and the guide's installation steps mention it.
- [The update from a version that still declares `false` to the first version with `true` might be tried without a restart] → The new version's descriptor decides:
  - "Install Plugin from Disk" (`PluginInstaller.installFromDisk`) and the Marketplace update (`PluginDownloader.installDynamically`) both call `DynamicPlugins.allowLoadUnloadWithoutRestart` on the descriptor of the version being installed.
  - In the harness on 2026-10-19, a build of HEAD as 2.6.2 (`false`) was running. That check returned `false` for the new build's zip (`true`), so the IDE asks for a restart. For the installed version alone it returned `true`.
