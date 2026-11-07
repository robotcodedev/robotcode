# Spec Delta

## MODIFIED Requirements

### Requirement: Version bump checks that the bundled plugin is ready

Before it commits, `hatch run build:bump` SHALL check the vendored agent plugin for a final release:
- The `version` in `chat-plugins/robotcode/plugin.json`, the plugin's Agent Plugins manifest, and the `metadata.version` in the vendored `SKILL.md` SHALL equal the new RobotCode version.
- `chat-plugins/robotcode/` SHALL be in sync with the plugin in the local plugin repository checkout.
- The commit recorded in `chat-plugins/.upstream.json` SHALL be contained in that checkout's local `next` branch.

#### Scenario: Plugin ready
- **WHEN** a maintainer runs `hatch run build:bump` for 2.9.0, the vendored plugin has version `2.9.0` in `plugin.json` and `SKILL.md`, is in sync with the local plugin checkout, and its recorded commit is on the local `next`
- **THEN** the bump proceeds

#### Scenario: Version in the root manifest
- **WHEN** a maintainer runs `hatch run build:bump` for 2.9.0 and the vendored `plugin.json` in the plugin's folder says `2.8.0`
- **THEN** the bump aborts, and the message names `plugins/robotcode/plugin.json` as the file to change on the plugin repo's `next`, not a generated legacy copy
