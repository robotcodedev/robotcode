# Design

## Context

See proposal.md for the motivation. What the change builds on:

- **VS Code** (`vscode-client/extension/index.ts`, lines 50 to 71):
  - On every activation the extension compares the version in its global state `robotcode.lastVersion` with its own version and then stores its own version. VS Code does not synchronize that state unless an extension asks for it.
  - It shows the notification when the two differ, the version is no dev build (patch number 100000 or more) and `robotcode.showWhatsNewOnUpdate` is on.
  - "What's New?" opens `https://robotcode.io/news/latest/`, which the docs site redirects to the newest news post (`docs/astro.config.mjs`, lines 29 to 30).
  - The extension activates only in workspaces with Robot Framework files or a `robot.toml` (`activationEvents` in `package.json`), so the notification appears in such workspaces.
- **IntelliJ plugin** (`intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/`):
  - `RobotCodePostStartupActivity` calls `RobotCodeEnvironment.markRobotProject()` when the project contains Robot Framework files or a `robot.toml`, and `RobotCodeFileOpenedListener` calls it when such a file is opened. `markRobotProject()` acts once per project.
  - The plugin is dynamic (`require-restart="false"`). When the IDE loads a new version without a restart, the platform runs the plugin's `ProjectActivity` extensions for every open project (`StartupManagerImpl.addActivityEpListener` in intellij-community), and the plugin's services start anew.
  - The General page (`configuration/RobotCodeGeneralConfigurable.kt`) binds to `RobotCodePersonalConfiguration`, stored in `.idea/workspace.xml`. The plugin has no application-level settings yet.
  - The application-level `PropertiesComponent` keeps its values in a non-roamable file (`StoragePathMacros.NON_ROAMABLE_FILE`, `propertyService.kt` in intellij-community).
  - The balloon notification group "RobotCode" exists (`plugin.xml`).
  - The action group `dev.robotcode.robotcode4ij.actions` is the menu Tools | RobotCode and also the menu of the RobotCode status bar widget (`editor/RobotCodeStatusBarWidget.kt`). The texts of its actions are in `RobotCode.properties`.
- **Versions:** releases are plain versions such as `2.7.0`; dev builds carry a semver pre-release such as `2.8.0-dev.508` (`scripts/tools.py`), and the CI uploads them to the Marketplace channel `dev`.

## Goals / Non-Goals

**Goals:**

- The same text, link, setting, command and fresh-install behavior as VS Code, adapted to the IDE's projects and its plugin updates without restart.
- One notification per version for the whole IDE, however many projects are open or open at the same time.

**Non-Goals:**

- Announcing in projects that aren't Robot Framework projects.
- Synchronizing the noted version between machines.
- Testing an update without restart end to end; the platform behavior it relies on is described above, and the once-per-version step covers its several calls.

## Decisions

### The check runs when a project becomes a Robot Framework project

`markRobotProject()` calls the check when it marks a project. Like VS Code's activation, this limits the notification to Robot Framework projects. It also covers an update without restart: the platform runs `RobotCodePostStartupActivity` again for every open project, and the new environment service marks each Robot Framework project once more.

Alternatives:
- An own `ProjectActivity` that checks in every project: the notification would also appear in a Java or web project that has nothing to do with Robot Framework.
- `AppLifecycleListener.appStarted`: there is no project frame to show the balloon in, and it doesn't run after an update without restart.

### One application service notes the version and decides in one step

An application-level service compares the noted version with the plugin's own version, from the plugin descriptor, and notes the own version in one synchronized step. Only the call that changes the noted version may show the notification, so activities of several projects that run at the same time show it once. It notes the version in every case, also for a dev build and with the setting off, as VS Code does. Any difference counts, also a downgrade, as in VS Code.

The noted version is kept in the application-level `PropertiesComponent` under `robotcode.lastVersion`, the key VS Code uses. Its file doesn't roam, like VS Code's global state.

Alternative: keep the noted version in the new application settings. Settings Sync would carry it to another machine, which would then miss the notification after its own update.

### A dev build is a version with a pre-release part

The IntelliJ plugin's dev builds are semver pre-releases, unlike VS Code's patch numbers of 100000 or more. A version whose numeric part is followed by `-` counts as a dev build. Build metadata after `+` doesn't make a version a dev build.

### The notification uses the existing group and the browser

- The balloon goes to the group "RobotCode", with VS Code's text in `RobotCode.properties`.
- Its action "What's New?" calls `BrowserUtil.browse("https://robotcode.io/news/latest/")`, which uses the browser set under Settings | Tools | Web Browsers and Preview, and expires the notification.

Alternatives:
- A JCEF editor tab, like the report preview: the user chose the browser.
- An own notification group: the setting already switches the notification off, and a second group would add another switch for the same thing.

### The action "Show What's New" opens the same page

- A `DumbAware` action at the end of the group `dev.robotcode.robotcode4ij.actions`, after a separator, so that it appears in Tools | RobotCode and in the status bar widget's menu. Its text is VS Code's title "Show What's New".
- It is always enabled. It needs neither the language server nor a Robot Framework project, and it stays available while RobotCode is switched off for the project.
- The action and the notification's "What's New?" call one function that opens `https://robotcode.io/news/latest/` with `BrowserUtil.browse`.

Alternative: the Help menu, next to the IDE's own "What's New". All of RobotCode's actions are in Tools | RobotCode, and VS Code also files the command under RobotCode.

### An application-level settings component holds the setting

- **Storage:** A new application service, a `SimplePersistentStateComponent` stored in `robotcode.xml` in the IDE's configuration, holds `showWhatsNewOnUpdate` as `property(defaultValue = true)`. The file holds an entry only when the setting is off. Settings Sync may carry it, like VS Code's application-scope setting.
- **Page:** The General page binds a checkbox to it, after "Profiles", as the page orders its settings alphabetically. The label "Show whats new on update" is VS Code's title for the key in sentence case, as the labels rule of `intellij-settings` requires. The comment says that it applies to all projects of the IDE.
- **Apply:** The page's existing Apply stores it. The value is part of neither the language server's settings nor the discovery command line, so applying it restarts nothing.

### Tests replace the browser launcher

The platform's `BrowserUtil.browse` hands the URL to the application service `BrowserLauncher`. A test replaces that service and records the URL instead of starting a browser. The harness sets the IDE's browser to a script that writes the URL to a file, so that the user's own browser stays closed.

## Risks / Trade-offs

- [The notification appears right after the update to the first version that has this feature, also for users who installed RobotCode long ago] → That is the fresh-install behavior the user chose: no version was noted before.
- [`news/latest` shows the newest news post, which can be newer than the installed version after a delayed update] → The same as in VS Code; dev builds aren't announced.
- [The IDE closes before the balloon was seen, and the version is noted anyway] → The same as in VS Code; the news stays on the docs site.
- [A downgrade says "has been updated"] → Rare, and the same as in VS Code.

## Migration Plan

None. The setting starts with its default, and no version is noted before the first check.
