# REPL and Notebooks in VS Code

This document describes how RobotCode gets a native Robot Framework REPL and notebooks in VS Code, and the
execution layer they share with the command-line REPL (`robotcode repl`). It collects the decisions of 2026-10-25,
the platform facts they rest on and the questions that are still open. It will be cut into OpenSpec changes later.

## Goals

- **Native instead of terminal.** What `robotcode repl`, `robotcode robot-debug` and the VS Code debugger already do,
  available in VS Code's own UI:
  - a **REPL in the Interactive Window**: an input box at the bottom, the history with its output above;
  - **notebooks** (`.robotbook`) for experimenting and documenting, similar to Jupyter notebooks.
- **One session, two cell modes.** A cell or input is either Robot Framework data with sections (`*** Settings ***`
  up to `*** Test Cases ***`) or a REPL input that works like today's REPL. Both run in the same session.
- **A way into the REPL and back out.** Lines and tests of a `.robot` file go into the REPL with the file's imports,
  variables and keywords; lines that work go back into the test or keyword they belong to.
- **Standard channels only.** VS Code's notebook API for the UI and execution, LSP 3.17 notebook synchronization for
  language features, DAP for debugging cells.
- **One execution layer** in `packages/repl` for the command-line REPL, the native REPL and the notebook kernel.

## Non-goals for now

- **Jupyter.** No Jupyter kernel, no `.ipynb`, no output fallbacks for GitHub or JupyterLab. A Jupyter kernel can sit
  on the same execution layer later.
- **Running and debugging whole tests and suites.** That stays with the debugger (Test Explorer, Run/Debug, Debug
  Console); its documentation should cover the experimenting workflow better.

## Workflows

The requirements come from these issues:

