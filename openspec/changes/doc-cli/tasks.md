# Tasks: doc-cli

## 1. Prerequisite

- [x] 1.1 Confirm that `library-loading-robustness` is applied: `LibraryDoc.loaded_without_arguments` exists, and `get_library_doc` sets it when the library could only be loaded without the given arguments. Verify with `hatch run test:test -- tests/robotcode/robot/diagnostics/test_library_loading.py`.

## 2. Shared rendering fixes (robotcode-robot)

- [x] 2.1 In `packages/robot/src/robotcode/robot/utils/markdownformatter.py`, let `TableFormatter._format_cell` escape the `|` left in a cell after its inline formatting, and let `LinkFormatter` write link targets with `#` instead of `\#`; link texts and other text stay as they are (design, Context). Verify with a new `tests/robotcode/robot/utils/test_markdownformatter.py`, run on every RF version:
  - `| x | (Foo|Bar) |` keeps two cells;
  - a `[http://example.com|text]` link inside a cell stays a link;
  - `[http://example.com/x.html#frag|docs]` becomes `[docs](http://example.com/x.html#frag)`;
  - a bare URL with `#` keeps `#` in its target;
  - `#` in plain text stays `\#`.

  Also add tests to `tests/robotcode/robot/diagnostics/test_library_doc_rendering.py`, gated `RF_VERSION < (7, 5)`: the `Should Match Regexp` hover row with `(Foo|Bar)` has as many unescaped `|` as the header row of its table, and the BuiltIn import hover contains `(http://docs.python.org/library/functions.html#eval)`.
- [x] 2.2 In `get_library_doc_from_library` (`packages/robot/src/robotcode/robot/diagnostics/library_doc.py`), store `lib.scope.name` on RF ≥ 7.0 and `str(lib.scope)` below, bound once at import time. Remove `_without_version_specifics` from `test_library_doc_rendering.py`. Verify with a test on every RF environment that `get_library_doc("Collections").scope == "GLOBAL"` and that the `Collections` import hover shows `GLOBAL`, and with `hatch run test:test -- tests/robotcode/robot tests/robotcode/language_server`.
- [x] 2.3 In `packages/robot/src/robotcode/robot/utils/markdown_docs.py`, make `slugify` follow github-slugger's rule, and add `heading_anchors(markdown)`, which numbers repeated slugs (design D5). Let `LibraryDoc._create_toc` and `_link_inline_links` call `slugify`, and let `_link_inline_links` write `(#slug)`. Verify in `tests/robotcode/robot/utils/test_markdown_docs.py`:
  - `Should Be Equal` gives `should-be-equal`, `` `TODAY` and `NOW` `` gives `today-and-now`, `Open ${browser} Browser` gives `open-browser-browser`, `Größe prüfen` gives `größe-prüfen`, `a  b` gives `a--b` and `Evaluate (Python)` gives `evaluate-python`;
  - `Library *BuiltIn*` gives `library-builtin` (the existing expectation changes);
  - two `Get Length` headings give `get-length` and `get-length-1`, and headings inside fenced code are ignored.

  In `test_library_doc_rendering.py`, update `ROBOT_FORMAT_LIBRARY_MARKDOWN` (`[Second section](#second-section)`), and check that the DateTime import hover links `` `TODAY` and `NOW` `` to `#today-and-now` (gated `RF_VERSION >= (7, 5)`), and that the BuiltIn import hover contains `[str](#str)` and no link target with `\#` (gated `RF_VERSION < (7, 5)`).
- [x] 2.4 Build the anchor map of `packages/repl/src/robotcode/repl/_pt/doc_viewer.py` (`_build_anchor_to_line_map`) from `heading_anchors`. Verify in `tests/robotcode/repl/test_doc_viewer.py`: the expectation of `test_build_anchor_to_line_map_strips_emphasis_for_matching` becomes `library-builtin`; two headings with the same text map to `x` and `x-1` on their own lines; a heading with a code span (`` Open `${browser}` Browser ``) is found.
- [x] 2.5 Add `code_span_variables(markdown)` to `markdown_docs.py`: scalar variables in text become inline code, found with Robot's `search_variable`; fenced and indented code blocks, HTML blocks, code spans and link targets are skipped, and an escaped `\${x}` is left alone (design D4). Verify in `test_markdown_docs.py` on every RF version:
  - `Use ${x} and ${y}.` becomes ``Use `${x}` and `${y}`.``;
  - `${x}[0]` and `${a${b}}` stay whole;
  - `` `${x}` ``, a fenced block with `${x}`, an indented code block with `${x}`, an HTML block `<div>${x}</div>`, `[t](http://h/${x})`, `\${x}` and `@{list}` stay unchanged.

