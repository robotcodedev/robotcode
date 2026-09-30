# Design: intellij-debugger-session-builder

## Context

See proposal.md for the motivation. Verified against the sources on the `261` branch of intellij-community (262 and master where noted) and the reports of the current build:

- **Current code.** `RobotCodeDebugProgramRunner` is an `AsyncProgramRunner`.
  - `execute` saves all documents and returns `resolvedPromise(doExecute(...))`.
  - `doExecute` calls `XDebuggerManager.getInstance(project).startSession(environment, starter)`. Its `XDebugProcessStarter` runs the profile state and wraps the result in `RobotCodeDebugProcess`.
  - `doExecute` then returns `session.runContentDescriptor`.
- **Reported deprecations.** The compiler (on 261) and `verifyPlugin` (on 261, 262 and 263) report exactly these two calls. Neither is `@ApiStatus.ScheduledForRemoval`, not even on master.
- **What the deprecated calls do in 261.**
  - `XDebuggerManagerImpl.startSession(environment, starter)` is `newSessionBuilder(starter).environment(environment).startSession().getSession()`.
  - Without `showTab`, `startSession(SessionStartParams)` creates `XDebugSessionImpl(environment, manager)`, initializes it with `environment.getContentToReuse()` and returns `XSessionStartedResultImpl(session, session.getMockRunContentDescriptorIfInitialized())`.
  - `XDebugSessionImpl.getRunContentDescriptor()` returns the same `getMockRunContentDescriptorIfInitialized()`, asserting that it is not null.
  - In split debugger mode with `xdebugger.toolwindow.split.warnings` enabled, `getRunContentDescriptor()` also logs "[Split debugger] RunContentDescriptor should not be used in split mode from XDebugSession".
  - The builder path therefore creates the same session with the same content reuse and yields the same descriptor, without that log.
- **The replacement API.**
  - `XDebuggerManager.newSessionBuilder(starter)` returns an `XDebugSessionBuilder`. `startSession()` on it returns an `XSessionStartedResult` with `session` and a nullable `runContentDescriptor`.
  - The javadoc of the deprecated getter points to `XSessionStartedResult.getRunContentDescriptor()` as the value to return from `AsyncProgramRunner.execute`.
  - The platform's `GenericDebuggerRunner` in 261 does exactly `newSessionBuilder(starter).environment(env).startSession().getRunContentDescriptor()`.
- **API status.**
  - In 261, `XDebugSessionBuilder` and `XSessionStartedResult` are `@ApiStatus.Experimental` and `@ApiStatus.NonExtendable`.
  - In 262 and master, the `Experimental` annotation is gone and the members are unchanged. Only documentation comments were added.
  - `verifyPlugin` fails only on `INVALID_PLUGIN`, `COMPATIBILITY_PROBLEMS` and `MISSING_DEPENDENCIES`. Its 261 report already lists 15 experimental usages, all from LSP4IJ.

## Goals / Non-Goals

**Goals:**
- Start the debug session through the builder in the way the platform's own runners do on 261.

**Non-Goals:**
- Showing the tab differently:
  - no `showTab`, `sessionName`, `icon` or `showToolWindowOnSuspendOnly`;
  - the environment keeps deciding the tab and content reuse, as today.
- Changes to `RobotCodeDebugProcess`, the breakpoint types or the run profile state.
- Other deprecated APIs (TextMate lexer: change `intellij-textmate-lexer-api`; `DaemonCodeAnalyzer.restart()`, `DynamicBundle`, `EnvironmentVariablesComponent`).
- Support for split debugger mode beyond no longer calling the getter that warns there.

## Decisions

### D1: `newSessionBuilder(starter).environment(environment).startSession()`

`doExecute` builds the session with `newSessionBuilder`, sets only the environment and calls `startSession()`. The starter object stays as it is. This is the call the deprecated method made internally in 261, so the session, its tab and the content reuse are the same.

Alternatives considered:
- **Keeping the deprecated calls until the minimum is 262.** This avoids the experimental annotation on 261. But the code would need a second change later, and the deprecation stays reported for every supported version in the meantime. The builder's members are the same in 261 and 262, so there is no known migration risk. This trade-off was agreed before the change was planned.
- **`showTab(true)` with a session name.** The platform uses that path for sessions started outside a `ProgramRunner`. Here the environment carries the run configuration and content reuse, and the deprecated method never used `showTab`.

### D2: Return the result's descriptor as it is

`doExecute` returns `startSession().runContentDescriptor` and becomes `RunContentDescriptor?`. `execute` already returns `Promise<RunContentDescriptor?>`. There is no `!!` and no fallback to `session.runContentDescriptor`.

On the environment path the descriptor is set while the session is initialized (the session tab is created in `initializeSession`), so it is not null in practice. Today a null would have failed the assertion in the deprecated getter. `GenericDebuggerRunner` hands the nullable value on in the same way.

## Risks / Trade-offs

- [The builder is experimental in 261 and could change in a 261 update] → Its members are the same in 262 and master. `verifyPlugin` checks 261, 262 and 263 and would report a changed signature as a compatibility problem, which fails the build.
- [A new experimental usage in the 261 report hides other new ones] → Only the xdebugger entries are expected; task 2.2 checks the report for exactly those.
- [Behaviour differs from the deprecated path] → The deprecated method delegates to the same builder call in 261. The manual `runIde` check covers breakpoint, stepping, rerun and stop.

## Migration Plan

None. The plugin behaves as before, and no settings, files or minimum version change.
