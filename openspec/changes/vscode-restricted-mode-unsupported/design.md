# Design: vscode-restricted-mode-unsupported

## Context

See proposal.md, Why. The facts below were measured on 2026-11-08 in the isolated harness (`playground/robotcode-demo/vscode/`, Workspace Trust switched on), with VS Code 1.145.2 and a test folder whose `robot.toml` has an `expr` that writes a marker file and whose suite imports `Library    evil.py`, a library that writes a marker file at import:

| Run | Restricted Mode | After "Trust" |
|---|---|---|
| Today (`limited`), real `ms-python.python` 2026.10.0, `vscode-python-envs` 1.42.0, `debugpy` 2026.6.0 | RobotCode and the Python extensions not available to the extension host, `.robot` opens as Plain Text, no marker | everything active without a reload, both markers written |
| `limited`, stub `ms-python.python` that declares `untrustedWorkspaces: true` | **RobotCode active, both markers written** | n/a |
| `false`, real Python extensions | as today | active without a reload, both markers written |
| `false`, the permissive stub | RobotCode not available, Python stub installed but inactive, no marker | active without a reload, both markers written |

- `ms-python.python` 2026.10.0 and `ms-python.vscode-python-envs` 1.42.0 declare `untrustedWorkspaces: false`; VS Code 1.145.2's `product.json` overrides nothing. RobotCode's `extensionDependencies` are `ms-python.python` and `ms-python.debugpy`.
- VS Code's Workspace Trust guide: with `false` the extension "will remain disabled until Workspace Trust is granted"; with `"limited"` the extension itself must disable trust-sensitive features, and `restrictedConfigurations` withholds workspace values of listed settings.
- The extension never reads `vscode.workspace.isTrusted` and declares no `restrictedConfigurations`. The settings `robotcode.python`, `robotcode.languageServer.extraArgs` and `robotcode.robot.pythonPath` have the scope `resource`, so a workspace's `.vscode/settings.json` sets them.
- PyCharm 2026.1 (UI-test sandbox): "Preview in Safe Mode" opens the project without its `.idea`. The only module is a placeholder named `untrusted` without an SDK, the project SDK is null, and RobotCode logs "no module has a Python interpreter". With the `.robot` file open for two minutes, no marker appeared. Trusted control: the SDK is loaded and both markers appear within about 20 s. Neither the plugin nor LSP4IJ checks project trust; the plugin takes its interpreter from the module's SDK only.

## Goals / Non-Goals

**Goals:**
- RobotCode stays disabled in untrusted workspaces because of its own declaration, independent of the Python extension's.

**Non-Goals:**
- A partial RobotCode in Restricted Mode (see D1).
- `capabilities.virtualWorkspaces` stays `"limited"`.
- The IntelliJ plugin (see D3).
- The CLI: a `robot.toml` from a repository is as trusted as the tests in it, which `robotcode` runs anyway.
- The descriptions of `expr` and `if` in `robot.toml` say "For security reasons, only certain expressions and functions are allowed". That is a separate point, not part of this change.
- No documentation change: what users see in Restricted Mode stays the same.

## Decisions

### D1: `"supported": false` instead of a working `"limited"`

The extension declares `false`.

Alternative: keep `"limited"` and make it true. The extension would have to:
- check `vscode.workspace.isTrusted` before the language server, test discovery, the REPL and notebooks, the Documentation Viewer, the Keywords view, the language model tools and the debug configuration providers;
- list every setting that names an executable or adds arguments in `restrictedConfigurations`;
- drop the hard dependency on `ms-python.python`, which is disabled in Restricted Mode.

Rejected: that is code at many places, each forgotten one reopens the gap, and users would gain nothing they have today, since RobotCode is already disabled in Restricted Mode (measured). Declarative grammars and language configuration would only help if they lived in an extension without a `main` entry point, which is not planned.

### D2: The description

`capabilities.untrustedWorkspaces.description` explains why the extension needs trust. VS Code shows it where it explains that the extension is disabled in Restricted Mode. Text:

> RobotCode is not available in untrusted workspaces: to analyze, discover and run tests, it runs code of the workspace, such as its Python libraries and the expressions in robot.toml.

### D3: PyCharm unchanged

In Safe Mode PyCharm itself keeps RobotCode from starting: no `.idea`, so no module SDK, so no interpreter (measured, see Context). Not measured: whether a user can assign an interpreter to a project in Safe Mode, in which case RobotCode would start. A trust check in the plugin is left for a later change if that turns out to be possible.

### D4: Verification without an automated test

The extension tests run in a trusted window and could only assert the value in `package.json`. The behaviour is checked in the harness instead, before and after, as in the table above: the "before" is the measurement of 2026-11-08.

## Risks / Trade-offs

- [Workspace Trust switched off by the user (`security.workspace.trust.enabled: false`)] → every workspace counts as trusted and RobotCode starts as before; that is the user's choice.
- [Users who expect RobotCode in Restricted Mode] → there are none today: RobotCode is already disabled there with the current Python extension.
- [A future Python extension that runs in Restricted Mode] → with `false`, RobotCode stays disabled all the same (measured with the stub).

## Migration Plan

None. Rollback: set the value back to `"limited"`.
