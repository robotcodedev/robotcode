# Design: robot-language-definition

## Context

See proposal.md for the motivation. Verified facts:

- **The definitions.** `RobotLanguageServerProtocol.language_definitions` (`language_server/robotframework/protocol.py`) is a class attribute with one `LanguageDefinition(id="robotframework", extensions=[".robot", ".resource"], extensions_ignore_case=True, aliases=["Robot Framework", "robotframework"])` and two commented-out definitions (`feature`, `markdown`). `RobotFrameworkLanguageProvider.LANGUAGE_DEFINITION` (`analyze/code/robot_framework_language_provider.py`) has the same content, with the module constant `ROBOTFRAMEWORK_LANGUAGE_ID = "robotframework"`, which no other module imports. The provider reads `LANGUAGE_DEFINITION` in `get_language_definitions()` and, for its extensions, in `collect_workspace_folder_files()`.
- **Nothing changes a definition.** `DocumentsManager` keeps the list it gets and only reads it. The protocol adds the Markdown definition by building a new list (`[*self.language_definitions, markdown]`), and `robot_workspace.py` reads the extensions of all of them. No code assigns to a definition's fields.
- **Markdown.** `document_formats.py` holds `MARKDOWN_LANGUAGE_ID = "robotframework-markdown"` and `markdown_language_definition(profile, root)`, which uses `markdown_extensions()` and `parse_include_condition()` of the same module. 26 modules under `packages/` and three test files import one of the two from there; `tests/robotcode/robot/test_document_formats.py` has the three tests of `markdown_language_definition()`.
- **The gates.** Under `packages/` there are 49 `@language_id` gates: 33 with `("robotframework", MARKDOWN_LANGUAGE_ID)` (language server parts, `imports_manager.py`, the analyze provider), 8 with `("robotframework")` (`completion.py` and `formatting.py` twice each, `selection_range.py`, `robocop_diagnostics.py`, `folding_range.py`, `document_symbols.py`; each has a Markdown counterpart under `parts/markdown/`), and 8 with `(MARKDOWN_LANGUAGE_ID)` under `parts/markdown/`. Three comparisons name the pair as a tuple: `workspace_symbols.py` (`in`), `diagnostics.py` (`not in`) and `references.py` (`in`).
- **Other `"robotframework"` literals that are not language ids.** `@symbol_information_label("robotframework")` on the protocol is the label of symbol information, and `_ROBOT_LANGUAGES = ("robotframework", "robot")` in `utils/markdown_blocks.py` are the info strings of the Markdown fences.
- **The name `languages`.** In `robotcode-robot`, `languages` means Robot Framework's translations (`namespace.languages`, `workspace_languages`, `RobotLanguages`), and `robotcode.robot.languages` is the VS Code setting for them (`--language`).
- **Typing.** `language_id(id: str, *ids: str)`: mypy `--strict` accepts `@language_id(*GROUP)` with `GROUP: Final = (A, B)`, and `language in GROUP` with an `Optional[str]` (checked on a scratch file).

## Goals / Non-Goals

**Goals:**
- One place for the ids and definitions of the languages RobotCode serves, which the language server and `robotcode analyze code` both use.
- The gates and comparisons name a language or the group of languages with Robot Framework data instead of string literals.

**Non-Goals:**
- A registration of languages for plugins such as Gherkin: that needs a hook, which comes with the plugin.
- Deriving `RobotLanguageServerProtocol.file_extensions` from the definitions, or changing the extensions, ids or aliases.
- The language ids of the VS Code extension and the IntelliJ plugin, the symbol label, the fence info strings, and the `"unknown"` id of `DocumentsManager`.
- Language id literals in the tests, except imports of the moved names.

## Decisions

### D1: A module `robotcode.robot.language_definitions` in `robotcode-robot`

The language server and `robotcode-analyze` both depend on `robotcode-robot`, and the Markdown definition needs its profile and `document_formats`. `robotcode-core` keeps the mechanism (`LanguageDefinition`, `language_id`, `language_id_filter`), and the new module imports `document_formats`, which does not import it back. The module is named after `LanguageDefinition`.

Rejected:
- `robotcode.robot.languages`, as proposed on 2026-11-14: the name stands for Robot Framework's translations in this package and in the VS Code settings (Context).
- `robotcode-core`: it knows no Robot Framework, and the Markdown definition needs the profile.
- Keeping Markdown in `document_formats.py` and adding only Robot Framework's language: the ids and definitions would again live in two modules.

### D2: One shared instance of Robot Framework's definition

`ROBOTFRAMEWORK_LANGUAGE` is a module-level `LanguageDefinition`. The protocol's class attribute becomes `[ROBOTFRAMEWORK_LANGUAGE]`, and the analyze provider returns it from `get_language_definitions()` and reads its extensions in `collect_workspace_folder_files()`. Sharing the instance is safe, because nothing changes a definition (Context). The commented-out `feature` and `markdown` definitions go: Markdown has its real definition, and Gherkin will bring its own as a plugin.

Rejected: making `LanguageDefinition` frozen. It would guard the shared instance, but it changes a core class for a case that does not occur.

### D3: `ROBOT_LANGUAGE_IDS` for the handlers of both languages

`ROBOT_LANGUAGE_IDS: Final = (ROBOTFRAMEWORK_LANGUAGE_ID, MARKDOWN_LANGUAGE_ID)` names the languages whose documents hold Robot Framework data. A gate or comparison that names both today uses the group. One that names only `"robotframework"` uses `ROBOTFRAMEWORK_LANGUAGE_ID`, and the Markdown gates keep `MARKDOWN_LANGUAGE_ID`. A later built-in language with Robot Framework data is one entry in the group.

Rejected: a function that returns the ids of the active definitions. The gates are set when a class is defined, before any profile is read.

### D4: Moved names are imported from the new module only

`document_formats.py` loses `MARKDOWN_LANGUAGE_ID`, `markdown_language_definition()` and its import of `LanguageDefinition`, and keeps no re-export (`implicit_reexport = false`). Every importer, in `packages/` and in the tests, imports from `robotcode.robot.language_definitions`. The three tests of `markdown_language_definition()` move unchanged to `tests/robotcode/robot/test_language_definitions.py`, as the tests mirror the modules.

Rejected: a re-export in `document_formats.py`. It would keep two paths for the same name.

## Risks / Trade-offs

- [A place that names `"robotframework"` as a language id is missed] → task 4 searches `packages/` for the literal and for the old imports, and the full matrix runs.
- [The many import changes mix with the gate changes in one diff] → the tasks keep the move (imports) and the gates apart, and each ends with lint and tests.
- [Planned changes edit the same files] → about twenty open changes under `openspec/changes/` (the `semantic-model-*` series among them) plan edits in the same parts, but none of them names `@language_id`, `"robotframework"`, `MARKDOWN_LANGUAGE_ID` or the definitions, so they need no update; a handler they add later takes the names of the new module.
