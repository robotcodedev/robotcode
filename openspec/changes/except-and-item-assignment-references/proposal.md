# Proposal

## Why

Robot Framework sets an existing variable again with `EXCEPT    AS    ${name}` and with an item assignment such as `${items}[0]=`. This was checked in Robot Framework 5.0 to 7.5; item assignments exist since 6.1. RobotCode's analysis records neither as a reference of that variable:
- Find References misses these places.
- Rename leaves them unchanged, so after a rename they still set the old name.
- Since `argument-usage-tokens`, their names stay `variable` tokens where every other use of an argument is a `parameter` token.

The gaps were found while checking `argument-usage-tokens` against Robot Framework.

## What Changes

- `EXCEPT    AS    ${name}` with the name of an argument or a local variable is a reference of that variable, as a FOR variable with that name already is.
- On Robot Framework 6.1 and newer, an item assignment such as `${items}[0]=` or `${SUITE_DICT}[key]=` is a reference of the variable it changes, whatever its kind.
- An item assignment to a variable that does not exist reports `VariableNotFound` on its name, because Robot Framework fails there with "Variable '${name}' not found.".
- Both analysis paths, with and without the semantic model, record the same references and report the same diagnostics.
- Find References, Rename, the document highlight and the semantic tokens follow from the references and need no changes of their own.

Not part of this change:
- `EXCEPT AS` with a new name keeps defining a new local variable.
- `[Documentation]` and `[Tags]`, which already resolve their variables as Robot Framework does, with the caller's variables.

## Capabilities

### New Capabilities

- `variable-assignments`: which existing variable a statement that sets a variable refers to, and what RobotCode reports when that variable does not exist.

### Modified Capabilities

_None._

## Impact

- `packages/robot/src/robotcode/robot/diagnostics/namespace_analyzer.py` and `packages/robot/src/robotcode/robot/diagnostics/semantic_analyzer/analyzer.py`: `EXCEPT AS` records the reference, and assignments accept item assignments.
- New tests for both analysis paths. Regression outputs of Find References, document highlight and diagnostics may change where the test data contains such statements; each diff is reviewed before a reset.
- Users see more references, more places renamed and, for an item assignment to an unknown variable, a new error.
