# Tasks: variables-completion-details

## 1. Test first

- [ ] 1.1 In `tests/robotcode/language_server/robotframework/parts/test_completion_argument_docs.py`, add tests that write `vars.py` (`HOST`, `PORT`, a module docstring), `settings.yaml` (`user`, `timeout`) and `needsarg.py` (`def get_variables(env)`) to `tmp_path`, request completion after `Variables    ` through the session `protocol` fixture and resolve the items (design D4). Assert:
  - for `vars.py` and `settings.yaml`, the heading `Variables <name>` and their variables with values, and no `Library` heading;
  - for `needsarg.py`, the heading and the load error, matched in part;
  - for a variable module put on the Python path with `monkeypatch.syspath_prepend`, its variables.

  Verify with `hatch run test.rf75:test -- tests/robotcode/language_server/robotframework/parts/test_completion_argument_docs.py -p no:cacheprovider` that they fail.

## 2. Fix

- [ ] 2.1 In `resolve` of `packages/language_server/src/robotcode/language_server/robotframework/parts/completion.py`, load items with `import_type == "VARIABLES"` with `get_libdoc_for_variables_import(name, (), <directory of the document>, variables=…)` and render them with `to_markdown(False)`, without a Documentation Viewer target (design D1)
- [ ] 2.2 When the loaded documentation has errors, show the error messages below the heading (design D2)
- [ ] 2.3 Remove the unreachable `CompleteResultKind.VARIABLES` mapping in the item kinds of the `Variables` import completion (design D3); verify that the tests from 1.1 pass and that `test_file_of_a_variables_import_has_no_links` still passes

## 3. Verification

- [ ] 3.1 Check in VS Code (isolated harness) with `playground/variables-completion-example`: the details of `vars.py` and `settings.yaml` in the completion of `Variables    ` equal the hover of the matching import, and a file whose `get_variables` needs an argument shows the error
- [ ] 3.2 Run `hatch run test:test` and `hatch run lint:all` and confirm both pass; confirm with `git status` that no file under `_regtest_outputs` changed
