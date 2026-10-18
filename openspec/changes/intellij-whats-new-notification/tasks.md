# Tasks

## 1. The setting

- [ ] 1.1 Add an application service in `configuration/`, a `SimplePersistentStateComponent` stored in `robotcode.xml`, with `showWhatsNewOnUpdate` as `property(defaultValue = true)`. Verify with a new unit test class:
  - the `@State` storage is `robotcode.xml`, not the workspace file or `robotcodeSettings.xml`;
  - the default state serializes to no entry, and `false` survives the XML serializer.
- [ ] 1.2 Show the checkbox "Show whats new on update" on `RobotCodeGeneralConfigurable` after "Profiles", bound to the application service. Its row comment in `RobotCode.properties` says that it shows a notification with a link to the news when RobotCode was updated, and that it applies to all projects of the IDE. Verify with a new platform test of the General page:
  - the checkbox follows "Profiles" and is checked by default;
  - turning it off and applying changes the application service's value and leaves `RobotCodeProjectConfiguration` and `RobotCodePersonalConfiguration` unchanged;
  - the comment says both points.
- [ ] 1.3 Add "Show whats new on update" to the General row of the settings table in `docs/src/content/docs/guides/pycharm/configuration.mdx`, and say in the paragraph on storage that it applies to all projects and is stored with the IDE's settings. Verify with `npm run docs:build`.

## 2. The announcement

- [ ] 2.1 Add the decision as a function of the noted version, the running version and the setting, and the dev build check: a version whose numeric part is followed by `-` is a dev build, build metadata after `+` is not. Verify with unit tests:
  - no noted version, 2.7.0 to 2.8.0, and 2.8.0-dev.508 to 2.8.0 announce;
  - the same version, 2.8.0-dev.483 to 2.8.0-dev.508, and 2.7.0 to 2.8.0-dev.508 don't;
  - a downgrade announces, as in VS Code;
  - with the setting off nothing is announced;
  - `2.8.0+build.5` isn't a dev build.
- [ ] 2.2 Add the application service that compares the noted version, from `PropertiesComponent.getInstance()` under `robotcode.lastVersion`, with the plugin's version and notes it in one synchronized step. It notes the version in every case and returns whether to announce. The caller passes the version from the plugin descriptor, so that tests can pass their own. Verify with a platform test:
  - with 2.7.0 noted, the first call for 2.8.0 announces and the second doesn't;
  - with the setting off nothing is announced, and 2.8.0 is noted;
  - a dev build is noted and not announced;
  - two threads that call it at the same time for a new version get exactly one announcement.
- [ ] 2.3 Show the notification in the group "RobotCode" with VS Code's text, naming the version, and the action "What's New?", which calls `BrowserUtil.browse("https://robotcode.io/news/latest/")` and expires the notification. Put the texts in `RobotCode.properties`. Verify with a platform test that subscribes to `Notifications.TOPIC` and replaces the `BrowserLauncher` service:
  - an announcement for 2.8.0 shows one notification whose text names v2.8.0;
  - its action hands `https://robotcode.io/news/latest/` to the browser launcher.
- [ ] 2.4 Call the check from `RobotCodeEnvironment.markRobotProject()` when it marks the project, with the version from the plugin descriptor. Verify with a platform test:
  - marking the project with an older version noted shows one notification;
  - marking it again shows none;
  - marking it after `resetForTests()`, with the running version already noted, shows none.
- [ ] 2.5 Add the action "Show What's New" at the end of the group `dev.robotcode.robotcode4ij.actions`, after a separator, with its text in `RobotCode.properties`. It is `DumbAware`, always enabled, and calls the same function as the notification's action of 2.3. Add it to the table of actions in `docs/src/content/docs/guides/pycharm/index.mdx`. Verify with a platform test that replaces the `BrowserLauncher` service:
  - the action is the last one of the group, which the status bar widget's menu shows too;
  - it is enabled in a project with "Disable extension" on;
  - performing it hands `https://robotcode.io/news/latest/` to the browser launcher.

  Verify the docs with `npm run docs:build`.

## 3. Verification

- [ ] 3.1 Run `./gradlew test` and `./gradlew verifyPlugin` in `intellij-client/`; both pass. Check in the headless PyCharm (`reference_intellij_headless_harness`), with the IDE's browser set to a script that writes its arguments to a file, and the sandbox options restored afterwards:
  - a project with Robot Framework files and no noted version shows one notification for the harness build's version;
  - "What's New?" writes `https://robotcode.io/news/latest/` into the script's file;
  - Tools | RobotCode | Show What's New writes the same URL into the file;
  - with an older version noted, opening two projects with Robot Framework files shows exactly one notification;
  - a project without Robot Framework files shows none;
  - with "Show whats new on update" off and an older version noted, no notification appears, and the running version is noted.

## Workflow follow-up

- Commit and archive only when the maintainer asks for it.