## 3. The full page (robotcode-robot)

- [x] 3.1 Change the structure in the `only_doc=False` branch of `LibraryDoc.to_markdown` and in `_get_doc_for_keywords` (design D4):
  - heading levels through `header_level + 2` for keywords and the initializer, and `header_level + 1` for types;
  - the introduction shifted after its table of contents; keyword documentation shifted through `modify_doc_handler`;
  - no initializer before the title;
  - keywords and types sorted by `name.lower()`, private keywords skipped;
  - `\n\n---\n\n` separators;
  - `## Data types` and its table-of-contents entry.

  Let the REPL's `.doc` (`packages/repl/src/robotcode/repl/console_interpreter.py`) pass `header_level=0`, and correct the docstring of `anchor_link_resolver`, which says that types have no heading (design D4). Verify with a new `tests/robotcode/robot/diagnostics/test_library_doc_page.py`, using fixtures written to `tmp_path` with unique module names. On every RF version, a Robot-format library has an introduction section `= Section =`, an initializer `__init__(self, mode="a")` with a docstring, keywords `Zeta Kw` and `Alpha Kw`, a keyword documentation with `= Heading =`, and a keyword tagged `robot:private`. Check on it:
  - the heading levels of the requirement "Page structure";
  - `Importing` between `Introduction` and `Keywords`, and not before the title;
  - the order, and the private keyword absent on RF ≥ 6.0;
  - no `---` line directly after a line of text.

  On RF ≥ 6.1, an `Enum` fixture gets `Color (Enum)` with its members under `Data types`. For the standard libraries check:
  - `Collections` on RF 7.5 has exactly the level-2 headings `Introduction`, `Keywords` and `Data types`;
  - `Collections` on RF 6.1 has `Related keywords in BuiltIn` at level 3;
  - on every RF version, the first three keywords of `Collections` are `Append To List`, `Combine Lists` and `Convert To Dictionary`;
  - `BuiltIn` on RF 7.5 has no `---` line after text and a table of contents with `Data types` after `Keywords`;
  - two `sys.executable` subprocesses with `PYTHONHASHSEED` 1 and 2 render identical `Collections` pages.
- [x] 3.2 Add the keyword index at the start of `## Keywords`, filled from `heading_anchors`, and the final `code_span_variables` pass for documentation that is not HTML or reStructuredText (design D4). Verify in `test_library_doc_page.py` on every RF version, with pages rendered as in design D4 (`header_level=0`, `anchor_link_resolver`). A resource fixture has a `Documentation` setting, `Zeta Kw` defined before `Alpha Kw`, a keyword tagged `robot:private`, `Open ${browser} Browser`, `Set ${a} To ${b}` and a keyword documentation `Use ${x} and ${y}.`. Check on it:
  - the title is `Resource *<name>*`, and the only level-2 sections are `Introduction` and `Keywords`;
  - `Alpha Kw` comes before `Zeta Kw`;
  - on RF ≥ 6.0, the private keyword is neither a heading nor an index entry;
  - the index links equal the anchors of the keyword headings;
  - the variables are inline code in the text, the headings and the index;
  - the anchor of `Open ${browser} Browser` is `open-browser-browser`.

  Also check that in `BuiltIn` and `Collections` on RF 6.1 and 7.5, every link target that starts with `#` is an anchor from `heading_anchors`, and that the table of contents of the `DateTime` page on RF 7.5 links `` `TODAY` and `NOW` `` to `#today-and-now`.
