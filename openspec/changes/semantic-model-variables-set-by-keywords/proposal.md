# Proposal: semantic-model-variables-set-by-keywords

## Why

`Set Local Variable`, `Set Test Variable`, `Set Task Variable`, `Set Suite Variable` and `Set Global Variable` create variables at run time, and the analysis does not know them. It reports `VariableNotFound` on the name in `Set Test Variable    ${x}    1` and on every later `${x}` that Robot Framework resolves, on both analysis paths and every Robot Framework version (checked on 5.0.1 and 7.5). The common case is a keyword such as `Login` that sets `${TOKEN}` for the tests that call it, and every use of `${TOKEN}` is then an error in the editor and in `robotcode analyze code`. After `semantic-model-cleanup` the semantic-model path is the only one, so the five keywords can become definitions there.

## What Changes

- The five keywords define the variable their first argument names, in every form Robot Framework accepts: `${name}`, `\${name}` and `$name`, and the same with `@` and `&`. The name is no use of a variable. Variables nested in the name are uses and follow the rules of a `VAR` name. Without a value, the name is also a use of the variable whose value Robot Framework copies.
- In the test or keyword with the call, the variable is known after the call, whatever its scope. A variable of `Set Local Variable` is known nowhere else.
- A variable that a keyword of the file or of an imported resource sets with test, suite or global scope is known in every test and keyword of the file, also when it is set with `VAR`. One that a test or the suite setup sets with suite or global scope is known in the other tests and keywords as well. Which test calls a keyword, and in which order tests run, is not known statically, so the order does not count.
- When several calls set the same variable, or the variable exists already, the first definition is the variable and the other names are references of it. Find References and Rename cover all of them in their written form.
- The name gets a variable token, like the name of a `VAR` statement.
- Hover, completion, inline values and debug expressions see these variables through the model's lookup.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `variable-assignments`: the five keywords define variables; where they are known; several definitions of the same variable.
- `semantic-highlighting`: "Variable tokens where Robot Framework defines variables" gets the name that these keywords take.

## Impact

- **Prerequisite (hard gate)**: `semantic-model-cleanup` is archived, and with it `semantic-model-feature-tests`, whose fix RK1 stops the model from looking up `\${name}` and `$name` as keyword names. `semantic-model-variables-at-cursor` is archived as well: its decision D6 makes `VAR` variables of every scope visible after their line in their test or keyword, and this change extends that to the five keywords and adds the visibility in other tests and keywords for both.
- **Code**:
  - the `SemanticAnalyzer` (`analyzer.py`, `model.py`): definitions for the five BuiltIn keywords, their visibility and the model's lookup;
  - `library_doc.py`: a user keyword's documentation records the variables its body sets with test, suite or global scope;
  - `parts/semantic_tokens.py` only through the analyzer's tokens.
- **Features that change**: diagnostics, Find References, Rename, hover, completion, semantic tokens, inline values and debug expressions.
- **Specs written at implementation**: `inline-values` ("Visibility at the stopped position") and `debug-expressions` ("Definitions") list where variables come from. `semantic-model-variables-at-cursor` modifies both requirements, so their deltas for this change are written once that change is archived (task 1.2).
- **Cache**: the keyword documentation gains a field; a new RobotCode version empties the caches, and development caches need clearing.
- **Tests**: `test_variable_assignments.py` and `test_semantic_tokens_rules.py` in `tests/robotcode/language_server/robotframework/parts/`, analyzer tests in `tests/robotcode/robot/diagnostics/test_semantic_analyzer/`.
- Not breaking. Fewer false errors; a use before the variable is set at run time is no longer reported where the order is not known statically.
