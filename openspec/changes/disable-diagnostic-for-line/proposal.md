# Proposal

## Why

The quick fix "Disable '<code>' for this line" never appears for RobotCode's own diagnostics. It only considers diagnostics whose source starts with `robotcode.`, but the analyzer reports them with the source `robotcode`. And where it does appear, it writes a bare `# robotcode: ignore`, which silences every RobotCode diagnostic of the line, not the one it names. Robocop's findings, shown next to RobotCode's in the editor and in Problems, have no such quick fix at all, so users have to know and type both comment syntaxes themselves.

## What Changes

- **Disable for this line, fixed:** "Disable '<code>' for this line" appears for every diagnostic with the source `robotcode` and writes `# robotcode: ignore[<code>]`, so only that code is silenced. If the line already has a `# robotcode:` comment, the code goes into it instead of a second comment.
- **Disable for this file, new:** "Disable '<code>' for this file" writes `# robotcode: ignore[<code>]` as a comment at the top of the file, or adds the code to such a comment that is already there.
- **Robocop's findings, new:** the same two quick fixes for findings with the source `robocop`, when Robocop 6.0 or newer is installed. They write Robocop's own disabler, `# robocop: off=<rule>`, at the end of the line or at the top of the file, and add the rule to such a comment that is already there.
- **Only ignoring:** no quick fixes that change a severity; that stays with `robot.toml`, the editor settings and hand-written modifier comments.
- **Docs:** the reference page on diagnostics modifiers and the VS Code guide's page on diagnostics name the new quick fixes.

Not in this change, kept as separate findings: a check or completion for typos in `# robotcode:` comments, reporting modifiers that no longer suppress anything, and that a `# robotcode:` modifier written behind another comment of the line is ignored.

## Capabilities

### New Capabilities

- `diagnostic-suppression`: how users suppress single diagnostics of RobotCode and Robocop from the editor, with quick fixes that write the matching comment for a line or a file.

### Modified Capabilities

None.

## Impact

- **Language server:** `packages/language_server/src/robotcode/language_server/robotframework/parts/code_action_quick_fixes.py` (the existing quick fix and its resolve step), plus the Robocop version and rule names from `robocop_helper.py` and `robocop_diagnostics.py`. Any client that shows code actions gets the quick fixes; there is no client-side code.
- **Tests:** a new end-to-end test for the quick fixes in `tests/robotcode/language_server/robotframework/parts/`, with test data; so far no test covers `code_action_quick_fixes.py` end to end.
- **Docs:** `docs/src/content/docs/reference/diagnostics-modifiers.md` and `docs/src/content/docs/guides/vscode/diagnostics-and-linting.mdx`.
- **Behavior:** files get comments that silence one code instead of all codes of the line; existing `# robotcode: ignore` comments written by the old quick fix stay as they are.