- [x] 3.3 Link names and references in documentation text (design D4).
  - Let `get_reference_targets()` also return the `= … =` headings of a Robot-format introduction as sections, found with Robot Framework's `HeaderFormatter` and added last.
  - In the `only_doc=False` branch, stop calling `_link_inline_links`, and pass `get_reference_targets()` to the keyword entries for Robot-format documentation too.
  - Render a page with data types twice, and take the anchors of the level-3 headings under `## Data types` from `heading_anchors` after the first rendering. Give them to the second rendering through a resolver that returns them for types and asks the given resolver for everything else.
  - In the Robot-format conversion of the introduction, of keyword documentation in `KeywordDoc.to_markdown` (task 4.2 moves it into `format_text`) and of `_format_doc_fragment`, write each name in single backticks that has one of these targets, and for which the resolver returns an anchor, as the link `[<anchor>|<name>]` before `MarkDownFormatter` runs; headings and preformatted text keep the name.

  Verify in `test_library_doc_page.py`, with pages rendered as in design D4. On every RF version, the documentation of `Zeta Kw` in the Robot-format library of task 3.1 also names `` `Alpha Kw` `` and `` `Section` ``. Check:
  - the page links them as `[Alpha Kw](#alpha-kw)` and `[Section](#section)`;
  - `KeywordDoc.to_markdown(link_resolver=anchor_link_resolver)` of `Zeta Kw`, called with a resolver as the REPL's `.kw` calls it, keeps both as inline code;
  - on RF 6.1 and 7.4, where `BuiltIn` and `XML` are documented in Robot Framework's format, no line of an `Arguments:` part of their pages contains a link; today the argument names `repr`, `text`, `tail` and `tag` and the argument type or default `str` link to sections of the introduction (design, Context);
  - on RF 6.1 and 7.4, `BuiltIn` shows `` `str` (default), `repr`, and `ascii` `` and `XML` shows `` Similarly as with `text`, also `tail` `` without links, while `` `Should Be Equal` `` and `` `Evaluating expressions` `` in `BuiltIn` link to `#should-be-equal` and `#evaluating-expressions`, and `` `introduction` `` in `XML` links to `#introduction`.

  Gated `RF_VERSION >= (6, 1)`, the fixture is a library with `paint(self, shade: Color, color: str = "red") -> Color` and an `Enum` `Color`, once documented in Markdown with ``Paints `color` in [Color].`` and once in Robot Framework's format with ``` Paints ``color`` in `Color`. ```. Check:
  - both pages link the reference as `[Color](#color-enum)`, and `color-enum` is the anchor of the heading `Color (Enum)`;
  - on both pages, this reference is the only link to `#color-enum`: the argument name `color`, the argument type and, on RF ≥ 7.0, the return type of `Paint`, and the code `color` stay inline code;
  - with an added keyword `Color Enum` in both libraries, the keyword's heading has the anchor `color-enum`, the type's heading `color-enum-1`, and both pages link the reference to `#color-enum-1`;
  - the hover of `Paint` (`KeywordDoc.to_markdown()`) still shows `` `Color` ``;
  - on RF 7.4, where `XML` is documented in Robot Framework's format, no link of its page points to the heading of the type `Source`, although 37 argument rows name the argument `source` and its documentation writes ``` ``source`` ```;
  - on RF 7.5, the `OperatingSystem` page links the `[Secret]` references of its argument descriptions to `#secret-standard`, and its argument types stay `` `str` | `Secret` ``.
- [x] 3.4 Update the tests that show the full page or the REPL's `.doc` call:
  - `tests/robotcode/language_server/robotframework/parts/test_http_server_markdown.py`: keyword headings at level 3 and the introduction heading `### A section`;
  - the `only_doc=False` assertions of `test_library_doc_rendering.py`;
  - the `.doc` spy in `tests/robotcode/repl/test_dot_commands.py`: `header=0`.

  Verify that `hatch run test:test -- tests/robotcode/robot tests/robotcode/repl tests/robotcode/language_server` passes, and that the keyword goldens `ROBOT_FORMAT_KEYWORD_MARKDOWN` and `MARKDOWN_KEYWORD_MARKDOWN` and `test_builtin_log_shows_argument_descriptions` pass unchanged.

## 4. The command (robotcode-repl)

