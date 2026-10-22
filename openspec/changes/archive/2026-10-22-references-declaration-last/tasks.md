# Tasks

## 1. Language server

- [x] 1.1 In `references.py`, let `_find_keyword_references` and `_find_variable_references` add the declaration after the references (design.md, "The declaration goes last"). Add tests to `tests/robotcode/language_server/robotframework/parts/test_references.py` that ask with the declaration and check that the last location is the declaration and every other location a usage:
  - `Log` in `data/tests/references.robot`, with the BuiltIn library's Python file last;
  - `${A_VAR_FROM_LIB}` in `data/tests/goto.robot`, with `lib/myvariables.py` last;
  - a keyword of `firstresource.resource` called in `data/tests/references.robot`, with the resource file last;
  - `Log` without the declaration, with no location in the BuiltIn library's Python file.

  Verify that the tests with the declaration pass with the change and fail without it, that the test without the declaration passes with and without it, that `hatch run test:test` passes with the existing regression outputs unchanged, and that `hatch run lint:all` passes.

## 2. Verification

- [x] 2.1 Check in the headless PyCharm with the working tree's language server (`reference_intellij_headless_harness`; wait until the IDE has stopped indexing). Use a copy of the demo project with `BuiltIn.Log    ${arg2}`, `Collections.Append To List    ${items}    b` and a test that logs `${GREETING}` from `libraries/shopvars.py`. These SHALL behave as in `specs/intellij-navigation/spec.md`:
  - LSP Reference(s) on a plain `Log`, on `Log` in `BuiltIn.Log`, on `Append To List` in `Collections.Append To List`, on `${GREETING}` and on `Add To Cart`.

  The same as before the change:
  - Show Usages on these places;
  - LSP Reference(s) on `${user}` in the body of `Open Shop As`, with the same rows. Its title reads "Variable user" instead of "Argument user" until `argument-usage-tokens`: LSP4IJ titles the popup by the first location, which is now a use of `${user}`. That change checks the title (its task 4.1);
  - `idea.log` with no new entries.
- [x] 2.2 Mark J12 as done in `playground/pycharm-befunde.md`, with the date and the commit. The report to LSP4IJ stays open there.

## Workflow follow-up

- Commit and archive only when the maintainer asks for it.
- Report the LSP4IJ point of J12 upstream only when the maintainer asks for it.
