# Tasks

## 1. Declaration and documentation

- [ ] 1.1 Set `require-restart="true"` on `<idea-plugin>` in `intellij-client/src/main/resources/META-INF/plugin.xml`. Verify with a new platform test that RobotCode's descriptor, as the test IDE loaded it, requires a restart and that `DynamicPlugins.checkCanUnloadWithoutRestart` returns a reason for it. Verify that `./gradlew test` and `./gradlew verifyPlugin` in `intellij-client/` pass.
- [ ] 1.2 Say in the installation steps of `docs/src/content/docs/getting-started/pycharm.mdx` that PyCharm asks for a restart after installing RobotCode, and that RobotCode is active after it. Verify with `npm run docs:build`.

## 2. Verification

- [ ] 2.1 Check in the headless PyCharm (`reference_intellij_headless_harness`):
  - with the new build running and a project with Robot Framework files open, changing the plugin's jar no longer unloads RobotCode: the log shows no unload, and RobotCode keeps working;
  - with a build of HEAD running (`require-restart="false"`), installing the new build's zip through the API that Install Plugin from Disk uses asks for a restart instead of loading it without one; record what the IDE does, because it answers the open question of design.md.

## Workflow follow-up

- Commit and archive only when the maintainer asks for it.
