# Proposal: robot-language-definition

## Why

Since `markdown-suites`, Markdown has a language of its own: `MARKDOWN_LANGUAGE_ID` and `markdown_language_definition()` in `robotcode.robot.document_formats`. Robot Framework's own language is still written out where it is used. Its definition (`.robot`, `.resource`, aliases) exists twice with the same content: in the language server's protocol and in the analyze provider, which also has a constant `ROBOTFRAMEWORK_LANGUAGE_ID` of its own. The id `"robotframework"` is a string literal in 41 `@language_id` gates and in three direct comparisons, and 36 of these places name the pair `"robotframework", MARKDOWN_LANGUAGE_ID` themselves. Maintainer question (2026-11-14): "sollten wir sowas auch für robotframework als language anlegen? momentan ist das ja größtenteils hart verdrahtet".

## What Changes

- **One module for the languages.** A new module `robotcode.robot.language_definitions` (`packages/robot/src/robotcode/robot/language_definitions.py`) holds:
  - `ROBOTFRAMEWORK_LANGUAGE_ID` and `ROBOTFRAMEWORK_LANGUAGE`, the one definition of Robot Framework's language, with its extensions and aliases as today;
  - `MARKDOWN_LANGUAGE_ID` and `markdown_language_definition()`, moved unchanged from `document_formats.py`, which keeps the document formats;
  - `ROBOT_LANGUAGE_IDS`, the languages whose documents hold Robot Framework data: Robot Framework's and Markdown's.
- **One definition.** The language server's protocol and the analyze provider both use `ROBOTFRAMEWORK_LANGUAGE`. The analyze provider loses its `LANGUAGE_DEFINITION` and its own `ROBOTFRAMEWORK_LANGUAGE_ID`. The commented-out definitions in the protocol go.
- **Gates by name.** The 33 gates for both languages become `@language_id(*ROBOT_LANGUAGE_IDS)`, the eight gates for Robot Framework alone `@language_id(ROBOTFRAMEWORK_LANGUAGE_ID)`, and the three comparisons `in ROBOT_LANGUAGE_IDS`. The eight Markdown gates keep `MARKDOWN_LANGUAGE_ID`, now imported from the new module.
- **Behaviour.** None changes: the ids, extensions, aliases and the documents each handler serves stay the same.

## Capabilities

### New Capabilities

<!-- none -->

### Modified Capabilities

<!-- none -->

None, so the change sets `skip_specs: true` in `.openspec.yaml`. No requirement under `openspec/specs/` names a language id, a language definition or the module they live in, and the change keeps every id, extension and the documents each handler serves.

## Impact

- Code: `packages/robot/src/robotcode/robot/language_definitions.py` (new), `document_formats.py` and `diagnostics/{document_cache_helper.py, imports_manager.py}` in the same package; `packages/language_server/src/robotcode/language_server/robotframework/protocol.py` and the parts under `robotframework/parts/` that import `MARKDOWN_LANGUAGE_ID` or gate on `"robotframework"`; `packages/analyze/src/robotcode/analyze/code/{robot_framework_language_provider.py, markdown_language_provider.py}`.
- Tests: the three tests of `markdown_language_definition()` move from `tests/robotcode/robot/test_document_formats.py` to a new `tests/robotcode/robot/test_language_definitions.py`. Two other test files import `MARKDOWN_LANGUAGE_ID` from the new module.
- Not affected: the VS Code extension, the IntelliJ plugin, the docs, `robot.toml` and the generated files.
