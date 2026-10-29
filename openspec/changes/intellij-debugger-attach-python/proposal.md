# Proposal

## Why

In PyCharm, a Robot Framework debug session stops only in Robot Framework files: breakpoints in the Python code of libraries and keywords never stop, and users have to switch to VS Code, whose "Attach Python" debugs both, or to a separate Python run configuration ([#679](https://github.com/robotcodedev/robotcode/issues/679), earlier [#460](https://github.com/robotcodedev/robotcode/issues/460)). PyCharm's own Python debugger can run the robot process, so a debug session can stop in both kinds of code without anything extra to install.

## What Changes

- A new option "Attach Python", VS Code's `robotcode.debug.attachPython`: a project default on the "Debug" settings page, off by default, and an option in the "Run & Debug" group of Robot Framework run configurations with "Project default", on and off.
- With "Attach Python" on, Debug starts the robot process under PyCharm's own Python debugger, in every setting of PyCharm's Python debugger mode, with the configuration's interpreter, environment and working directory. Nothing else has to be installed.
- The run shows two debug sessions side by side in the Debug tool window:
  - the Robot Framework session, unchanged: its tab is named after the run configuration and shows the test tree, the output, "Terminal", "Debug Console" and "Robot Debug Console", and Robot Framework breakpoints stop there;
  - a session of PyCharm's Python debugger in a tab named "Python <name>": Python line and exception breakpoints in libraries and keywords stop there, with PyCharm's Python frames and variables and PyCharm's Python debug console, whose prompt evaluates in the paused Python frame.
- Both sessions start and end together. Stop in either of them ends the run gracefully, as Stop does today, also while the run is paused in Python code.
- Run is not affected; "Attach Python" applies only to Debug.
- Only local interpreters. WSL interpreters get it with `intellij-wsl-runs`; Docker, SSH and other remote interpreters stay refused.
- The PyCharm guide describes it, and its comparison with VS Code no longer lists debugging the Python code of libraries as missing.

Behaviour that users notice, for the release notes (not breaking): debugging in PyCharm can also stop in the Python code of libraries, with the new option "Attach Python", which is off by default.

Not part of this change: WSL, Docker, SSH and other remote interpreters; one combined session for both debuggers, which the IDE's debugger does not offer; debugpy and PyCharm's "Attach to DAP"; Python debugging in runs started with Run.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `intellij-debugging`: Debug with "Attach Python" also starts a session of PyCharm's Python debugger, beside the Robot Framework session; Python breakpoints stop there; both sessions end together, and Stop in either ends the run gracefully.
- `intellij-run-configurations`: the "Run & Debug" group offers "Attach Python", and Debug starts PyCharm's Python debugger only when it is on.
- `intellij-settings`: the "Debug" page offers the project default for "Attach Python", off by default.

## Impact

- IntelliJ plugin (`intellij-client/`): the run configuration options, their editor fragments and their resolution with the project defaults; the "Debug" settings page and the project settings; the debug runner, which starts the run through a subclass of PyCharm's `PyDebugRunner` when "Attach Python" is on; a stand-in process handler for the Python session; message bundle texts; unit tests.
- Platform API: PyCharm's `PyDebugRunner` and `PyDebugProcess` from the bundled Python plugin, which the plugin already depends on; both are public in PyCharm 2026.1 and 2026.2. No new dependency.
- Documentation: the PyCharm guide's pages on debugging, running tests, configuration and the comparison with VS Code.
- Related change: `intellij-wsl-runs` will build the WSL part on this change.
