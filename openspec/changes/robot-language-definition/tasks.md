# Tasks: robot-language-definition

## 1. The module and the moved names

- [ ] 1.1 Before any edit, make a scratch project in the session's scratchpad with a `robot.toml`, a `.robot` suite with a finding, a `.robot.md` suite that calls a keyword of a `.resource` file, and that `.resource` file. Run `robotcode analyze code` there with the repository's environment and save the output. Task 4.1 compares against it.
- [ ] 1.2 Create `packages/robot/src/robotcode/robot/language_definitions.py` (D1–D3) with:
  - `ROBOTFRAMEWORK_LANGUAGE_ID` and `ROBOTFRAMEWORK_LANGUAGE`, with the content of the protocol's definition;
  - `MARKDOWN_LANGUAGE_ID` with its comment and `markdown_language_definition()`, moved unchanged from `document_formats.py`;
  - `ROBOT_LANGUAGE_IDS: Final = (ROBOTFRAMEWORK_LANGUAGE_ID, MARKDOWN_LANGUAGE_ID)`.

  Remove the two moved names and the import of `LanguageDefinition` from `document_formats.py`, with no re-export (D4). In the same task, import the two names from the new module in every file under `packages/` and `tests/` that imports them today, because an import of a removed name breaks the import of its whole package. Move the three tests of `markdown_language_definition()` unchanged from `tests/robotcode/robot/test_document_formats.py` to a new `tests/robotcode/robot/test_language_definitions.py`, with its own `requires_markdown` mark. Verify:
  - `git grep -n -E "MARKDOWN_LANGUAGE_ID|markdown_language_definition" -- packages/robot/src/robotcode/robot/document_formats.py` finds nothing;
  - `hatch run lint:all` passes;
  - `hatch run test.rf75:test -- tests/robotcode/robot tests/robotcode/analyze tests/robotcode/language_server` passes.

## 2. One definition of Robot Framework's language

- [ ] 2.1 Set the protocol's `language_definitions` to `[ROBOTFRAMEWORK_LANGUAGE]` and remove the commented-out `feature` and `markdown` definitions (D2). In `robot_framework_language_provider.py`, remove `LANGUAGE_DEFINITION` and the module constant `ROBOTFRAMEWORK_LANGUAGE_ID`: `get_language_definitions()` returns `[ROBOTFRAMEWORK_LANGUAGE]`, and `collect_workspace_folder_files()` reads `ROBOTFRAMEWORK_LANGUAGE.extensions`. Verify:
  - `git grep -n -F "LanguageDefinition(" -- packages` finds only `language_definitions.py`, twice;
  - `git grep -n -F "LANGUAGE_DEFINITION" -- packages` finds nothing;
  - `hatch run lint:all` passes, and `hatch run test.rf75:test -- tests/robotcode/analyze tests/robotcode/language_server` passes.

## 3. Gates and comparisons by name

- [ ] 3.1 Change the gates and comparisons (D3):
  - the 33 gates `@language_id("robotframework", MARKDOWN_LANGUAGE_ID)` to `@language_id(*ROBOT_LANGUAGE_IDS)`;
  - the 8 gates `@language_id("robotframework")` to `@language_id(ROBOTFRAMEWORK_LANGUAGE_ID)`;
  - the tuple comparisons in `workspace_symbols.py`, `diagnostics.py` and `references.py` to `in ROBOT_LANGUAGE_IDS` or `not in ROBOT_LANGUAGE_IDS`.

  Leave the 8 gates `@language_id(MARKDOWN_LANGUAGE_ID)` as they are, and remove imports that are no longer used. Verify:
  - `git grep -n -F '"robotframework"' -- packages` finds only `language_definitions.py` (the id and the alias), `@symbol_information_label("robotframework")` in `protocol.py` and `_ROBOT_LANGUAGES` in `utils/markdown_blocks.py`;
  - `git grep -n -F "@language_id(*ROBOT_LANGUAGE_IDS)" -- packages` finds 33 lines, `@language_id(ROBOTFRAMEWORK_LANGUAGE_ID)` 8 and `@language_id(MARKDOWN_LANGUAGE_ID)` 8;
  - `hatch run lint:all` passes, and `hatch run test.rf75:test -- tests/robotcode/analyze tests/robotcode/language_server tests/robotcode/robot` passes.

## 4. Integration

- [ ] 4.1 Run `robotcode analyze code` in the scratch project of task 1.1 again, and verify that the output is the same. Run `hatch run lint:all` and `hatch run test:test`, and verify that both pass and that the test run changes no tracked file, such as a regression baseline under `tests/`.
