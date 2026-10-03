# Tasks: variables-import-signature

## 1. Test first

- [ ] 1.1 Add `tests/robotcode/robot/diagnostics/test_variables_doc_initializer.py` (design D6):
  - write `typedvars.py` (`get_variables(env="dev", port: int = 1)`), `classget.py` (a class with `get_variables(self, env="dev")`), `classvars.py` (a class with `__init__(self, x="1")`), a static `vars.py` and `settings.yaml` to `tmp_path`, and call `get_variables_doc`;
  - assert per `RF_VERSION`: from 7.0 on, `env` and `port` accept names and positions and `port` has the type `int`; before 7.0, both are positional only and untyped; `classget` has `env` without `self`; `classvars`, `vars` and `settings` have no initializer.

  Verify with `hatch run test.rf75:test` and `hatch run test.rf61:test` on that module that the RF 7.5 cases and the `classvars`/`vars` cases on RF 6.1 fail.
- [ ] 1.2 Language server tests (design D6):
  - remove the RF ≥ 7.0 skip in `tests/robotcode/language_server/robotframework/parts/test_signature_help_documentation_links.py` and let the test check the parameter;
  - add a signature help test for `Variables    typedvars.py    ` on both analysis paths;
  - in `test_completion_argument_docs.py`, assert `env=` and `port=` items from RF 7.0 on and none before;
  - for a library keyword `def show(a, /, b="x")`, assert the item `b=` without `a=` (design D5).

  Verify on RF 7.5 that they fail.

## 2. Implementation

- [ ] 2.1 In `get_variables_doc` of `packages/robot/src/robotcode/robot/diagnostics/library_doc.py`, read `get_variables`, or else `getVariables`, of the object the variables are read from with `PythonArgumentParser("variable file").parse(...)`. Build the initializer `KeywordDoc` from the spec and the docstring (design D1, D4), replacing `VarHandler`, `InitVarHandler` and both RF 7.0 `TODO`s.
- [ ] 2.2 Before RF 7.0, make the parameters positional only and drop their types, named-only parameters and `**kwargs` (design D2).
- [ ] 2.3 Give a file without `get_variables` or `getVariables` no initializer (design D3).
- [ ] 2.4 In `packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py`, add positional-only parameters to the kinds that the named-argument items leave out (design D5).

Verify that the tests of 1.1 and 1.2 pass on RF 7.5, 7.0, 6.1 and 5.0.

## 3. Regression outputs

- [ ] 3.1 Run the language server regression suites (signature help, inlay hints, completion, hover) on RF 7.5 and RF 6.1. Review every changed output, and confirm that each change concerns a `Variables` import and matches design D2/D3. Only then reset the outputs. Nothing else may change.

## 4. Verification

- [ ] 4.1 Check in VS Code (isolated harness) on RF 7.5 with `typedvars.py`: signature help in the arguments of `Variables    typedvars.py    ` shows `env` and `port: int`, and the completion offers `env=` and `port=`.
- [ ] 4.2 Run `hatch run test:test` and `hatch run lint:all` and confirm both pass.
