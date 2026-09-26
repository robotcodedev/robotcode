# Design: repl-vars-user-at-debug-stop

## Context

- `_vars` in `packages/repl/src/robotcode/repl/console_interpreter.py` branches to `_show_frame_scopes` at a debugger stop before it reads `--user`, so the flag never reaches the grouped listing. `_show_frame_scopes` prints the `Scope`s of `DebugController.get_scopes`, whose `Variable.name` is the decorated name (`${x}`, `@{x}`, `&{x}`) from Robot Framework's `as_dict()`.
- `_is_robot_internal` matched a bare name against reserved prefixes with a `_`/space boundary. The prefix list contains prefixes no Robot Framework version sets (`TASK`, `ROBOT`, `TIMEOUT`, `FAILED`, `PASSED`, `CURDIR`), hides user variables such as `${SUITE_VAR}`, and misses the seven constant built-ins without a prefix.
- The variables Robot Framework sets itself are the global ones of `GlobalVariables._set_built_in_variables` (identical from 5.0 to 7.5) plus the suite, test and keyword variables set in `robot/running/context.py` and `BuiltIn` (`SUITE_*`, `TEST_*`, `KEYWORD_STATUS`/`KEYWORD_MESSAGE`; `TEST_METADATA` since 7.5). `${EMPTY}` and `${CURDIR}` are resolved without being stored and never appear in a listing.

## Goals / Non-Goals

**Goals:**
- `--user` works at a debugger stop and hides the same set of variables there as at the normal prompt.

**Non-Goals:**
- No change to `.vars` without `--user` or to the DAP debugger's Variables view.
- No version switch for the name set: a name that an older Robot Framework does not set simply never occurs.

## Decisions

### D1: Exact Robot Framework names instead of prefixes

`_is_robot_internal` checks the name against the set of variables Robot Framework sets itself, normalized with Robot Framework's own `normalize(name, ignore="_")`, so `${test name}` counts as `${TEST_NAME}` exactly as Robot resolves it. User decision after the prefix rule turned out to hide `${SUITE_VAR}`, which the spec's own scenario expects to be listed.

Alternatives considered:
- Keeping the prefix rule and adding the constants: smaller, but user variables such as `${SUITE_VAR}` or `${TEST_USER}` stay hidden.
- Reading the names from Robot Framework at runtime (e.g. the keys of `GlobalVariables`): covers only the global variables; the suite, test and keyword variables are set in several places while running.

### D2: One function for decorated names

`_is_robot_internal` takes the decorated name and strips the decoration itself, because both callers (`_vars` with `as_dict()` keys and `_show_frame_scopes` with `Variable.name`) have decorated names.

### D3: The result variable `${_}` is hidden too

`${_}` is not a Robot Framework variable but the REPL's own: `set_last_result` writes it into the current context after every keyword, and `run` seeds it with `None`, so a fresh session's `.vars --user` listed nothing but `${_}`, and at a stop it appeared in the paused test's scope after the first evaluated keyword. The user never defines it, and its value is already echoed as `=> …`. User decision: `--user` hides it as well. Since Robot Framework ignores underscores in variable names, `${_}` normalizes to an empty name, which is what `_is_robot_internal` checks.

## Risks / Trade-offs

- [A future Robot Framework version adds a built-in variable] → it is listed by `--user` until it is added to the set; `test_vars_user_hides_robot_variables_in_every_scope` compares the whole listing at a stop in a test body on every Robot Framework version of the matrix, so a new global, suite or test variable fails it; one that only exists in teardowns or keyword scopes would not.