- [#381](https://github.com/robotcodedev/robotcode/issues/381) (open, "Multiline interactive console"): build long UI
  or ERP tests line by line against a running application. Every line depends on the state the previous lines left,
  and is retried until it works. Wishes: a session that stays open, a shortcut that runs the current line or the
  selection as whole logical lines, run a whole test, reload keywords after editing, completion in the input, see
  console output, variable and return values.
- [#544](https://github.com/robotcodedev/robotcode/issues/544) (closed as a duplicate of #381): load resource files,
  own keywords and libraries into the REPL, completion, screenshots (SikuliLibrary) in the output.
- [#23](https://github.com/robotcodedev/robotcode/issues/23): try keywords at runtime while building a test.
- [#231](https://github.com/robotcodedev/robotcode/issues/231): RoboCon 2024 wish "Interactive Interpreter REPL".
- [#501](https://github.com/robotcodedev/robotcode/issues/501): documentation "How to work with notebooks".
- [#354](https://github.com/robotcodedev/robotcode/issues/354): a variables view.

The workflow the design is built around:

```
   editor (.robot)                          REPL (Interactive Window)
  +-----------------------+    way in      +-------------------------------+
  | Order Coffee          |  ------------> | session after "run to here"   |
  |   Open Shop As alice  |  Shift+Enter,  | [1] Get Text  css:.price      |
  |   Add To Cart coffee  |  run to here   | [2] Click  id:buy      FAIL   |
  | > Click  ...    <-----+-- cursor       | [3] Click  css:#buy    PASS   |
  |   ...                 |                |                               |
  +-----------------------+  <------------ +-------------------------------+
                               way back: insert cell [3] after the line
                               the session came from
```

## Decisions (2026-10-25)

| # | Topic | Decision | Section |
|---|---|---|---|
| 1 | Execution layer | A session is one Robot Framework suite: REPL inputs run in *driver tests*, test case cells are appended to the running suite as real tests. | [Session suite](#session-suite) |
| 2 | Cell mode | Decided by the cell language only: `robotframework` = Robot mode (sections, including Test Cases and Tasks), `robotframework-repl` = REPL mode, like today's REPL. A section in a REPL input is an error. | [Cell modes](#cell-modes) |
| 3 | Same keyword in two cells | The definition executed last wins. Duplicates within one cell are reported by Robot Framework itself. | [Keywords at runtime](#keywords-at-runtime) |
| 4 | Suite Setup | Runs every time its Settings cell is executed. | [Robot mode](#robot-mode-emulating-the-sections) |
| 5 | Settings cell executed again | The Suite Teardown of the previous execution runs first, then the new Suite Setup. | [Robot mode](#robot-mode-emulating-the-sections) |
| 6 | Variables of REPL inputs | Stay local, as in a test: test case cells don't see them; the REPL keeps them. | [REPL mode](#repl-mode) |
| 7 | Order the language server analyzes | Notebook: the order of the cells. REPL: the history, the input box last. | [Language server](#language-server) |
| 8 | Command-line REPL | Gets the new execution layer and the Robot mode in the first step. | [Cell modes](#cell-modes) |
| 9 | Robot mode in the command-line REPL | Through a dot command, `.robot`. | [Cell modes](#cell-modes) |
| 10 | "Run test to here" | Runs the test as a real test with its Test Setup, without its teardown. | [Way in](#way-in) |
| 11 | The cursor line in "run to here" | Runs too. | [Way in](#way-in) |
| 12 | Way back | Inserts after the line the session came from, with matching indentation. | [Way back](#way-back) |
| 13 | Target of "run selection" and "run to here" | Only the Interactive Window. The terminal REPL stays a separate tool. | [Way in](#way-in) |
| 14 | Shortcut | Shift+Enter by default, only in Robot Framework files. | [Way in](#way-in) |
| 15 | Notebook file format | `.robotbook` with a new format. Files in today's format are not read. | [Notebooks](#notebooks) |
| 16 | Notebook outputs | Saved, as readable JSON, without timings. | [Notebooks](#notebooks) |
| 17 | Dot commands | None in VS Code; native UI instead. The command-line REPL keeps them. | [Native UI](#native-ui-instead-of-dot-commands) |
| 18 | Order | Execution layer, native REPL, notebooks, language server, debugging; changed by decisions 19 and 20. | [Order](#order) |
| 19 | Language server support | Comes early: support for REPL documents right after the execution layer. | [REPL documents](#repl-documents) |
| 20 | Notebooks and notebook synchronization | Come in one step, so notebooks never ship without language features in their cells. | [Notebooks and the Interactive Window](#notebooks-and-the-interactive-window) |

## Starting point

### The notebook prototype (2024)

`vscode-client/extension/notebook.ts`, `vscode-client/rendererLog/` and `packages/repl_server/` (last functional
change 2024-12):

- a `.robotbook` serializer, a controller for the notebook type `robotframework-repl`, interrupt and restart, a
  renderer for the log tree (`x-application/robotframework-repl-log`);
- `robotcode repl-server` with its own interpreter (`repl_server/interpreter.py`) from 2024: every cell runs as the body
  of the one test of a synthetic suite, that is REPL semantics.

Gaps found on 2026-10-23, partly with a JSON-RPC client against `repl-server`:

- An input with a token error, such as `[Tags]`, produces no output at all; an empty cell fails with "Test cannot be
  empty."
- `Log To Console` goes to the "RobotCode REPL" output channel, not to the cell. The whole result arrives when the
  cell has finished.
- No return value, no `${_}`, no `Library  X` shorthand, no dot commands; the 2024 interpreter parses with
  `get_test_body_from_string`, not with `parse_input`.
- The interpreter reads attributes Robot Framework 7 deprecates on control structures (`name`, `doc`, `args`, `tags`,
  `timeout`), which fills the output channel with warnings.
- "Run All" can't be stopped: the interrupt handler only interrupts the running cell, and the loop goes on with the
  next one (from the code). Execution numbers count across all notebooks and don't restart with the kernel.
- The renderer shows arguments without separators, labels the timeout "Tags:" and shows the elapsed time twice.
- Outputs are stored base64-encoded, together with timings, so every run changes the file.
- Cells get no language features: the language client's document selector only covers `file` and `untitled`
  documents of the language `robotframework`.

### The command-line REPL

`packages/repl` has the pieces a native frontend can reuse:

- `BaseInterpreter.parse_input` (incomplete blocks, errors), the `Library  X` shorthand, `${_}`, `.save` with
  `_session_export.py`, and the dot commands of `ConsoleInterpreter`;
- `_pt/completion.py`, a completion service without a prompt_toolkit dependency that also completes in the scope of
  a paused frame;
- `_debug/controller.py`, the debug core of `robot-debug`, with a `Frontend` protocol (`wait_at_stop`, `on_output`,
  `on_continued`, `on_exited`).

The 2024 interpreter of `repl-server` uses none of them. The new execution layer replaces it.

### Throwaway prototype: a REPL in the Interactive Window

A git-ignored prototype in `playground/robot-interactive-repl/` (a plain JavaScript extension plus a helper library),
checked in the VS Code harness with the demo project and Robot Framework 7.5:

- a controller for the notebook type `interactive`, opened with `interactive.open`, running `repl-server`;
- Shift+Enter sends the selection or, without one, the statement under the cursor with its `...` lines, the whole
  block when the line opens one, or the body of a test without its settings when the cursor is on the test's name;
  the cursor moves to the next statement;
- before lines of a file run, a helper library loads the file's imports, Variables section and keywords from the
  editor's current content, only the parts that changed;
- input typed into the input box runs through VS Code's `interactive.execute`; the log renderer works in the
  Interactive Window.

It also showed that VS Code restores an Interactive Window with its history after the extension host restarts,
while the session behind it is gone, and then asks whether to save it when it is closed.

## Architecture

```
                VS Code                                           Python
 +---------------------------------------+               +-------------------------------+
 | Notebook editor (.robotbook)          |   execution   | Kernel: robotcode repl-server |
 | Interactive Window (REPL)             | ------------> |  on the new execution layer   |
 |  NotebookController, log renderer     |   JSON-RPC    |  (packages/repl)              |
 |                                       | <-- events -- |                               |
 |  Language client                      |   LSP 3.17    | Language server               |
 |   NotebookDocumentSyncFeature         | ------------> |  notebook model, virtual      |
 |                                       |  notebook*    |  Robot document per notebook  |
 |  Debug session ("Debug Cell",         |   DAP         | RobotCode debugger            |
 |   breakpoints in cells)               | ------------> |  in the kernel process        |
 +---------------------------------------+               +-------------------------------+

 Frontends of the execution layer:  command-line REPL (ConsoleInterpreter)
                                    native REPL (Interactive Window)
                                    notebook kernel
```

- **Execution:** a `NotebookController` per notebook type sends cells to the kernel. VS Code defines no kernel
  protocol; ours stays JSON-RPC.
- **Language features:** LSP 3.17 notebook synchronization, so the server knows which cells belong together.
- **Debugging:** a notebook kernel provides a debug adapter (VS Code's notebook guide); RobotCode's DAP debugger runs
  in the kernel process.

All three have to agree on one thing: under which Robot Framework source a cell runs. The kernel parses each cell
under its own source, keywords and tests carry it, the debugger reports frames and breakpoints with it, the language
server maps its positions back to the cell, and the extension maps the source to the cell's URI.

## Execution layer

### Session suite

Today the whole REPL runs inside one test ("RobotCode REPL") whose keyword never returns. Robot Framework can't run
real tests inside it: `VariableScopes` keeps a single slot for the running test (`start_test` sets `_test`,
`end_test` resets it to `None`), so a nested test breaks the scopes of the outer one.

The new layer makes the session a suite whose tests alternate between *driver tests* and real tests:

```
 session suite (one Robot Framework run, one namespace, one set of library instances)
  +-- REPL 1        driver test: REPL inputs run here, as today;
  |                  a cell with *** Test Cases *** appends its tests and "REPL 2",
  |                  then the driver returns
  +-- Cell Test 1   real test: Test Setup, body, teardown, status, tags
  +-- Cell Test 2   real test
  +-- REPL 2        next driver: the REPL goes on, with the variables of REPL 1
  ...
  Suite Teardown: set on the running suite, runs when the session ends
```

Why it works:

- `ItemList.__iter__` walks its items by index (`while index < len(self._items)`, Robot Framework 5.0 and 7.5), so
  `suite.tests.visit(...)` also runs tests appended while the suite runs.
- `SuiteVisitor.visit_suite` checks `suite.has_teardown` only after the tests, and `SuiteRunner.end_suite` runs the
  teardown of the data suite as it is then.
- The kernel builds the session suite itself (`TestSuite.from_model`), so it holds the running data suite.

Checked in a throwaway experiment (2026-10-25): a library keyword serves as the driver; it appends the tests of a
cell (`TestSuite.from_model(get_model(cell))`) and a new driver test to the running suite and returns.

| Result | RF 5.0 | RF 6.1 | RF 7.5 |
|---|---|---|---|
| Appended tests run as real tests, with PASS and FAIL; the next driver runs after them | yes | yes | yes |
| Keywords of the cell are found in its tests | yes | yes | yes |
| Suite variables set in the REPL are visible in the tests | yes | yes | yes |
| Local REPL variables are not visible in the tests, and can be carried into the next driver | yes | yes | yes |
| Test Setup of the cell's Settings runs (`output.xml`) | | | yes |
| A Suite Teardown set at runtime runs at the end (`output.xml`) | | | yes |

The cell model needs a source (`model.source`): on Robot Framework 5.0, building a `UserLibrary` from a resource
without one fails with a `TypeError`.

Carrying the REPL's variables: before a driver test ends, the kernel keeps its test-level variables and sets them
again at the start of the next driver (`Set Test Variable`). Test case cells never see them (decision 6).

### Cell modes

The language of a cell decides how it runs (decision 2):

| Language | Mode | Content |
|---|---|---|
| `robotframework` | Robot mode | sections: `*** Settings ***`, `*** Variables ***`, `*** Keywords ***`, `*** Test Cases ***`, `*** Tasks ***`, comments |
| `robotframework-repl` | REPL mode | statements without a section header, as in today's REPL; a section header is an error |

- In the Interactive Window the input box uses the first language of the controller's `supportedLanguages`, so REPL
  mode. A selection sent from an editor that contains sections becomes a `robotframework` cell; the extension picks
  the language when it inserts the cell.
- The command-line REPL has no cell language. `.robot` opens a multi-line input in Robot mode, finished with its own
  key (decision 9); files with sections given to `robotcode repl` run in Robot mode.
- The command-line REPL gets the new layer in the first step (decision 8). There, `*** Test Cases ***` then runs real
  tests, and the prompt goes on afterwards.

### Robot mode: emulating the sections

| Section or setting | What the session does | Checked |
|---|---|---|
| `Library`, `Resource`, `Variables` | imported into the session's namespace (`Namespace._handle_imports` with the imports of the parsed cell, so relative paths resolve against the cell's source); imports only add up, removing one needs a restart | prototype, RF 6.1 to 7.5 |
| `*** Variables ***` | set as suite variables, overwritten when the cell runs again (`set_from_variable_section`, `set_from_variable_table` up to RF 6.1) | prototype |
| `*** Keywords ***` | see [Keywords at runtime](#keywords-at-runtime) | experiment, RF 5.0 to 7.5 |
| `Test Setup`, `Test Teardown`, `Test Tags`, `Test Timeout`, `Test Template`, `Keyword Tags` | remembered; Robot Framework's builder applies them when it builds the tests of later test case cells | Test Setup, RF 7.5 |
| `Suite Setup` | runs at once, every time its Settings cell runs (decision 4) | |
| `Suite Teardown` | set on the running session suite, runs when the session ends; when the Settings cell runs again, the previous Suite Teardown runs first, then the new Suite Setup (decision 5) | runs at the end, RF 7.5 |
| `Documentation`, `Metadata` | set on the result suite, cosmetic | |
| `*** Test Cases ***`, `*** Tasks ***` | appended as real tests, see [Session suite](#session-suite) | experiment, RF 5.0 to 7.5 |

### Keywords at runtime

The keywords of a cell become keywords of the session's suite file, as if they were written in its
`*** Keywords ***` section. They have the precedence suite file keywords have in Robot Framework.

1. Robot Framework's parser builds `UserKeyword` objects from the cell, with arguments, defaults, tags and embedded
   arguments (`get_model` plus `TestSuite.from_model`; the model gets the cell's source).
2. The session remembers which keywords came from which cell. When a cell runs again, its previous keywords are
   replaced; a keyword no longer in the cell is gone. Across cells, the definition executed last wins (decision 3):
   same-named keywords of other cells are removed too.
3. The session suite's keyword list is replaced with a slice assignment, `suite.resource.keywords[:] = ...`.

```python
new = list(TestSuite.from_model(model).resource.keywords)
keywords = session_suite.resource.keywords
keywords[:] = [kw for kw in keywords if not defined_by(cell, kw)] + new   # drops the keyword cache on RF 7
if RF_VERSION < (7, 0):
    # the suite file's keywords are built once at suite start; build them again
    # with the arguments the namespace of this version uses
    namespace._kw_store.user_keywords = (
        UserLibrary(session_suite.resource, UserLibrary.TEST_CASE_FILE_TYPE)   # RF 5.0
        if RF_VERSION < (6, 0)
        else UserLibrary(session_suite.resource, resource_file=False)        # RF 6.x
    )
```

- **Robot Framework 7:** public running-model API. `UserKeywords.append`, `extend`, `insert`, `__setitem__` and `clear`
  invalidate the keyword finder's cache; `remove`, `pop` and `del` don't, hence the slice assignment (checked in 7.0
  and 7.5).
- **Robot Framework 5.0 to 6.1:** `KeywordStore` builds a `UserLibrary` from the suite file once, when the suite
  starts; it has to be built again (internal attribute, one line per version).

Checked in a throwaway experiment (2026-10-25) on Robot Framework 5.0, 6.0, 6.1, 7.0 and 7.5: a keyword defined,
replaced with a new body, replaced with new `[Arguments]`, and removed when its cell no longer defines it.

Each keyword carries its cell's source and line numbers, which the debugger and the language server need.

### REPL mode

- Works like today's command-line REPL: `parse_input`, the `Library  X` shorthand, `${_}` for the last return value,
  errors of an input are reported, an empty input does nothing.
- Assignments are local, as in a test (decision 6), and carried from one driver test into the next.
- The command-line REPL keeps its dot commands; VS Code has none (decision 17).

### File context: sending from a file

When lines of a `.robot` or `.resource` file run in the REPL, the session first loads the file's context, from the
editor's current, possibly unsaved content:

- the imports of its Settings, its Variables section and its keywords; for a suite file, without tests and suite
  settings;
- only the parts that changed since the last load, so variables set in the REPL keep their values as long as the
  Variables section stays the same;
- `${CURDIR}` of the sent lines is the file's directory.

Robot Framework doesn't offer this on its own (checked with Robot Framework 7.5):

- `Import Resource` of a suite file fails: "Resource file with 'Test Cases' section is invalid.", and `Suite Setup`
  is reported as not allowed in a resource file.
- A second `Import Resource` of a file that changed keeps the old keywords: the importer caches resource files by
  path.
- `--source` only sets `${CURDIR}`, `${SUITE SOURCE}` and the base of relative imports, once for the whole session.

The prototype keeps the file's keywords as an in-memory resource under the file's path
(`namespace._kw_store.resources[path]`, wrapped in a `UserLibrary` before Robot Framework 7), which also replaces a
resource imported the usual way. In the execution layer this becomes a request of the kernel instead of a keyword
called with a snapshot file.

### Output

- One notebook output per output item: the items of one output are alternative presentations of the same thing,
  so a log and an error in the same output would hide one of them.
- Events while a cell runs (keyword start and end, messages) instead of one response at the end, so the cell's output
  grows live (`NotebookCellExecution.appendOutputItems`, `replaceOutputItems`).
- `Log To Console`, stdout and stderr as stream outputs of the cell. Robot Framework already captures `print()` of
  libraries into the log; `Log To Console` writes to `sys.__stdout__`.
- The return value of the last statement as its own output.
- Screenshots: libraries log `<img src>` relative to `${OUTPUT DIR}`, which a notebook output can't load; the kernel
  embeds or resolves them.

## Native REPL in the Interactive Window

### Opening and kernel

- A `NotebookController` for the notebook type `interactive`; `interactive.open` with the controller's id
  (`<extension id>/<controller id>`) opens the window and preselects the kernel.
- One window per workspace folder, reused through the `resource` argument of `interactive.open`.
- The kernel starts in the folder's Python environment and waits for RobotCode's environment state, as the
  Documentation Viewer does; a missing Robot Framework is reported as such.
- Restart and interrupt in the window's toolbar (`interactive/toolbar`).
- After the extension host restarts, VS Code restores the window with its history while the session is gone; the
  kernel has to start a new session for it.

### Way in

- **Shift+Enter** in Robot Framework files (decision 14, a default binding with
  `editorLangId == robotframework`, like the Python extension's), also in the editor's context menu:
  - with a selection: the selected lines, as whole lines;
  - without one: the statement under the cursor with its `...` lines; the whole block when the line opens one
    (`FOR`, `WHILE`, `IF` without an inline keyword, `TRY`, `GROUP`); the body of a test without its settings when
    the cursor is on the test's name. The cursor moves to the next statement.
  - The language server already returns selection ranges built from the AST, but without node types; telling a
    statement from its block needs its own request.
- **Run test to here** (decisions 10 and 11): the test runs as a real test of the session, with its Test Setup and
  the body up to and including the cursor line, without its teardown, so the state stays for experimenting. Cleaning
  up is the Suite Teardown's job at the end of the session, or a restart's.
- Both go only to the Interactive Window (decision 13): the file context, "run to here" and the way back need the
  kernel. "Start Terminal REPL" stays as it is.

### Way back

"Take over into the file" on a history cell (`interactive/cell/title`) inserts its code after the line the session
came from (decision 12): the last line "run to here" ran, or the last line sent. The indentation matches the target;
further cells taken over go below. A session that never came from a file has no such line.

### Native UI instead of dot commands

| Command-line REPL | VS Code |
|---|---|
| `.vars` | a variables view; `NotebookController.variableProvider` is only a proposal, so an own view or the debugger's variables |
| `.doc`, `.kw` | the Documentation Viewer and the Keywords view |
| `.imports` | open question |
| `.save` | export of the session as a `.robot` file (`_session_export.py`) |
| `.exit` | closing the window or restarting the kernel |

## Notebooks

- A notebook type of our own with `.robotbook` and a new, versioned format (decision 15). Files in the format of the
  2024 prototype are not read.
- Outputs are saved as readable JSON, without timings, so a notebook can serve as documentation with its results and
  a rerun changes little (decision 16). Execution numbers per kernel, starting again after a restart.
- Code cells in both modes, Markdown cells for documentation.
- "Run All" stops when interrupted.
- They ship with notebook synchronization in the language server (decision 20), see
  [Notebooks and the Interactive Window](#notebooks-and-the-interactive-window).

## Language server

### REPL documents

REPL inputs have no section header and no indentation. For execution, `BaseInterpreter._parse_test_body` puts them
under a synthetic test and indents every line by two spaces, so Robot Framework parses them as the body of a test:

```
 REPL input, as typed                    what Robot Framework parses
                                          *** Test Cases ***
                                          DummyTestCase423141592653589793
 FOR    ${i}    IN    1    2      ---->     FOR    ${i}    IN    1    2
 Log    ${i}                                Log    ${i}
 END                                        END
```

The language server builds the same virtual document, analyzes it with the existing analysis as a suite file and
maps positions back. For a single REPL source the offsets are constant: the line minus the synthetic header lines,
the column minus two.

- **Completion:** the cursor position goes in, the `textEdit` ranges of the items come back.
- **Semantic tokens:** tokens of the synthetic lines and of the two prefix spaces are dropped, the others shifted.
- **Diagnostics** on synthetic lines are dropped.
- **Hover, definitions, references, highlights:** the same mapping.

The virtual document mirrors the REPL's own rules, so that analysis and execution agree:

- settings such as `[Tags]` are errors ("Setting 'Tags' is not allowed in the REPL.", `_mark_settings_as_errors`);
- the `Library  X` shorthand and `Import Library`, `Import Resource` and `Import Variables` with literal arguments are
  hoisted as imports into a `*** Settings ***` part, as `_session_export.py` does for `.save`. The analysis takes
  imports from settings only; no handling of `Import Library` as a keyword call turned up in the analyzer, so without
  hoisting every keyword after `Import Library  Browser` would be reported as not found;
- `${CURDIR}` is the directory of the source;
- a `...` at the start of an input is an error.

One mechanism serves every source: a virtual document with a line map that records, for every virtual line, the
URI, the line and the column offset it comes from.

```
 virtual document              origin of each line (URI, line, column offset)
 +-------------------------+
 | *** Settings ***        |   Robot mode cells, hoisted REPL imports
 | ...                     |
 | *** Keywords ***        |   Robot mode cell 2          (offset 0)
 | ...                     |
 | *** Test Cases ***      |   Robot mode cell 3          (offset 0)
 | ...                     |
 | *** Test Cases ***      |   synthetic
 | Driver                  |   synthetic
 |   Log    hello          |   REPL cell 4, input box or .robotrepl file  (offset 2)
 +-------------------------+
```

- **A `.robotrepl` file:** one source, constant offsets.
- **The Interactive Window:** the history cells and the input box.
- **A notebook:** Robot mode cells unshifted, REPL mode cells with offset 2, each cell with its own first line.

The language features translate in this one place instead of each on its own.

**REPL files today:** the language `robotframework-repl` (`.robotrepl`, `.robotscript`) has a TextMate grammar only.
The Python side doesn't know the language, and the language client only sends `robotframework` documents to the
server (`supportedLanguages` in `languageclientsmanger.ts`). With the virtual document these files get completion,
hover, semantic tokens, diagnostics and navigation. They are its first consumer (decision 19): they need no notebook
synchronization, so the mapping can be built and tested on plain files before cells and the input box use it.

### Notebooks and the Interactive Window

Notebooks ship together with notebook synchronization (decision 20), so Robot mode and REPL mode cells have language
features from the start. LSP's simpler mode `cellContent`, where every cell is analyzed like a file of its own, is
no interim solution: a test in one cell calling a keyword of another cell would be reported as not found.

- **Synchronization:** the server announces `notebookDocumentSync` in the mode `notebook`, with a `notebookSelector`
  for the notebook types `robotframework-repl` (or the new type's id) and `interactive` and the cell languages
  `robotframework` and `robotframework-repl`. `vscode-languageclient` 10.1.2 already has the
  `NotebookDocumentSyncFeature`; it activates when the server announces the capability.
- **Notebook model:** handlers for `notebookDocument/didOpen`, `didChange`, `didSave` and `didClose`. Per notebook,
  the server builds one virtual Robot Framework document mirroring the session suite (see
  [REPL documents](#repl-documents)): all Robot mode cells as sections, the REPL mode cells as the body of the driver
  test. Order (decision 7): the cells' order in a notebook;
  in the Interactive Window the history, the input box last.
- **Mapping:** results of the existing analysis (diagnostics, completion, hover, definitions, semantic tokens) are
  mapped back to the cells' positions; diagnostics go to the cell they belong to.
- **Today:** the server has the notebook types (`packages/core/src/robotcode/core/lsp/types.py`), but no
  `notebookDocument/*` handlers; `common/parts/documents.py` only handles `textDocument/*`. A cell URI would also
  fail later: `get_document_type` decides by file suffix, a `.robotbook` path is `UNKNOWN`, and that raises
  `UnknownFileTypeError`.
- **Input box:** the Interactive Window's input is a separate text document, not part of the notebook. VS Code
  creates `untitled:/Interactive-N.interactive` and `vscode-interactive-input:/InteractiveInput-N` with the same
  counter; the server has to pair them.
- **Inputs from a file:** a REPL input sent from a file runs with that file's context; analyzing it with the file's
  imports is still open.

## Debugging

- The kernel process runs RobotCode's DAP debugger; "Debug Cell" starts a debug session that attaches to it (the
  debugger already supports `attach` with `connect`, `host`, `port` and `pathMappings`) and runs the cell.
- VS Code sends breakpoints set in a cell with the cell's URI as `source.path`, and shows a frame in a cell when the
  adapter reports the cell's URI. The archived sample `vscode-nodebook` translates both directions in a
  `DebugAdapterTracker`.
- In RobotCode the translation hangs on the cell's source: the kernel parses each cell under its own source, keywords
  and tests carry it, `set_breakpoints` keeps breakpoints by path.
- `contributes.breakpoints` only lists `robotframework`; cells in `robotframework-repl` get no breakpoint gutter yet.
- The debug core of `robot-debug` stays for the command-line REPL.

## Open questions

- **Variables view:** what replaces `.vars` (an own view, the debugger's variables, both).
- **"Run to here" inside a keyword:** decisions 10 and 11 cover tests; a cursor in a keyword body has no arguments to
  run with.
- **Way back:** only cells that passed, several at once, and what a session without an origin line does.
- **Inputs from a file in the language server:** analyze them with the file's imports.
- **Pairing the input box** with its Interactive Window in the language server.
- **Breakpoints in REPL cells:** add `robotframework-repl` to `contributes.breakpoints`.
- **File context on Robot Framework 5.0 and 6.0:** `ResourceFile.from_model` exists from 6.1; the experiment built
  keywords with `TestSuite.from_model`, which also works on 5.0.

## Order

Decisions 18 to 20, to be cut into changes later:

1. Execution layer in `packages/repl`: session suite with driver tests, Robot mode, keywords at runtime, Suite Setup
   and Teardown, file context, output events, `.robot` in the command-line REPL; `repl-server` on the new layer.
2. Language server for REPL documents: the virtual document with its line map, the REPL's rules, `.robotrepl` and
   `.robotscript` files. The Interactive Window's input box can use it as a single document from the start.
3. Native REPL: Interactive Window, Shift+Enter, run to here, way back, kernel lifecycle.
4. Notebooks with notebook synchronization in the language server: new `.robotbook` format, two cell modes, saved
   outputs; Robot mode and REPL mode cells in the notebook's virtual document; the Interactive Window's history as
   context for its input box.
5. Debugging cells over DAP.

## Platform facts and sources

Checked on 2026-10-23 to 2026-10-25.

### VS Code

- Stable notebook API (`@types/vscode` 1.140): `NotebookSerializer`, `NotebookDocumentContentOptions`
  (`transientOutputs`, `transientCellMetadata`, `transientDocumentMetadata`), `NotebookController`
  (`supportedLanguages`, `executeHandler`, `interruptHandler`, `supportsExecutionOrder`, `updateNotebookAffinity`,
  `onDidChangeSelectedNotebooks`, `description`, `detail`), `NotebookCellExecution` (`appendOutput`,
  `appendOutputItems`, `replaceOutputItems`, `token`), `notebooks.createRendererMessaging`,
  `notebooks.registerNotebookCellStatusBarItemProvider`, `NotebookEdit`, `workspace.onDidChangeNotebookDocument`.
- Notebook renderers are chosen by MIME type only (`notebookRenderer` contribution: `id`, `displayName`,
  `mimeTypes`, `entrypoint`, dependencies, `requiresMessaging`), so the log renderer also works in the Interactive
  Window.
- `interactive.open` is a public API command (`src/vs/workbench/api/common/extHostInteractive.ts`, wrapping
  `_interactive.open` in `src/vs/workbench/contrib/interactive/browser/interactive.contribution.ts`): arguments
  `showOptions`, `resource`, `controllerId`, `title`; it returns `{ notebookUri, inputUri, notebookEditor }`.
  `interactive.execute` runs the input box: Ctrl+Enter always, Enter or Shift+Enter depending on
  `interactiveWindow.executeWithShiftEnter` (default `false`, so Enter); the input's language is the first of the
  active kernel's `supportedLanguages`. Menus `interactive/toolbar` and `interactive/cell/title` exist.
- VS Code's wiki ("Interactive Window Documentation") describes the component as the way for extensions "to offer REPL
  like experience to its users".
- Proposals on VS Code `main`: `notebookReplDocument` (`showNotebookDocument(..., { asRepl })`, `replOptions`) and
  `notebookVariableProvider` (`NotebookController.variableProvider`). Not usable by a Marketplace extension.
- VS Code ships the `ipynb` extension, which registers the notebook type `jupyter-notebook` for `*.ipynb`.
- Debugging: the notebook guide says a kernel can implement a debug adapter; samples `vscode-nodebook` (archived) and
  `vscode-simple-jupyter-notebook`.

### LSP 3.17

- Two modes: `cellContent` (cells as plain text documents over `textDocument/did*`) and `notebook`
  (`notebookDocument/didOpen`, `didChange`, `didSave`, `didClose` with the notebook, its cells, their kind, metadata and
  `executionSummary`; the cell text travels inside these notifications).
- The specification motivates `notebook` with the case of this design: completion in cell two needs what cell one
  defines.
- Server capability `notebookDocumentSync` with `notebookSelector` (notebook filter and cell languages); client
  capability `notebookDocument.synchronization` with `executionSummarySupport`.
- For requests such as completion or hover, cells are ordinary text documents with their cell URIs.

### Robot Framework

Checked in the installed versions of the test environments:

- `ItemList.__iter__` iterates by index, and `SuiteVisitor.visit_suite` visits the teardown after the tests (5.0,
  7.5).
- `VariableScopes.start_test` and `end_test` keep a single test slot (5.0, 7.5).
- `KeywordStore` finds suite file keywords through `suite_file.find_keywords` (7.0, 7.5) or a `UserLibrary` built at
  suite start (5.0, 6.0, 6.1). `UserKeywords` invalidates the finder cache on `append`, `extend`, `insert`,
  `__setitem__` and `clear` (7.0, 7.5).
- `ResourceFile.from_model` and `from_string` exist from 6.1 (not in 5.0 and 6.0). Variable sections are set with
  `set_from_variable_table` up to 6.1 and with `set_from_variable_section` from 7.0.
- `Namespace._handle_imports`, `import_library`, `import_resource` and `import_variables` exist in 5.0, 6.0, 6.1, 7.0
  and 7.5; `import_library` has no `notify` parameter in 7.5.

### Reference implementations

They solve the same problem: a language REPL in VS Code's notebook UI.

- **Python extension** (`microsoft/vscode-python`, `src/client/repl/`): its native REPL is a `NotebookController`
  for `jupyter-notebook` plus `python_files/python_server.py` over JSON-RPC (`execute`, interrupt, an `input`
  request), shown with the proposal `asRepl`; code is inserted as a cell and run with `notebook.cell.execute`.
  Shift+Enter (`python.execInREPL`) is bound to `editorLangId == python` and sends to the native REPL only with
  `python.REPL.sendToNativeREPL` (default `false`).
- **Jupyter extension** (`microsoft/vscode-jupyter`, `src/interactive-window/interactiveWindowProvider.ts`): its
  Interactive Window uses `interactive.open`; "Run Selection/Line in Interactive Window", and Shift+Enter sends to
  it with `jupyter.interactiveWindow.textEditor.executeSelection`.
- **R extension** (`REditorSupport/vscode-R` 3.2.0, 2026-10-15): experimental persistent R sessions in the
  Interactive Window without any API proposal; `r.interactive.executionTarget` (`auto`, `terminal`, `interactive`)
  chooses where code from the editor goes.
