# Proposal: code-action-and-selection-range-fixes

## Why

Surround, Extract Keyword, the variable quick fixes, Add argument and the selection ranges have no model branch; the same code runs on both analysis paths, and everyone sees its bugs today. The worst: since Robot Framework 6.1, Extract Keyword creates the keyword without `[Arguments]` and `RETURN`, so the extracted code refers to variables it does not define. Other quick fixes write code that fails at run time or edit the wrong place.

## What Changes

- **Extract Keyword** gets its `[Arguments]` and `RETURN` back on Robot Framework 6.1 and newer, and its two edits no longer overlap.
- **Surround** accepts `BREAK` and `CONTINUE` and an inline IF on every supported version. It rejects a selection that reaches into the next test or keyword. Its edit stays inside the document, and it selects the right placeholder afterwards. The title "TRY...EXCEPT...FINALLY" gets its third dot.
- **Create Keyword** writes `@{args}` for a list and `&{kwargs}` for a dictionary argument, and each name once.
- **Create local variable and Create suite variable** write a list or a dictionary where the variable is one; from Robot Framework 7.0 on, Create local variable writes `VAR`. Create local variable puts the assignment before the whole IF or TRY when the variable is used in `ELSE IF` or `EXCEPT`, and is not offered for a default value of `[Arguments]`. Create suite variable selects the right placeholder afterwards.
- **Add argument** inserts before `&{…}` and before an argument whose default value needs the new one.
- **New sections** that code actions create are in the language of the file and come after its `Language:` line.
- **Code action ranges** reach the editor in UTF-16, as rename already sends them.
- **Selection ranges** return one result for each requested position.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

The three capabilities are created by `semantic-model-feature-tests`; this change adds requirements to them.

- `code-action-refactorings`: Surround and Extract Keyword.
- `code-action-quick-fixes`: placeholders for list and dictionary arguments and repeated names in Create Keyword; Create local variable, Create suite variable and Add argument; the language and place of new sections; the UTF-16 ranges of code actions.
- `selection-ranges`: one result per position.

## Impact

- **Code**: `code_action_refactor.py`, `code_action_quick_fixes.py`, `code_action_helper_mixin.py` and `selection_range.py` in `packages/language_server/src/robotcode/language_server/robotframework/parts/`, and the common code action part `packages/language_server/src/robotcode/language_server/common/parts/code_action.py`. Both analysis paths use this code; no model branch changes.
- **Tests**: new tests through the code action and selection range handlers in `tests/robotcode/language_server/robotframework/parts/`.
- **Plans**:
  - The change can be implemented at any time, independent of `semantic-model-switchover` and `semantic-model-cleanup`. It is archived after `semantic-model-feature-tests`, whose capabilities its deltas extend.
  - `semantic-model-workspace-refactorings` plans an improved Extract Keyword; this change only repairs the existing one.
- Not breaking.
