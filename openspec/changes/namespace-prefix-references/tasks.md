# Tasks

## 1. Language server

- [ ] 1.1 In `references.py`, let `collect` answer a position on a prefix recorded in `namespace.namespace_references` with the answer of the import the prefix names, when neither `_references_default` nor a handler for the node answered (design.md, "The prefix gets the answer of its import"). Share the code that builds the answers at an import instead of copying it. Add tests to `tests/robotcode/language_server/robotframework/parts/test_references.py` for `data/tests/references.robot`, with positions taken from the text so that the data file stays as it is:
  - `BuiltIn` in `Suite Setup    BuiltIn.Log To Console` lists only calls with the prefix `BuiltIn.`, among them the four in `references.robot`;
  - `firstresource` in `firstresource.a keyword with args` gives the same locations as the import of `firstresource.resource`;
  - `lib_hello` in `lib_hello.A Library Keyword` gives the same locations as the alias `lib_hello` in its import;
  - `Log To Console` after `BuiltIn.` still lists the calls of the keyword.

  Verify that the new tests pass with the change and fail without it, that `hatch run test:test` passes with the existing regression outputs unchanged, and that `hatch run lint:all` passes.

## 2. Verification

- [ ] 2.1 Check in the headless PyCharm with the working tree's language server (`reference_intellij_headless_harness`; wait until the IDE has stopped indexing). Use a copy of the demo project with `Collections.Append To List    ${items}    b`, `shop.Open Shop As    alice` and two calls prefixed with `BuiltIn.`. These SHALL behave as in `specs/intellij-navigation/spec.md`:
  - LSP Reference(s) on `Collections`, `shop` and `BuiltIn` in those calls.

  The same as before the change:
  - LSP Reference(s), Show Usages and Find Usages on the keyword after each prefix;
  - Show Usages and Find Usages on `Collections` and `shop`, which search the import;
  - `idea.log` with no new entries.

  Also note what Find Usages on `BuiltIn` finds now; it searched from the prefix and found only `class BuiltIn` before.
- [ ] 2.2 Mark J14 as done in `playground/pycharm-befunde.md`, with the date and the commit.

## Workflow follow-up

- Commit and archive only when the maintainer asks for it.
