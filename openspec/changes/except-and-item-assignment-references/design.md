# Design

## Context

See proposal.md for the motivation and the spec for the behavior. The current state, read from the code and checked in Robot Framework on 2026-10-22:

- **EXCEPT AS:** `visit_ExceptHeader` of `NamespaceAnalyzer` and of `SemanticAnalyzer` defines a new `LocalVariableDefinition` when no argument or local variable of the name exists, and does nothing when one exists. For the same case, `visit_ForHeader` adds the location of the name to the references of the existing variable.
- **Item assignments:** `_analyze_assign_statement` of both analyzers asks `matcher.is_assign(allow_assign_mark=True, allow_nested=True)`.
  - RobotCode's `VariableMatcher.is_assign` passes `allow_items` on to Robot Framework from 6.1 on. Without it, `${items}[0]=` is no assignment, and the method returns early.
  - The method has a branch for item assignments (`if matcher.items:`), which it never reaches today. That branch looks the variable up with `_find_variable`, reports `VariableNotFound` when it does not exist, and otherwise adds the location of the name to its references.
  - That branch does not look at the index. A variable in it, such as `${key}` in `${d}[${key}]=`, would stay without a reference or diagnostic even once the branch is reached.
- **Robot Framework**, run in the versions named:
  - `EXCEPT AS` sets an existing argument again (5.0, 6.1, 7.0, 7.3, 7.5) and an existing local variable (5.0, 6.0, 6.1, 7.5);
  - item assignments exist since 6.1: 5.0 and 6.0 read `${SUITE_DICT}[k]=` as a keyword name and fail with "No keyword with name '${SUITE_DICT}[k]=' found.";
  - an item assignment changes the existing variable of any kind, for example a suite variable (6.1, 7.5) or a list argument (7.0, 7.5);
  - an item assignment to a variable that does not exist fails with "Variable '${name}' not found." (6.1, 7.5);
  - the index is resolved: `${d}[${key}]=` uses `${key}`, and `${d}[${missing}]=` fails with "Variable '${missing}' not found." (6.1, 7.5).
- **Other places that check for assignments** (`*** Variables ***` and `VAR`) allow no item assignments, so they stay as they are.
- **The two analyzers are compared** by `test_variable_pipeline_comparison.py` for their variable resolution, and by `test_semantic_tokens_flag_parity.py` for their semantic tokens.

## Goals / Non-Goals

**Goals:**

- `EXCEPT AS` and item assignments are references of the variable they set, on both analysis paths, as FOR variables and `${name}=` already are.
- The variables in the index of an item assignment are uses, like the variables in any argument.

**Non-Goals:**

- A new name in `EXCEPT AS`, which keeps defining a new local variable.
- Changes to FOR, to `${name}=` or to `VAR`.

## Decisions

### EXCEPT AS records a reference like FOR

When an argument or a local variable of the name exists, `visit_ExceptHeader` adds the location of the stripped name to its references, as `visit_ForHeader` does.

Alternative: define a new local variable as for a new name. Find References and Rename would then treat the name as another variable, unlike Robot Framework.

### Item assignments reach their existing branch

`_analyze_assign_statement` passes `allow_items=True` to `is_assign` in both analyzers. The branch for item assignments already looks the variable up and reports what Robot Framework reports. The reference must cover the name of the variable, like every other reference, because Rename edits that range and the semantic tokens match it with the name. The tests check this.

Alternative: a separate code path for item assignments. It would repeat the lookup that the branch already has.

### The index is analyzed like other uses

In the branch for item assignments, the text after the closing brace of the variable becomes an argument token at its column. `_iter_variables_from_token` and `_handle_find_variable_result` then record the references of its variables or report them as not found, as the same method already does for the variables nested in a name. The position comes from a search without type parsing, so a type in the name does not shift it.

Alternative: leave the index out. Find References would then miss variables that Robot Framework resolves there.

### Both analyzers change together

Both analyzers get the same change in one step, so the comparison and parity suites keep them equal.

## Risks / Trade-offs

- [An item assignment to a variable that RobotCode cannot see statically, such as one set with `Set Test Variable` in another keyword, now reports `VariableNotFound`] → Every use of such a variable already does. The diagnostic can be switched off or downgraded for it as for those uses.
- [Rename now edits these places] → Intended: Robot Framework sets the same variable there.
- [Regression outputs change where the test data contains such statements] → Each diff is reviewed before a reset: it may only add these references or this diagnostic.
