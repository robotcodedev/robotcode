# Design

## Context

See proposal.md for the motivation. The approach depends on how the language server builds code actions and how RobotCode and Robocop read their comments. All of the following was checked in the code or by running the tools on 2026-10-11:

- **Code actions:** `code_action_quick_fixes.py` collects every `code_action_*` method and sorts the results by title. A `quickfix` action carries `CodeActionData`, including `diagnostics_code`. Its edit is computed later in the matching `resolve_code_action_<method>`.
- **The quick fix today:** `code_action_disable_robotcode_diagnostics_for_line` keeps only diagnostics whose source starts with `robotcode.`. The analyzer reports `robotcode` (`DIAGNOSTICS_SOURCE_NAME`), so only `robotcode.discover` from `robotcode discover` matches, and the modifier engine is never applied to those. The resolve step inserts `    # robotcode: ignore` at the end of the line, marked with a `TODO` for the code.
- **RobotCode's modifier engine** (`diagnostics_modifier.py`):
  - The modifiers are applied to the language server's and `robotcode analyze code`'s own diagnostics.
  - An end-of-line modifier is read only from the *first* comment of a statement. `_handle_statement_comments` strips the `#` only from that comment, so `# note    # robotcode: ignore[X]` does not silence `X`, while `# robotcode: ignore[X]    # note` does (checked with `robotcode analyze code`).
  - A comment line in column 0 applies from its line to the end of the file. Before the first section, it covers the whole file (checked).
  - `ignore[A,B]` takes several codes, and actions can be chained in one comment.
- **Robocop:**
  - Since 6.0, Robocop only knows `# robocop: off=<rule>[,<rule>]` (and `# noqa`). The older `# robocop: disable` syntax was dropped.
  - Robocop finds the disabler in any comment of the line, also behind another comment. In the first comment section of the file, it covers the whole file. Several rules in one `off=` list work. All of this was checked with Robocop 9.1.0.
  - For Robocop 6.0 and newer, RobotCode reports a finding with the source `robocop` and the code `<rule id>-<rule name>`, for example `VAR02-unused-variable`. For older versions, the code is `<rule name>-<severity><rule id>`.
  - The `lint` extra of RobotCode still allows Robocop 2.0 and newer, while the development and test environments use 6.0 and newer.

## Goals / Non-Goals

**Goals:**

- Every comment the quick fixes write works with the modifier engine and with Robocop as they are today.
- Each code action request returns at most one quick fix per code and scope, with the code in the title as shown in the Problems view.

**Non-Goals:**

- No change to the modifier engine. That it ignores a modifier behind another comment stays a separate finding; the quick fix places its modifier where the engine reads it.
- No quick fixes for Robocop older than 6.0, and none that change a severity.
- No new handling of `CodeActionContext.only`: since finding A5, every code action checks it with the shared `code_action_kind_requested` (`code_action_helper_mixin.py`).

## Decisions

### D1 Which diagnostics get the RobotCode quick fixes

Exactly those with the source `robotcode`, because these are the diagnostics the modifier engine applies to. Diagnostics without a code are skipped.

- *Alternative:* keep the prefix test and add the exact source. Rejected, because it keeps offering the fix for `robotcode.discover`, where a modifier has no effect.

### D2 Where the modifier for one line goes

The resolve step reads the statement at the diagnostic's first line from the document's model and finds its comment tokens. Using the tokens means a `#` inside an argument value is not taken for a comment.

- If the line's first comment is a `# robotcode:` modifier, the code goes into its `ignore[...]` list. If that comment has no `ignore` segment, ` ignore[<code>]` is appended to it.
- Otherwise `# robotcode: ignore[<code>]` is inserted as the first comment of the line, four spaces after the last value. An existing comment then follows it, four spaces further on.

This follows the engine's rule that only the first comment of a statement counts. The variant "always append at the end" works only on lines without a comment.

- *Alternative:* change the engine so that it reads a modifier in any comment. That would be simpler for the quick fix, but it changes the engine for hand-written comments, so it stays a separate finding.

### D3 Where the modifier for the file goes

The comment lines in column 0 before the file's first section are searched for a `# robotcode:` comment. The first one found gets the code, as in D2. If there is none, a new line `# robotcode: ignore[<code>]` becomes the file's first line.

The first line is the simplest place that covers the whole file. Inserting after a leading comment block, such as a license header, would have the same effect but needs more rules.

### D4 Robocop's findings

- **When:** offered only when Robocop is installed in version 6.0 or newer, and only for diagnostics with the source `robocop`.
- **Rule name:** taken from the code. The rule id contains no hyphen, so the name is everything after the first hyphen of `<rule id>-<rule name>`. The name, not the id, goes into `off=`, because Robocop's documentation describes disablers with rule names.
- **One line:** `# robocop: off=<rule name>` is appended at the end of the line. If a comment of the line already starts with `# robocop: off=`, the name is added to its list. Robocop reads its disabler in any comment, so the order relative to other comments does not matter.
- **File:** a `# robocop: off=` comment line in column 0 before the first section gets the name; otherwise a new first line is added, as in D3.

- *Alternative:* also support Robocop older than 6.0, with its other code format and `# robocop: disable`. Rejected, because our test environments cannot cover it and Robocop 6 has dropped that syntax.

### D5 Titles, kind and sorting

- **Titles:** "Disable '<code>' for this line" and "Disable '<code>' for this file" for both sources. The code is the one shown in Problems, for example `KeywordNotFound` or `VAR02-unused-variable`.
- **Kind and diagnostics:** the actions keep the kind `quickfix` and carry their diagnostics, so editors show them at the diagnostic and in its hover.
- **`CodeActionContext.only`:** checked with the shared `code_action_kind_requested` of finding A5, like every code action: the quick fixes are offered when `only` is empty or contains `quickfix`.
- **Sorting:** stays the existing sorting by title.

### D6 Tests

A new test file in `tests/robotcode/language_server/robotframework/parts/` drives the code action and resolve steps on small test documents and checks the edited text. It also checks that the diagnostic is gone after the edit, for RobotCode by analyzing the edited text. The Robocop cases use `pytest.importorskip("robocop")` and a version check against 6.0, like `test_formatting.py`.

## Risks / Trade-offs

- **[Risk] A comment on an earlier line of the same statement.** In a statement continued with `...`, a comment on an earlier line is the statement's first comment, and the engine reads no modifier from later lines (D2). → The line quick fix would write a modifier that has no effect there. The file quick fix still works. The separate engine finding would remove the limitation; until then this case is listed in the modifiers reference.
- **[Risk] A later `reset` in column 0.** It re-enables the code from its line on, also after "Disable … for this file". → This is the documented behavior of `reset`, and the quick fix leaves other modifiers alone.
- **[Trade-off] Robocop 2.x–5.x get no Robocop quick fixes.** RobotCode's own quick fixes still work there.
- **[Risk] Editing a hand-written comment.** → Only the bracket list or the `off=` list changes, plus an appended segment. The rest of the comment, including its spacing, stays as it is.
- **[Trade-off] Old comments stay.** Comments the old quick fix wrote (a plain `# robotcode: ignore`) still silence the whole line and are not migrated.

## Migration Plan

None. The quick fixes only edit the files the user applies them to.
