# Design

## Context

- `DebugController._match_breakpoint` stops at a keyword when `bp.name in (frame.short_name, frame.name)`. `frame.name` is the qualified name of the call as written (Robot Framework 7: the result's `full_name`, before that its `name`); `frame.short_name` drops the owner prefix. A call with a variable keeps the variable: `Select ${pet} From List` stays that text (checked on RF 5.0 and 7.5).
- Keyword breakpoints come from `.break`/`.tbreak` (`add_keyword_breakpoint`) and from `robotcode robot-debug --break` (`_apply_break_specs` → `set_keyword_breakpoints`). Every value of `--break` that isn't `path:line` is a keyword name.
- Robot Framework selects keywords by name with `robot.utils.Matcher(pattern, ignore="_")`: `--removekeywords name:` matches it against the keyword's full name, `--flattenkeywords name:` against `owner.name`. `Matcher` ignores case and spaces by default, `ignore="_"` adds underscores, and the pattern is a glob (`fnmatch`: `*`, `?`, `[chars]`). It exists on every supported Robot Framework version.
- For a keyword with embedded arguments, Robot Framework stores the definition name on the result keyword before the keyword starts: `source_name` from Robot Framework 7 on, `sourcename` before, for user and library keywords alike (`_config_result` / `_get_result` of the embedded-arguments runners). Other keywords have none.
- The robot-debug guide and the agent skill document the exact, case- and whitespace-sensitive match.

## Goals / Non-Goals

**Goals:**
- Match keyword names with Robot Framework's own matcher instead of rebuilding its normalization.
- Let a keyword with embedded arguments be targeted by its definition name and by patterns.

**Non-Goals:**
- Regular expressions. Robot Framework doesn't select keywords by regular expression, and at the prompt the `.` of `Library.Keyword` would need escaping.
- Evaluating argument values. A keyword breakpoint's condition sees the caller's variables, so stopping only for certain values is done with a line breakpoint in the keyword body and a condition, as the guide already describes.
- The VS Code debugger: it has no keyword breakpoints.
- A warning for names that match no keyword. Keywords of other suites and of libraries imported later aren't known when the breakpoint is set (decided with #668).

## Decisions

### Robot Framework's `Matcher` for the name

A keyword breakpoint's name becomes a `Matcher(name, ignore="_")`, built once per name and cached in the controller. It is matched against `frame.name` and `frame.short_name`, the same two names as today, so a name with or without owner prefix keeps working and every keyword name that stops today still stops. Only keyword frames (`KEYWORD`, `SETUP`, `TEARDOWN`) are matched, so a pattern such as `*` doesn't stop at `FOR`, `IF` or `RETURN`; before, `.break FOR` happened to stop at a `FOR` loop.

Alternative: normalizing with `robot.utils.normalize` and `fnmatch` ourselves. It would rebuild what `Matcher` does and could drift from Robot Framework.

Alternative: resolving the breakpoint's name like a call (`get_runner`) and comparing keyword identity. It can't handle patterns, and the result would depend on the imports of the suite that is running.

### The definition name from the result keyword

A frame keeps the definition name of a keyword with embedded arguments, bare and with its owner (`Select ${animal} From List`, `res.Select ${animal} From List`), taken from the result keyword when the frame starts. Keyword breakpoints match it besides the call names, so the definition name and patterns such as `Select * From List` stop at every call. The difference between `source_name` (Robot Framework 7) and `sourcename` (before) is resolved once at import, next to `result_qualified_name`.

Alternative: resolving each call to its keyword through the namespace (`namespace.get_runner`), as first planned. It works on every version, but it needs an extra lookup per keyword frame and Robot Framework's internal runner classes (`runner.keyword` from version 7 on, `runner._handler` before), while the result keyword already carries the name.

### The name stays as typed

`Breakpoint.name` keeps the text the user typed; `.breakpoints` shows it unchanged. The matcher lives in the controller's cache, not in the shared `Breakpoint` model.

## Risks / Trade-offs

- [A `[` in a keyword name is a pattern character] → `.break Log [x]` reads `[x]` as a character class. Robot Framework's `name:` patterns have the same rule; `[[]` stands for a literal `[`. The guide says so.
- [A broad pattern stops often] → `.break *` stops at every keyword. That is what the pattern asks for; `.delete` and `.disable` remove or pause it.
- [Several keywords share a name] → `.break Login` stops at every keyword named `Login`, as today. The owner prefix narrows it.
