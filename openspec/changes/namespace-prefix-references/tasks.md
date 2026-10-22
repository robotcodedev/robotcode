# Tasks

## 1. Language server

- [x] 1.1 In `references.py`, let `collect` answer a position on a prefix recorded in `namespace.namespace_references` with the answer of the import the prefix names, when neither `_references_default` nor a handler for the node answered (design.md, "The prefix gets the answer of its import"). Share the code that builds the answers at an import instead of copying it. Add tests to `tests/robotcode/language_server/robotframework/parts/test_references.py` for `data/tests/references.robot` and `data/tests/goto.robot`, with positions taken from the text so that the data files stay as they are:
  - `Collections` in `Collections.Log Dictionary` in `goto.robot` gives the same locations as `Collections` in its `Library` import;
  - `BuiltIn` in `Suite Setup    BuiltIn.Log To Console` lists only calls with the prefix `BuiltIn.`, among them the four in `references.robot`;
  - `firstresource` in `firstresource.a keyword with args` gives the same locations as the import of `firstresource.resource`;
  - `lib_hello` in `lib_hello.A Library Keyword` gives the same locations as the alias `lib_hello` in its import;
  - `Log To Console` after `BuiltIn.` still lists the calls of the keyword.

  Verify that the tests on a prefix pass with the change and fail without it, that the test on the keyword passes with and without it, that `hatch run test:test` passes, and that `hatch run lint:all` passes. Of the existing regression outputs, only those of the two markers on the prefix `firstresource` in `references.robot` (line 106, columns 4 and 13) change, in every Robot Framework version, from no result to the references of the import.
- [x] 1.2 In `docs/src/content/docs/guides/vscode/finding-information.mdx`, let the section "Find references" say that Find All References on an import, or on the library or resource name in front of a keyword such as `BuiltIn` in `BuiltIn.Log`, lists where that library, resource or variable file is imported and where a keyword is called with its name in front. Verify with `npm run docs:build`.

## 2. Verification

- [x] 2.1 Check in the headless PyCharm with the working tree's language server (`reference_intellij_headless_harness`; wait until the IDE has stopped indexing). Use a copy of the demo project with `Collections.Append To List    ${items}    b`, `shop.Open Shop As    alice` and two calls prefixed with `BuiltIn.`. These SHALL behave as in `specs/intellij-navigation/spec.md`:
  - LSP Reference(s) on `Collections`, `shop` and `BuiltIn` in those calls.

  The same as before the change:
  - LSP Reference(s), Show Usages and Find Usages on the keyword after each prefix;
  - Show Usages and Find Usages on `Collections` and `shop`, which search the import;
  - `idea.log` with no new entries.

  Also note what Find Usages on `BuiltIn` finds now; it searched from the prefix and found only `class BuiltIn` before.
- [ ] 2.2 Mark J14 as done in `playground/pycharm-befunde.md`, with the date and the commit.

## Workflow follow-up

- Commit and archive only when the maintainer asks for it.
