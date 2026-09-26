# Tasks: repl-vars-user-at-debug-stop

## 1. Implementation

- [x] 1.1 In `packages/repl/src/robotcode/repl/console_interpreter.py` parse `--user` before the debug-stop branch of `_vars` and pass it to `_show_frame_scopes`, which skips the variables `_is_robot_internal` matches and prints `(none)` for a scope left empty; verify with new tests in `tests/robotcode/repl/test_debug_console.py` using the existing `_run_debug` helper (`[".vars --user", ".continue"]` at a keyword breakpoint in a suite that assigns `${local}`, defines a suite variable and assigns `${TESTDATA}`): the output contains `${local}`, the suite variable and `${TESTDATA}`, contains none of `${TEST_NAME}`, `${SUITE_NAME}`, `${OUTPUT_DIR}`, `&{OPTIONS}`, shows `Global:` followed by `(none)`, and `.vars` without the flag still lists the built-ins
- [x] 1.2 Replace the prefix rule of `_is_robot_internal` with the names Robot Framework 5.0–7.5 sets itself (see the spec), compared with Robot Framework's `normalize(name, ignore="_")`, and let it take decorated names; verify by extending `test_vars_user_flag_filters_robot_internals` in `tests/robotcode/repl/test_dot_commands.py` with the constant built-ins, a differently spelled built-in (`${suite source}`), kept look-alikes (`${SUITE_VAR}`, `${TEST_USER}`, `${TESTDATA}`), and hide the REPL's result variable `${_}` as well (a hidden `${_}` in that test, and `Evaluate` at the stop before `.vars --user` in the tests of 1.1)
- [x] 1.3 Remove the sentence "Has no effect at a debug stop, where variables are grouped by scope instead." from the `_vars` help text and describe that `--user` applies to the grouped listing too; verify that the `.help .vars` test in `tests/robotcode/repl/test_dot_commands.py` still passes and asserts the new wording

## 2. Documentation and verification

- [x] 2.1 Align `docs/03_reference/robot-debug.md` (command table row for `.vars` / `.v`) and `docs/03_reference/repl.md` (`.vars [--user]` row) with the behaviour, including the `(none)` case; verify with `npm run docs:build`
- [x] 2.2 Run `hatch run lint:all` and `hatch run test:test -- tests/robotcode/repl` on the full RF matrix (the built-in set differs by version, e.g. `&{TEST_METADATA}` on RF 7.5, all covered by the prefix rule) and confirm both pass