- [x] 4.1 Create `packages/repl/src/robotcode/repl/doc_cli.py` with the group `doc`, the command `lib`, the shared options, `--language` and `-o`, and register it in `packages/repl/src/robotcode/repl/hooks.py` (design D1). Move `-v`, `-V` and `-P` of `SHELL_OPTIONS` in `packages/repl/src/robotcode/repl/cli.py` into the shared list.
  - Load the target as in design D2: the configuration chain of `run_repl` inside `app.save_syspath()`, with `--language` passed like `-v`, `-V` and `-P` after the configuration's options, `GlobalVariables(settings).as_dict()`, `::` splitting, a library name that exists as a path made absolute first (Libdoc's `_normalize_library_path`), and libraries through `get_library_doc`. Files go through `find_file` and `ResourceFileBuilder`, or through `TestSuiteBuilder` when that raises (the suite's name, the type `SUITE`, the resource builder's error when both fail). Suite initialization files go straight to `TestSuiteBuilder` with `allow_empty_suite=True`. When the built suite's name equals the name derived from the file (`Init`, or `INIT` for `__INIT__.robot`), it is replaced by the name derived from the directory, with `format_name` below RF 6.1 and `TestSuite.name_from_source` from RF 6.1; a name from a `Name` setting is kept. On RF ≥ 6.0 both builders get `lang=settings.languages`.
  - Apply the abort rules of D3, render the page as `to_markdown(only_doc=False, header_level=0, link_resolver=anchor_link_resolver)` (design D4), and write it with `app.echo_as_markdown` or to the `-o` file.

  Verify with a new `tests/robotcode/repl/test_doc_cli.py`: in-process `CliRunner` on the root `robotcode` group with `--no-color --no-pager`, and a `tmp_path` project with `robot.toml` (`python-path`, `[variables]`, a profile with variables, `[env]`), entered with `monkeypatch.chdir`, with `os.environ` restored by `monkeypatch` and unique library module names. It covers the scenarios that run `doc lib`:
  - of "Subcommands and targets": "Library by name", "Directory as target", "Resource file", and "Suite file" without its JSON part, with a Test Cases file and a Tasks file on every RF version, and "Suite initialization file" without its standard error part (task 4.6), on every RF version and also for `Mysuite/__init__.robot`, whose page has the title `Suite *Mysuite*`, and for `lower_dir/__INIT__.robot`, whose page has the title `Suite *Lower Dir*`; gated `RF_VERSION >= (6, 1)`, an initialization file with `Name    Custom Name` gets the title `Suite *Custom Name*`;
  - of "Targets resolve with the project configuration": "Relative path from a subdirectory";
  - of "Failing loads abort": "Unknown library", "Import arguments that fail", "Missing resource file" and "Resource file with unrecognised section headers" (gated `RF_VERSION >= (6, 1)`; the German file is written with `encoding="utf-8"`, so the test also passes on Windows).

  It also checks that `${CURDIR}` in an import argument follows `--base-dir`, that `doc lib BuiltIn` on RF 7.5 contains `[Set Log Level](#set-log-level)` (scenario "Keyword reference in a full-document view"), and these points of the requirement "Markdown output":
  - the piped page;
  - an `-o` file whose bytes contain no `\r\n`;
  - `-o` given in a subdirectory writes there;
  - `-o` with `--format json` exits with 2.

  Run `tests/robotcode/repl/test_cli.py` as well, for the moved options.
- [x] 4.2 Add the JSON output of `lib` (design D6: `LibraryDocumentation`, `KeywordSelection`, `KeywordEntry`, `TypeEntry`, fields without defaults and never `None`, `app.print_data`). Add the public `KeywordDoc.format_text(text)` in `library_doc.py`, which `KeywordDoc.to_markdown` then uses for the documentation, and take the anchors from `heading_anchors`. Verify in `test_doc_cli.py`:
  - the scenario "Library as JSON";
  - on every RF version, all fields are present, `markdown` is the Markdown output, and every `anchor` is an anchor of `markdown`;
  - `type` is `LIBRARY` for `Collections`, `RESOURCE` for a resource file and `SUITE` for the files of the scenarios "Suite file" and "Suite initialization file";
  - for the Markdown library of task 3.3 with the keyword `Color Enum`, the `anchor` of the `Color` type entry is `color-enum-1`, the target of the `[Color]` link in `markdown` (gated `RF_VERSION >= (6, 1)`);
  - `args` contains no zero-width joiner, and `short_doc` is one line;
  - for a library documented in reStructuredText whose keyword documentation contains ``` ``value`` ```, neither `doc` nor `short_doc` contains double backticks (skipped without `docutils`).
