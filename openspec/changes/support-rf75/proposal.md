# Proposal: support-rf75

## Why

Robot Framework 7.5 was released on 2026-09-14 and is not part of RobotCode's test matrix. Running RobotCode against it silently loses information and rejects valid input: keyword tags declared in documentation (`Tags:` lines, including `robot:private`) disappear, the standard libraries — now documented in Markdown with Google-style docstrings — render their type documentation as raw Robot markup, a library using a recursive Python 3.12 type alias loses all of its type documentation, the "show documentation" web view only shows an error for every Markdown-documented standard library because the `markdown` package is missing, `robot.toml` refuses the custom console loggers RF 7.5 accepts, `${TEST_METADATA}` is reported as an unknown variable, and `Resource    file.md` — valid in RF 7.5 — is flagged as an invalid extension. On top of that the generator that produces the `robot.toml` model is stale, so the model cannot be regenerated for the new options without first repairing it.

## What Changes

- **Test matrix and CI**: add an `rf75` environment (`robotframework~=7.5.0`) to the hatch `test` and `devel` matrices and to the GitHub workflow; record the RF 7.5 regression baselines (`_regtest_outputs/rf75/`, whose only differences to 7.4 are line numbers inside RF's own sources); rewrite the one test that imports a private RF helper renamed in 7.5; update the environment lists in `AGENTS.md`, `CONTRIBUTING.md` and the `.github` instruction files.
- **Library and resource documentation on RF ≥ 7.5** (behaviour restored to what RF ≤ 7.4 gave, without mutating Robot Framework's objects):
  - Tags declared in keyword documentation are extracted again, including `robot:private`, negated tags in resource files and backslash-unescaping of resource keyword documentation; a `Tags:` section no longer leaks into the rendered documentation in any form RF ≤ 7.4 recognised.
  - Google-style `Args:`/`Returns:`/`Raises:` sections stay in the documentation text unchanged. Separating and rendering them is the follow-up change `rf75-argument-docs`.
  - Standard type documentation (`integer`, `boolean`, …) is requested in the library's documentation format, so Markdown libraries no longer show raw Robot link syntax.
  - Recursive type aliases (`type Tree = int | list[Tree]`) no longer abort type documentation collection for the whole library.
  - Return types follow RF 7.5's model: keywords without a return annotation report no return type on every RF version; `-> None` is shown as `None` on 7.5, as RF's own Libdoc does.
  - The `markdown` package becomes a dependency of `robotcode-robot` and is bundled with the VS Code extension and the IntelliJ plugin, so Libdoc HTML generation (the documentation web view, `robotcode libdoc`) works for Markdown-documented libraries.
- **`robot.toml`**: `console` accepts a custom console class or module (RF 7.5) in addition to the built-in names, and the never-valid `skipped` value is removed; `libdoc.doc-format` and `libdoc.format` accept `MARKDOWN`; tag-pattern examples use the operator spelling RF 7.5 recommends (`foo AND bar*`). The generator `scripts/generate_rf_options.py` is repaired (it currently drops every `alias=` and a hand-added example, and under RF 7.5 would move `console`/`quiet` into the common options, which would make `robotcode rebot` pass them to `rebot` and fail on RF ≤ 7.4), then model, JSON schema and `docs/03_reference/config.md` are regenerated with documented commands. `console`/`quiet` stay `robot`-only; RF 7.5's new `rebot --console`/`--quiet` in `robot.toml` is the follow-up change `rebot-console-options`.
- **Built-in variables**: `${TEST_METADATA}` / `&{TEST_METADATA}` are known on RF ≥ 7.5, so `[Metadata]` inside tests and the variable produce no false diagnostics and the variable is offered in completion; analyzer, semantic-token and completion coverage for test-level `[Metadata]` is added.
- **Markdown files on RF ≥ 7.5**: `.md` and `.markdown` resources (including `.robot.md`) are accepted as resource imports and offered in import completion exactly like `.rst` resources today, and are kept out of the Libdoc HTML path (RF's Libdoc rejects them). Parsing the code blocks inside Markdown/reST files, `.robot.md` suites in the editor and test-explorer navigation are the follow-up change `markdown-suites`; `discover files` keeps its current list.
- **Syntax highlighting**: the deprecated French test-cases header `Unités de test` stays highlighted (RF 7.5 still accepts it and RF ≤ 7.4 requires it), the new `Cas de test` is added, and the Arabic headers missing since RF 7.3 are added, in both TextMate grammars. The generator and its template are out of sync with the committed grammar, so the regexes are edited by hand (see design).
- **Documentation**: regenerated `config.md`; regeneration procedure for the `robot.toml` model in `CONTRIBUTING.md`; a note that RF < 7.5 cannot read an RF 7.5 `output.xml` containing test metadata (affects `robotcode results`); a note in the variable-not-found patch that RF 7.5 fixed the finder-miss path but the patch still pays off.
- **Debugger and CLI tools**: verified end to end against RF 7.5 and compared with RF 7.4 — the DAP debugger, `robot-debug`, `repl`, `robot`, `rebot`, `libdoc`, `testdoc`, `discover`, `results`, `analyze code`, `config` and `profiles` need no code change (details in design.md); the change adds verification tasks so this is re-checked after the code changes. Exception-filter stops of the DAP debugger behave identically on RF 7.4 and 7.5 as well; the defects found on the way (the `failed_test` filter never stops, plain `filters` are ignored, hit-count breakpoints are inverted) exist on both versions and are handled in the separate change `debugger-dap-e2e-tests`. `robotcode testdoc` passes RF 7.5's Testdoc deprecation warning through. Breakpoints inside `.robot.md` suites do not hit (RF's block-relative line numbers, as for `.robot.rst` on every version); that belongs to `markdown-suites`.
- **Verified no-ops** (no code change): `TimeoutExceeded` becoming a `BaseException`, the console-logger and listener API refactors, tag-pattern deprecations (patterns are passed straight to RF), the Testdoc and Telnet deprecations, the deprecated `robot.utils` helpers, the `language:` config-line lexer change.

Not part of this change (each is its own follow-up): rendering per-argument/return/raises documentation, resolving Libdoc reference links and `%TOC%` in Markdown docs for hover and the REPL `.doc` view, and resolving type aliases of enums/TypedDicts to their type documentation (`rf75-argument-docs`), showing test metadata in discover, results and the test explorer (`rf75-test-metadata`), Markdown/reST code-block extraction and editor support (`markdown-suites`), `[rebot] console`/`quiet` in `robot.toml` (`rebot-console-options`), deprecation diagnostics for translated headers and tag-pattern spellings (`deprecation-diagnostics`).

## Capabilities

### New Capabilities

- `library-documentation-extraction`: What RobotCode extracts from library and resource keyword documentation — tags declared in documentation, privacy, unescaping, documentation formats, standard type documentation, type aliases and return types — and that it does so identically on every supported Robot Framework version and without mutating Robot Framework's objects.
- `robot-toml-option-coverage`: `robot.toml` accepts the console and libdoc option values that Robot Framework 7.5 accepts, and the generated model, JSON schema and configuration reference stay consistent with each other.
- `builtin-variable-catalog`: The set of built-in variables RobotCode treats as defined follows the Robot Framework version, including `${TEST_METADATA}` on 7.5.
- `markdown-resource-imports`: Resource imports of Markdown files are accepted on Robot Framework ≥ 7.5 in the same way reStructuredText resources are accepted today.
- `localized-section-headers-highlighting`: Syntax highlighting recognises every section header spelling Robot Framework accepts, including deprecated translations.

### Modified Capabilities

<!-- none — the existing specs cover the semantic model only -->

## Impact

- `hatch.toml`, `.github/workflows/build-test-package-publish.yml`: `rf75` matrix entries.
- `tests/robotcode/language_server/robotframework/parts/_regtest_outputs/rf75/` (new baselines, ~1530 files); `tests/robotcode/robot/test_robot_patching.py` (version-independent rewrite); new unit tests under `tests/robotcode/robot/diagnostics/` for documentation extraction, type aliases, return types, test-level `[Metadata]` and `${TEST_METADATA}`; new tests under `tests/robotcode/robot/config/` and `tests/robotcode/runner/cli/` for the `robot.toml` options.
- `packages/robot/src/robotcode/robot/diagnostics/library_doc.py`: documentation post-processing for RF ≥ 7.5, type-doc format, recursive-alias guard, return-type normalisation, Markdown resource extensions, clear error when Libdoc HTML is requested for a Markdown resource.
- `packages/robot/src/robotcode/robot/diagnostics/imports_manager.py`: Markdown resource extensions.
- `packages/robot/src/robotcode/robot/utils/variables.py`: `TEST_METADATA`.
- `packages/robot/src/robotcode/robot/utils/robot_patching.py`: docstring note only.
- `packages/robot/pyproject.toml`, `bundled_requirements.txt`: `markdown` dependency.
- `scripts/generate_rf_options.py` (alias emission, examples, `console` type, option placement), `packages/robot/src/robotcode/robot/config/model.py` (regenerated region), `docs/public/schemas/robot.toml.json`, `docs/03_reference/config.md`.
- `syntaxes/robotframework.tmLanguage.json`, `syntaxes/robotframework-repl.tmLanguage.json`: header regexes; `scripts/generate_tmlanguage.py`: deprecated terms (not run).
- Upstream: two Robot Framework issues to file (line numbers in Markdown/reST code blocks; doc-declared `robot:private` at runtime), see design.md Open Questions.
- `AGENTS.md`, `CONTRIBUTING.md`, `.github/copilot-instructions.md`, `.github/instructions/python-development.instructions.md`, `docs/03_reference/analyzing-results.md`.
- No change to the debugger, REPL, runner (`robot`, `rebot` pass-through), analyzer, VS Code or IntelliJ clients beyond the files listed.
- Related in-flight changes: none touch these files (`semantic-model-*` only exercise the existing hover/completion regtests, which stay green).
