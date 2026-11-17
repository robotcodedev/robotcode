# Tasks: doc-json-deprecated-flag

## 1. Test first

- [ ] 1.1 In `tests/robotcode/repl/test_doc_cli.py`, add tests to `TestJsonOutput` for the four scenarios of the delta spec. Write a library `DepLib` with `Old Lib Kw` and `New Lib Kw` and a resource file `dep.resource` with `Old User Kw` into the `doc_project` (`_write`), each with the documentation from the spec, and read the output with `_json(...)`. Leave `test_library_as_json` as it is. Run `hatch run test.rf75:test -- tests/robotcode/repl/test_doc_cli.py -p no:cacheprovider -k TestJsonOutput` and verify that the three tests that expect `"deprecated": true` fail and the one for `New Lib Kw` passes.

## 2. Field and guide

- [ ] 2.1 In `packages/repl/src/robotcode/repl/doc_cli.py`, add `deprecated: Optional[bool] = None` as the last field of `KeywordEntry` and set it in `_keyword_entries` to `True` when `kw.is_deprecated`, otherwise leave it at `None` (design D2, D3). Verify that the tests from 1.1 pass with the command from 1.1.
- [ ] 2.2 In `docs/src/content/docs/guides/cli/browsing-documentation.md`, add to the sentence on keyword entries that a deprecated keyword also has `deprecated` with the value `true` and that the field is missing for other keywords. Check the page in the docs dev server (`npm run docs:dev`).

## 3. Verification

- [ ] 3.1 Run `hatch run test:test` (full Robot Framework matrix) and `hatch run lint:all` and confirm that both pass. Run `robotcode --format json doc keywords` on a library with a deprecated and a normal keyword and confirm that only the deprecated entry has `"deprecated": true`.