- [x] 4.3 Add `keywords` (design D6 and D7: patterns, `--tag`, one line per keyword, `_(no keyword matches)_`, and the `KeywordSelection` JSON). Verify in `test_doc_cli.py` with every scenario of the requirement "Keyword overview", and with the scenarios that run `doc keywords`:
  - of "Subcommands and targets": "Markdown resource file" (gated `RF_VERSION >= (7, 5)`) and "Import arguments";
  - of "Targets resolve with the project configuration": "Python path from the configuration", "Variable from a profile", "Variable on the command line", "Translated resource file" and "Language on the command line" ("Library changed between two calls" follows in 4.6). The last two are gated `RF_VERSION >= (6, 0)`. "Translated resource file" runs with the German file of task 4.1 in a second `tmp_path` project whose `robot.toml` sets `languages = ["de"]`. In that project, a suite file with `*** Testfälle ***` and `*** Schlüsselwörter ***`, also written with `encoding="utf-8"`, has its keyword listed by `doc keywords` and the `type` `SUITE` in the output of `--format json doc lib`. "Language on the command line" runs in the first project, and its second part in the second one. On RF 5.0 (gated `RF_VERSION < (6, 0)`), `doc keywords --language de deutsch.resource` in the first project writes nothing to standard output, reports `option --language not recognized` and exits with 1;
  - of "Failing loads abort": "One keyword cannot be created".

  Also check that `--tag` and a pattern together select only keywords that match both, and that `--format json` with a pattern holds only the matching keyword entries.
- [x] 4.4 Add `keyword` (design D6 and D7: exact names, patterns and embedded arguments; the hover rendering followed by the argument types; `RecommendationFinder` on standard error and exit 1; the `KeywordSelection` JSON). Verify in `test_doc_cli.py` with every scenario of the requirement "Keyword documentation", the data type scenario gated `RF_VERSION >= (6, 1)`, and with the scenario "Selected keyword as JSON". Also verify the scenario "Type reference in a full-document view" of `keyword-documentation-rendering` (gated `RF_VERSION >= (7, 5)`), and check that `robotcode doc keyword Collections "Get Match Cont" "Get Match Count"` prints `Get Match Count` and exits with 1.
- [x] 4.5 Add `browse` (design D8). Verify in `test_doc_cli.py`, patching `_is_interactive_stdin`, `is_running_in_ai_agent` and the check of standard output as `robotcode.repl.doc_cli.<name>`, and `DocViewer.run`:
  - an interactive terminal starts the viewer with the page;
  - an AI-agent session and a pipe print the page instead;
  - a failing load exits with 1 without starting the viewer.

  In `test_doc_viewer.py`, following the `#get-match-count` link of the `Collections` page jumps to that heading, and going back returns. Also run `robotcode doc browse Collections` once in a terminal, follow a link and go back.
- [x] 4.6 Verify live generation and the entry point with `sys.executable -m robotcode.cli` subprocesses in `test_doc_cli.py`: after a keyword is added to `lib/MyLib.py`, the second `doc keywords MyLib` lists it; `doc lib Collections` exits with 0 and prints `# Library *Collections*`; and `doc lib 01__my_suite/__init__.robot` for the initialization file of task 4.1 writes nothing to standard error, on every RF version (the rest of the scenario "Suite initialization file").

## 5. Documentation and agent skill

- [x] 5.1 Write `docs/03_reference/browsing-documentation.md` ("Browsing Library Documentation", in the style of `discovering-tests.md`), covering:
  - installation from the `repl` package;
  - the four subcommands and their targets (libraries, resource files, suite files and suite initialization files), with `::` arguments and the variable recipe for arguments containing `::`;
  - configuration, with `languages` and `--language` for translated resource and suite files (not on RF 5.0), `--base-dir` and live generation;
  - Markdown, `-o` and JSON output, with the JSON fields;
  - patterns, `--tag` and names;
  - the abort rules and exit codes;
  - the limit of libraries that need a running execution context, with the REPL's `.doc` as the alternative.

  Then:
  - add the page to `docs/03_reference/index.md`, to the package overview of `docs/03_reference/cli.md`, and to the page map of `docs-next/scripts/convert.mjs` (`guides/browsing-documentation`, label "Browsing Documentation", order 60, a one-sentence description);
  - update the `.doc` row of `docs/03_reference/repl.md` (keyword index, data types, private keywords left out) and the lookup sentence of `docs/03_reference/ai-agents.md:96`;
  - regenerate the command reference with `hatch run create-cmd-line-docs` on the newest supported Robot Framework, keeping only the hunks of the new commands.

  Verify with `npm run docs:build` and `npm run docs-next:build`.
