# Tasks: disable-diagnostic-for-line

## 1. RobotCode's diagnostics: one line

- [ ] 1.1 Offer "Disable '<code>' for this line" for the diagnostics with the source `robotcode` (D1). Check `CodeActionContext.only` with `code_action_kind_requested` (D5). Verify with a new test in `tests/robotcode/language_server/robotframework/parts/`:
  - The fix is offered once per code at a `KeywordNotFound`.
  - It is not offered for diagnostics with the source `robotcode.discover` or `robocop`.
  - It is not offered for a request whose `only` holds just `refactor`.
- [ ] 1.2 Let the resolve step write `ignore[<code>]` with the placement of D2. Verify with tests on the edited text for the scenarios of "Disable a RobotCode diagnostic for one line" and "Modifier placement on a line with comments":
  - The line has no comment.
  - The line has an `ignore[...]` list.
  - The line has another action.
  - The line has a plain comment.
  - Analyzing the edited text no longer reports the code on that line but still reports another code there.
- [ ] 1.3 Describe the quick fix in `docs/src/content/docs/reference/diagnostics-modifiers.md` and in "Changing or hiding diagnostics" of `docs/src/content/docs/guides/vscode/diagnostics-and-linting.mdx`. Include where it puts the modifier and the limitation for statements continued with `...` (design, Risks). Verify that `npm run docs:build` has no link errors.

## 2. RobotCode's diagnostics: file

- [ ] 2.1 Offer "Disable '<code>' for this file" with the placement of D3. Verify with tests for both scenarios of "Disable a RobotCode diagnostic for a file", including that analyzing the edited file reports the code nowhere.
- [ ] 2.2 Add the file quick fix to the two pages of 1.3. Verify that `npm run docs:build` has no link errors.

## 3. Robocop's findings

- [ ] 3.1 Offer "Disable '<code>' for this line" and "… for this file" for the findings with the source `robocop` when Robocop 6.0 or newer is installed. Take the rule name from the code (D4). Verify with tests that skip without Robocop 6.0 or newer:
  - The edited text matches the scenarios of both Robocop requirements, including an existing `off=` list.
  - Robocop no longer reports the rule there, while it still reports it on other lines.
  - With an older Robocop version, mocked in the module that reads it, no Robocop fixes are offered.
- [ ] 3.2 Describe the Robocop quick fixes in the Robocop section of `docs/src/content/docs/guides/vscode/diagnostics-and-linting.mdx`. Verify that `npm run docs:build` has no link errors.

## 4. Integration

- [ ] 4.1 Check in the isolated VS Code harness:
  - At `Submit Ordr` in `resources/orders.resource`, both RobotCode quick fixes appear, and each removes the diagnostic.
  - At a Robocop finding of the demo project, both Robocop quick fixes appear and work.
  - The extension host log shows no "code action … will be dropped" warning for these quick fixes.
- [ ] 4.2 Run `hatch run test:test` and `hatch run lint:all` and verify that both pass.

## Workflow follow-up

- Mark B3 as planned in `playground/vscode-guide-befunde.md` once the change is reviewed.
- Archive the change after review.
