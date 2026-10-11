# Proposal

## Why

Keyword breakpoints of the command-line debugger (`.break`, `.tbreak`, `robotcode robot-debug --break`) only stop when the name matches exactly as the keyword was called. Robot Framework itself ignores case, spaces and underscores in keyword names, so `get_price`, `GetPrice` or `should be equal` run the keyword but never stop at it, without any hint. A keyword with embedded arguments can't be targeted by its definition name (`Select ${animal} From List`) at all, only per concrete call. Found while triaging [#668](https://github.com/robotcodedev/robotcode/issues/668).

## What Changes

- Keyword breakpoints match keyword names like Robot Framework does: case-, space- and underscore-insensitive, with or without the owner prefix (`BuiltIn.Should Be Equal`).
- Keyword breakpoints accept the glob patterns `*`, `?` and `[chars]`, the patterns Robot Framework uses to select keywords by name in `--removekeywords name:` and `--flattenkeywords name:` (for example `BuiltIn.*` or `Select * From List`). Regular expressions are not supported.
- A keyword with embedded arguments also matches by its definition name, so `Select ${animal} From List` stops at every call. The name of a single call, such as `Select dog From List`, still matches the calls written that way. Argument values are not evaluated; stopping only for certain values stays the job of a line breakpoint in the keyword body with a condition.
- The robot-debug guide, the `--break` help and `.help break` describe the new matching instead of the exact, case- and whitespace-sensitive one.

## Capabilities

### New Capabilities

- `keyword-breakpoints`: how keyword breakpoints of the command-line debugger match the keywords that run.

### Modified Capabilities

None.

## Impact

- `packages/repl` (`_debug/controller.py`, `_debug/types.py`, `base_interpreter.py`): the keyword breakpoint match; the definition name of keywords with embedded arguments, taken from Robot Framework's result keyword.
- `packages/repl` (`cli.py`, `console_interpreter.py`): the `--break` help and the `.break`/`.tbreak` docstrings; the generated CLI reference picks up the `--break` help.
- Docs: `docs/src/content/docs/guides/robot-debug.md`; the agent skill (`references/debugging.md` in agent-plugins) states the exact match too and needs the same update and a sync.
- Tests in `tests/robotcode/repl/`.
- Not breaking: breakpoints that stop today still stop; more spellings now stop as well.