- [x] 5.2 In /home/daniel/develop/robot/robotframework-agent-plugins, switch the `robotcode` skill's lookups from `robotcode libdoc … list/show` to `robotcode doc keywords <Lib> [PATTERN]` and `robotcode doc keyword <Lib> "<Keyword>"`:
  - `plugins/robotcode/skills/robotcode/SKILL.md` lines 26, 44, 56-66, 109, 162, 184-192 and 278: the introduction, the mode list, "Documentation lookup priority", `doc` in the list of commands that honour `-p` (109), "preferring `robotcode doc`" (162), "Library & keyword information" and the documentation gotcha;
  - `references/authoring.md`, `repl.md` and `workflows.md`;
  - `references/install.md`, with `doc` provided by the `repl` package.

  Then run `hatch run build:sync-chat-plugin` in this repository. Verify with `hatch run build:sync-chat-plugin --check`, and by running every lookup recipe of the skill against a project on RF 7.5.

## 6. Review corrections (2026-09-30)

- [x] 6.1 Link names in Robot-format documentation inside `MarkDownFormatter` (a name linker in its line formatter, placeholders, escaped link texts), per paragraph, list item and table cell; remove the pre-pass that wrote Robot links (design D4). Verify in `tests/robotcode/robot/utils/test_markdownformatter.py` (brackets before a name, a name across lines, escaping, lists and tables, headings and preformatted text, no linker) and in `test_library_doc_page.py` with `Remove Tags` and `Set Test Variable` of `BuiltIn` before RF 7.5.
- [x] 6.2 Resolve links within the page to the heading whose title is the name, with the introduction's headings first; match the index and the JSON anchors by title; escape the index's link texts (design D4, D5). Verify in `test_library_doc_page.py`: `Get-Value` links to `#get-value-1`, `Get [x] Item` is escaped, an HTML heading does not shift the index, and every `#` link of the standard-library pages resolves.
- [x] 6.3 Shift the headings of data-type documentation and of plain text on the page, by `header_level` (design D4). Verify in `test_library_doc_page.py`: a `= Usage =` or `# Usage` in a type's documentation becomes level 5 and both types keep their anchors; plain-text headings land on levels 3 and 5; `header_level=1` moves every heading by one.
- [x] 6.4 Rework `code_span_variables`: adjacent variables in one span, longer fences for backticks, and the block rules of design D4 (headings end blocks, list continuations, indented fences, CommonMark HTML blocks). Slugs from the rendered text of a heading (design D5). Verify in `tests/robotcode/robot/utils/test_markdown_docs.py`, with the cases checked against markdown-it, and with `Remove Files` of `OperatingSystem` before RF 7.5.
- [x] 6.5 Fix the loading of `robotcode doc` (design D2, D3, D6): no output files or directories; variable-file output on standard error; variables in the target resolved before the kind is decided, backslashes kept as text; Robot Framework's resource extensions; no import arguments for files; empty targets as a usage error; `-V`/`-P` relative to the start directory; the dry run; abort for libraries with errors and no keywords and for the Python easter egg; Robot Framework's messages collected and reported once as errors or warnings; `-o` creating its directory. Verify each in `tests/robotcode/repl/test_doc_cli.py` (`TestLoadingDetails`), and run the subprocess tests with `PYTHONUTF8=1` and without the user-level `robot.toml`.
- [x] 6.6 Update `docs/03_reference/browsing-documentation.md`, the skill and the evals in /home/daniel/develop/robot/robotframework-agent-plugins (case 05 and its READMEs), and re-sync `chat-plugins` with `hatch run build:sync-chat-plugin --force`. Verify with `npm run docs:build`, `npm run docs-next:build` and `hatch run build:sync-chat-plugin --check`.

## 7. Verification

- [ ] 7.1 Run `hatch run lint:all` and `hatch run test:test` (RF 5.0–7.5) and confirm that both pass. Regression baselines may change only where the converter corrections, the scope name or the anchor rule predict it. Confirm that the CI matrix on Linux, Windows and macOS is green.
- [ ] 7.2 Manually open the output of `robotcode doc lib -o builtin.md BuiltIn` and of `robotcode doc lib -o os.md OperatingSystem` on RF 7.5 in GitHub's Markdown preview and in VS Code's Markdown preview, with the built-in math support on. Confirm that no variable is shown as a formula, and that the table of contents, the keyword index and the reference links jump to their headings, including the `[Secret]` links of `OperatingSystem` to its data type.
