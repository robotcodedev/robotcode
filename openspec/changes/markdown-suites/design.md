# Design: markdown-suites

## Context

See proposal.md. Verified facts:

- **RF extraction.** `MarkdownParser._read_markdown_data` (RF 7.5 `running/builder/parsers.py`) opens a block on `\s*(`{3,}|~{3,})\s*(\S+)` when the info word is `robotframework`/`robot` (case-insensitive, further words ignored), closes on a fence of the same character and at least the same length, keeps an unclosed trailing block, dedents each block with `textwrap.dedent` and joins blocks with one empty line; fences inside other-language fences still open blocks. `read_rest_data` (now `running/builder/restreader.py`) replaces the docutils `code`/`code-block`/`sourcecode` directives by a collector that keeps blocks whose arguments contain `robotframework`, joins all lines without separators, and needs docutils (`DataError` otherwise); docutils exposes `content_offset` and the content lines per directive. RF reports block-relative line numbers (verified: file line 14 → `lineno` 5), and RF's lexer does not recognise indented section headers, so per-block dedent is semantically required. Suite extensions default to `.robot`, `.rbt`, `.robot.rst`, `.robot.md`; `--extension md` or explicit paths add plain `.md`; `ResourceFileBuilder` picks the Markdown/reST parser by single suffix; `__init__.md` is an init file, `__init__.robot.md` is not (stem rule). Token positions are mutable, and statement/block positions derive from tokens, so shifting token columns before building the model yields file-accurate positions everywhere.
- **RobotCode today.** `document_cache_helper.get_document_type` matches the single suffix; tokens are produced from `document.text()`; `get_tokens` raises for unknown types while models/namespaces silently fall back to the suite path; `imports_manager` loads `.rst` resources as raw text (false `ResourceEmpty`); the language server gates about forty handlers on the client-sent language id and detects ids from the single suffix; the LS file watcher and workspace preload, `analyze code`'s workspace scan and `discover files` know only `.robot`/`.resource`; `discover` already lists `.robot.md` tests (RF's default extensions) with RF's block-relative numbers and serves unsaved editor content to RF's parsers through the `FileReader` patch; the debugger stores breakpoints by editor line and compares them with RF's listener line numbers; formatting, EOF quick fixes, refactors and Robocop operate on the whole document text; docutils is an optional extra (`rest`), present in hatch envs but not in the bundled extension.
- **VS Code.** The client's document selector is language-based (`robotframework`), with `supportedLanguages`/`fileExtensions` extensible by other extensions; test explorer watchers, stdin discovery, refresh and run/debug enablement gate on language id or `fileExtensions`; the `robotframework-injection` grammar already highlights `robot`/`robotframework` fences in Markdown; run selection uses long names, so running `.robot.md` tests works today; run-time markers map RF line numbers 1:1.
- **IntelliJ.** File types for `robot`/`resource` bound to `robotframework`; LSP4IJ language mapping by language; `RobotCodeTestManager` gates refreshes on the suite file type and streams open files to `discover --read-from-stdin`; gutter items use discover ranges. LSP4IJ supports `fileNamePatternMapping`.
- **Tests.** No `.md`/`.rst` fixtures exist; LS regression tests read annotated data files of any extension and open them with language id `robotframework`; discover/analyze acceptance suites and `test_document_cache_helper.py` provide the patterns.

## Goals / Non-Goals

**Goals:**
- Full editor support for embedded suites and resources with exact positions, matching RF's parsing.
- One extraction implementation for the language server, `analyze` and `discover`, with a parity test against RF.
- Hosts keep their Markdown/reST tooling.

**Non-Goals:**
- Debugger breakpoint/frame mapping for embedded suites (`embedded-suites-debugging`).
- Treating every `.md`/`.rst` in a workspace as Robot data.
- Virtual-document/request-forwarding architecture in the clients.
- Bundling docutils with the editor extensions (RF users running reST need it anyway; a clear diagnostic covers the rest).
- Block-aware formatting and EOF-appending quick fixes inside embedded documents (later, on top of the block table this change exposes).

## Decisions

### D1: File-accurate extraction in a shared helper, dedent mirrored with a margin table

`packages/robot/src/robotcode/robot/utils/embedded_code.py` reimplements RF's Markdown fence rules (tiny regexes, parity-tested) and runs docutils with RF's directive replacement but a recording code-block directive (using `content_offset` and the content lines; blocks from included files ignored) for reST. It returns (1) the file-geometry text — non-code lines blanked, code lines dedented per block like `textwrap.dedent` — with a per-line margin width, (2) RF's concatenated text for parity tests, and (3) the extracted-line → file-line table. Not dedenting was rejected: RF's lexer treats indented headers as comments, so the LS would diverge from execution. Version constants at module scope: Markdown only on RF ≥ 7.5; one `REMAP_RF_LINE_NUMBERS` switch for the discover remap so an upstream fix flips one constant.

### D2: Document typing by suffix chain; tokens from the extracted text

`__get_document_type` matches compound suffixes (`.robot.md`, `.robot.rst` → suite; `.md`/`.markdown`/`.rst`/`.rest` → resource; `__init__.md`/`__init__.rst` → init, a RobotCode decision mirroring its unconditional `__init__.robot` rule, since RF only does so with a configured extension; `__init__.robot.md` → suite, which RF skips in directory runs as `_`-prefixed) with the RF-version rules; `get_tokens` no longer raises for these types; the three tokenisers read the helper's text and add the margin to `Token.col_offset` on dedented lines. The helper result is cached on the `TextDocument` next to the tokens and exposed for other parts (block table). `documents_manager.detect_language_id` and the LS `didOpen` prefer the extension-detected id when it is not unknown, so clients may keep sending `markdown`/`restructuredtext`. `LanguageDefinition` extensions and `file_extensions` gain the four extensions (watcher and workspace file operations; workspace preload and `analyze` scans still use suite-only patterns, so a plain `README.md` is neither preloaded nor analysed — asserted by tests). The extension constants (`REST_EXTENSIONS`, `MARKDOWN_EXTENSIONS`) move into the new `embedded_code.py`, which neither `library_doc` nor `imports_manager` depends on; both import from there and `imports_manager`'s unused copy is deleted (`library_doc` cannot import from `imports_manager`: that would be circular).

### D3: Withhold whole-document edits

Formatting returns nothing for embedded documents; EOF-appending quick fixes and text-based refactors are disabled for them; Robocop gets the extracted text. Destroying prose is worse than a missing feature; the block table allows block-aware insertion later.

### D4: VS Code by pattern selectors, host language kept

A setting `robotcode.embeddedFilePatterns` (default `["**/*.robot.md", "**/*.robot.rst"]`) feeds additional `{scheme, pattern}` document selectors; `fileExtensions` gains `robot.md`/`robot.rst` for the existing globs; language-id gates in the language client, test controller, debug manager, tools manager and keywords tree become "language id in supported languages OR path matches a pattern"; enablement/when clauses use a filename regex; activation events add the two extensions. Registering `.robot.md` as `robotframework` was rejected (loses Markdown editing, rejected already in `support-rf75`); virtual documents were rejected on effort and because server-side resource loading, diagnostics and workspace edits cannot be forwarded cleanly.

### D5: discover remaps, IntelliJ maps by pattern

`Collector.visit_test`/`visit_suite` translate RF's block-relative `lineno` through the helper's table (reading the file via `FileReader` so stdin content is honoured) into file lines for `lineno`, `range` and ids, consistently for all consumers; `discover files` and `analyze code`'s scans include `*.robot.rst` and, on RF ≥ 7.5, `*.robot.md`; explicit Markdown/reST paths are analysed. IntelliJ adds `<fileNamePatternMapping patterns="*.robot.md;*.robot.rst" serverId="RobotCode" languageId="robotframework"/>` and pattern checks next to the file-type gates.

### D6: Tests

Extraction unit tests (fence variants, indented fences, unclosed blocks, non-robot fences, CRLF/BOM/tabs written with `write_bytes` so Windows does not translate line endings, empty file) plus parity tests against `MarkdownParser._read_markdown_data` (RF ≥ 7.5) and `read_rest_data` (docutils); `test_document_cache_helper.py` typing and position tests; namespace tests for Markdown/reST resource imports and for the missing-docutils diagnostic (docutils is installed in every hatch env, so absence is simulated with `monkeypatch.setitem(sys.modules, "docutils", None)`, which requires the helper to import docutils lazily inside the reST function, as RF's `RestParser` does); LS regression data files `embedded_markdown.robot.md` (baselines only under `rf75/`) and `embedded_rest.robot.rst` (baselines recorded in every `_regtest_outputs/rf*/` directory with `test-reset` per matrix env, skipped without docutils) using non-indented fences because the marker-line parser expects markers at column 0, while the indented-fence position assertion lives in the unit test; formatting returns nothing; discover acceptance tests for line remapping (file and stdin) and `files`; analyze tests for workspace scan and explicit paths; manual checklist for VS Code and IntelliJ. All fixtures via `tmp_path` or committed data files without CRLF.

## Risks / Trade-offs

- [Drift from RF's extraction] → parity tests on RF ≥ 7.5 and with docutils.
- [Upstream fix of line numbers double-shifts the remap] → single version-gated constant; the LS never uses RF's numbers.
- [docutils absent in bundled extensions] → one diagnostic; documented.
- [Markdown linters flag Robot syntax inside fences] → not RobotCode's concern; documented.
- [Watcher noise from `**/*.{md,rst}`] → start with the simple extension list; narrow to patterns plus per-resource watchers if reported.
- [Same basename with both embedded extensions] → RF's own "multiple suites with name" warning; documented.
- [Debugger still block-relative] → known limitation until `embedded-suites-debugging`.
- [Semantic tokens overlay Markdown highlighting] → only code lines receive tokens.

## Migration Plan

Additive. Users with `robot --extension md` projects add the pattern to `robotcode.embeddedFilePatterns` (and `parse-include`/`extensions` in `robot.toml` already drive `discover`). Rollback: revert; no data format changes.

## Open Questions

- Whether `robotcode.embeddedFilePatterns` should also accept resource-only patterns (e.g. `docs/**/*.md`) — decidable when the setting is implemented; the server treats any pattern-opened Markdown file by its suffix rules.
