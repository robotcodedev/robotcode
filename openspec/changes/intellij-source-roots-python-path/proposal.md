# Proposal

## Why

In PyCharm and IntelliJ IDEA, RobotCode ignores the folders that the project marks as content roots and source roots. A Python library or a `.resource` file in a folder marked as Sources is reported as not found in the editor, and test discovery and runs don't find it either, while PyCharm's own Python run configurations put these roots on `PYTHONPATH` by default. GitHub #430 reports this, and one user called the plugin unusable for their project because of it. Today the only ways around it are `python-path` in `robot.toml` or the "Python path" field of the Robot settings page, both filled in by hand.

## What Changes

- The Robot settings page (Settings | Languages & Frameworks | Robot Framework | Robot) gets two switches after "Python path": "Add content roots to the Python path" and "Add source roots to the Python path", like "Add content roots to PYTHONPATH" and "Add source roots to PYTHONPATH" in PyCharm's Python run configurations. Both are on by default.
- With a switch on, the content roots, or the source roots including the test source roots, of the module whose Python interpreter RobotCode uses and of the modules it depends on go on the Python path. Content roots come first, then source roots, as in PyCharm, all after the entries of "Python path" and before the Python path of a run configuration.
- The roots reach the language server's analysis, test discovery and every run, the same ways as the entries of "Python path": the server's settings and initialization options, `-P` for discovery and runs.
- Marking or unmarking a folder, adding a content root or changing a module's dependencies takes effect while the project is open: the language server restarts and test discovery runs again when the Python path changes.
- The PyCharm options "Add content roots to PYTHONPATH" and "Add source roots to PYTHONPATH" of a Robot Framework run configuration stay as they are, off by default.
- Behavior change for existing projects, not breaking: their content and source roots now reach the analysis, discovery and runs, and the switches turn this off. The project folder is usually a content root, so it is on the Python path by default, and the IDE can find a library that a run on the command line without `-P` does not find.

Not part of this change: VS Code, which has no source roots; translating the paths for WSL interpreters, which the WSL changes take care of; one language server per module with its own roots (`intellij-python-interpreter`); Python libraries attached to a module, which PyCharm also adds.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `intellij-settings`: the Robot page gets the two switches, and a new requirement says which roots go on the Python path, in which order, where they are used and when a change takes effect.
- `intellij-test-discovery`: discovery passes `-P` for the roots too.
- `intellij-language-server`: the `pythonPath` of the initialization options is empty only while neither "Python path" nor a root provides an entry.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/`:
  - the two settings in `configuration/RobotCodeProjectSettingsConfigurableProvider.kt`, default true;
  - the two checkboxes and their texts in `configuration/RobotCodeRobotConfigurable.kt` and `RobotCode.properties`;
  - the Python path with the roots in `configuration/RobotCodeServerSettings.kt` (settings tree and initialization options), `RobotCodeRobotArguments.kt` (discovery) and `execution/RobotCodeRobotOptionsMerge.kt` (runs);
  - a module root listener that announces changes through `publishRobotCodeSettingsChanged()`.
- Tests for collecting the roots, the settings tree, the discovery and run arguments, and the stored settings.
- GitHub #430: the commit closes it; the comment of 2026-10-17 announced the option.
