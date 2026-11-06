# Proposal

## Why

PyCharm 2026.3, released on 2026-11-05, rewrote PyCharm's Python debug runner (JetBrains commit "PY-89567 [debugpy] move launch work off the EDT"). Since then the plugin verifier reports a compatibility problem with "Attach Python" ([#679](https://github.com/robotcodedev/robotcode/issues/679)): our runner overrides a method that is final in 2026.3. In 2026.3, Debug with "Attach Python" therefore does not start: PyCharm cannot load the runner class and shows "Error running …" with an `IncompatibleClassChangeError`. Debug without the option is not affected. The CI on `main` fails, so no dev builds come out until this is fixed. The released 2.8.0 does not contain "Attach Python", but the dev builds since 2026-10-31 do.

## What Changes

- Debug with "Attach Python" works in PyCharm 2026.3 as in 2026.1 and 2026.2: two sessions side by side, Python and Robot Framework breakpoints in one run, Stop and Rerun from both tabs, and the Python prompt.
- The runner of the Python session no longer overrides `execute(ExecutionEnvironment)` of PyCharm's `PyDebugRunner`, which became final in 2026.3. Instead, it becomes a run-starting object of its own that redirects a rerun from the Python tab to the whole run and passes every other start to an inner subclass of `PyDebugRunner`. That subclass only creates the Python session's debug process, as today.
- `verifyPlugin` again reports no compatibility problem for the released PyCharm versions in the plugin's range, so the CI on `main` passes and the dev builds come out again.
- First, the plan reproduces in the headless harness on 2026.3 what the problem breaks: only Debug with "Attach Python", or also Debug without it.
- The change `intellij-wsl-runs` describes the runner as it is after this change and notes that 2026.3 also changed how PyCharm starts pydevd with WSL interpreters.

Behaviour that users notice, for the release notes (not breaking): none compared with the released 2.8.0. Dev builds run "Attach Python" again in PyCharm 2026.3.

Not part of this change: the deprecated API usages that `verifyPlugin` lists for 2026.3, which do not fail the check; 2026.3 dropped the server mode of PyCharm's Python debugger, so our handling of it stays only for 2026.1 and 2026.2.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `intellij-debugging`: Debug with "Attach Python" works in every PyCharm version in the plugin's range, also where PyCharm's Python debug runner starts runs differently, and `verifyPlugin` reports no compatibility problem for them.

## Impact

- IntelliJ plugin (`intellij-client/`):
  - `RobotCodePythonDebugRunner` becomes a `ProgramRunner` that holds an inner `PyDebugRunner` subclass;
  - `RobotCodeDebugProgramRunner` keeps starting the Python environment through it.
  - No user-visible behaviour, setting or text changes.
- Platform API: `PyDebugRunner` and `ProgramRunner` as today; nothing new.
- CI: "Verify JetBrains Plugin (released IDE versions)" passes again.
- Planning: the design of `intellij-wsl-runs` gets two sentences.
