# Tasks

## 1. Analysis

- [x] 1.1 In `namespace_analyzer.py` and `semantic_analyzer/analyzer.py`, let `visit_ExceptHeader` add a reference to an existing argument or local variable of the name (design.md, "EXCEPT AS records a reference like FOR"). Let `_analyze_assign_statement` pass `allow_items=True` to `is_assign` (design.md, "Item assignments reach their existing branch"), and let its branch for item assignments analyze the variables in the index (design.md, "The index is analyzed like other uses"). Check that the reference of an item assignment covers the name of the variable, like other references.
- [x] 1.2 Add tests that run on both analysis paths, with and without the semantic model, for every scenario of `specs/variable-assignments/spec.md`:
  - Find References and Rename on an argument set again with `EXCEPT AS`;
  - Find References on a local variable set again with `EXCEPT AS`;
  - a new name in `EXCEPT AS`, still a local variable of its own;
  - Find References and Rename on a list argument changed by an item assignment;
  - Find References on a suite variable changed by an item assignment;
  - `VariableNotFound` for an item assignment to an unknown variable;
  - Find References on a variable in the index of an item assignment, and `VariableNotFound` for an unknown one there.

  Item assignments need Robot Framework 6.1. Add to `test_semantic_tokens_variables.py` that the name of an argument in `EXCEPT AS` and in an item assignment gets a `parameter` token.

  Verify that:
  - the tests of the changed behavior pass with the change and fail without it, and the test for a new name in `EXCEPT AS` passes with and without it;
  - `test_variable_pipeline_comparison.py` and `test_semantic_tokens_flag_parity.py` pass without new xfails;
  - every changed regression output only adds these references or this diagnostic, then reset them;
  - `hatch run test:test` and `hatch run lint:all` pass.

## Workflow follow-up

- Commit and archive only when the maintainer asks for it.
