# Tasks

## 1. Keyword names and patterns like Robot Framework

- [ ] 1.1 Match a keyword breakpoint's name in `packages/repl/src/robotcode/repl/_debug/controller.py` with `robot.utils.Matcher(name, ignore="_")`, cached per name, against `frame.name` and `frame.short_name`; verify with tests in `tests/robotcode/repl/test_debug_controller.py` that `get_price`, `should be equal` and `BuiltIn.Should Be Equal` stop at their keywords, `BuiltIn.*` stops at every BuiltIn keyword, `*Price` stops at `Get Price`, the names that stop today still stop, and `--break get_price` (`_apply_break_specs`) stops as well.
- [ ] 1.2 Rewrite the keyword breakpoint paragraph of `docs/src/content/docs/guides/robot-debug.md` (names match like Robot Framework, with or without owner prefix; glob patterns `*`, `?`, `[chars]`, `[[]` for a literal `[`), the `--break` help in `packages/repl/src/robotcode/repl/cli.py` and the `.break`/`.tbreak` docstrings; regenerate the CLI reference with `hatch run create-cmd-line-docs`, check that its diff only changes the `--break` help, and verify with `npm run docs:build`.

## 2. Keywords with embedded arguments

- [ ] 2.1 When neither call name matches, resolve the call to its keyword through the namespace (Robot Framework 7: `runner.keyword`, older versions: `runner._handler`, chosen once at import) and match the keyword's definition name with and without owner; verify with tests that `Select ${animal} From List` and `Select * From List` stop at `Select dog From List` and `Select cat From List`, `Select dog From List` stops at that call only, and it doesn't stop at `Select ${pet} From List` with `${pet}` set to `dog`.
- [ ] 2.2 Add the rules for keywords with embedded arguments to the keyword breakpoint paragraph of the robot-debug guide (definition name and patterns stop at every call, the name of a single call at the calls written that way, values through a line breakpoint in the keyword body); verify with `npm run docs:build`.

## 3. Agent skill

- [ ] 3.1 Update the keyword breakpoint paragraph of `plugins/robotcode/skills/robotcode/references/debugging.md` in agent-plugins to the new matching; verify that it no longer describes an exact, case- and whitespace-sensitive match.

## 4. Integration

- [ ] 4.1 Run `hatch run lint:all` and `hatch run test:test`, and verify both pass on the full Robot Framework matrix.

## Workflow follow-up

- After the agent-plugins change is committed, sync it into `chat-plugins/` with `hatch run build:sync-chat-plugin` and commit the sync.
- Archive the change after review.
