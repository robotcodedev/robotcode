---
title: Browsing Library Documentation
description: Show the documentation of a library, resource file or suite file with robotcode doc, as Markdown, as JSON or in a terminal viewer, with the project's configuration.
sidebar:
  label: Browsing Documentation
  order: 60
---

:::tip[Installation]
The `robotcode doc` command comes from the optional **`repl`** package. If it isn't installed yet, add it:

```bash
pip install "robotcode[repl]"   # or: pip install "robotcode[all]"
```
:::

**`robotcode doc`** shows the documentation of a library, a resource file or the keywords of a suite file the way your project sees it: with the installed library versions, the project's `robot.toml` configuration and profiles, its python path, variables and variable files, and the import arguments you give. The documentation is generated anew on every call, so a change to a library or resource shows up the next time you run the command.

The output is Markdown: rendered on a colour terminal, raw Markdown in a pipe, with `--no-color` and in AI-agent sessions, a Markdown file with `-o`, or JSON with the global `--format json` for scripts and editor integrations.

**Who this is for:**

- **Developers** who want to look up a keyword, its arguments and its documentation without leaving the terminal.
- **AI coding agents** that need the keywords of the installed libraries and of the project's resource files, instead of guessing from generic knowledge.
- **Documentation builds** that publish the documentation of a library or resource file as Markdown.
- **Editor integrations**, which read the JSON output.

The four subcommands take the same target and the same configuration options:

| Subcommand | Use it when you want to … |
|---|---|
| [`lib`](#lib-the-full-documentation) | … read the full documentation of a library, resource file or suite file |
| [`keywords`](#keywords-an-overview-of-the-keywords) | … list the keywords with their arguments and a short description, optionally filtered |
| [`keyword`](#keyword-the-documentation-of-single-keywords) | … read the full documentation of one or more keywords |
| [`browse`](#browse-the-documentation-in-the-terminal-viewer) | … browse the full documentation in the terminal, with links, search and back/forward |

For the exhaustive option list see the auto-generated [CLI reference](/reference/cli/#doc).

## Quick start

```bash
# The full documentation of a standard library
robotcode doc lib Collections

# Every keyword of Collections with "dictionary" in its name
robotcode doc keywords Collections dictionary

# The documentation of one keyword
robotcode doc keyword Collections "Get Match Count"

# A resource file of the project, with a keyword that has embedded arguments
robotcode doc keyword resources/common.resource "Open Chrome Browser"

# Browse a library in the terminal viewer
robotcode doc browse BuiltIn

# Write the documentation of a resource file to a Markdown file
robotcode doc lib -o common.md resources/common.resource
```

## Targets

Every subcommand documents exactly one TARGET, like Robot Framework's Libdoc:

- **A library name**, such as `Collections`, `SeleniumLibrary`, a module or `module.Class`.
- **The path of a library file**, such as `lib/MyLibrary.py`.
- **The path of a resource file**, with an extension Robot Framework accepts for resource imports in the installed version, such as `.resource`, `.robot` or `.txt`, and with Robot Framework 7.5 also Markdown resource files (`.md`). Resource files take no import arguments.
- **The path of a suite file**, a file with a `*** Test Cases ***` or `*** Tasks ***` section. The keywords of its `*** Keywords ***` section are documented under the suite's name, with the type `SUITE`.
- **The path of a suite initialization file**, such as `tests/__init__.robot`. Its keywords are documented under the name Robot Framework gives the suite of its directory: `tests/01__login/__init__.robot` becomes `Suite *Login*`. A `Name` setting in the file, available since Robot Framework 6.1, wins.

Relative paths are resolved against the directory you run the command in (see [`--base-dir`](#configuration)). A library name that exists as a path is imported by that path, as Libdoc does, so a directory is imported as a library too. Whether the target is a file or a library is decided after the variables in it are resolved, so `-v COMMON:resources/common.resource '${COMMON}'` documents the resource file.

### Import arguments

Import arguments follow the target, separated by `::`, as in Libdoc:

```bash
robotcode doc keywords 'SeleniumLibrary::plugins=MyPlugin'
robotcode doc lib 'Remote::http://localhost:8270'
```

Variables in the target and in its arguments are resolved with the project's variables (see [Configuration](#configuration)), so this works too:

```bash
robotcode -p dev doc keywords 'MyLibrary::${MODE}'
```

The target is split at `::` before variables are resolved. An argument that itself contains `::`, such as an IPv6 address, is therefore passed through a variable:

```bash
robotcode doc lib -v 'HOST:[::1]' 'Remote::http://${HOST}:8270'
```

Quote the target in the shell, so that the shell leaves `${…}` alone. A backslash in the target is part of its text, as in a Windows path such as `'${CURDIR}\resources\common.resource'`; it is not an escape character as in Robot Framework data.

## Configuration

`robotcode doc` loads the target the way `robot` loads it:

- **`robot.toml` and the selected profiles** (`robotcode -p <profile> doc …`) provide the environment variables (`env`), the python path, the variables and variable files, and the languages.
- **`-v/--variable`, `-V/--variablefile` and `-P/--pythonpath`** add variables, variable files and python path entries, as the options of the same name of `robot` do. Relative paths given to `-V` and `-P` are relative to the directory you run the command in, like the target.
- **`--language LANG`** adds a language to the languages of the configuration, so that translated resource and suite files can be read (Robot Framework 6.0 or newer). Robot Framework 5.0 has no language support; a language from the configuration or from `--language` is rejected there.
- **`--base-dir DIR`** sets the directory for `${CURDIR}` and for relative paths in the target. Its default is the directory you run the command in.

The analysis settings of `[tool.robotcode-analyze]` and RobotCode's cache are not used: every call imports the library or parses the file anew.

## Output

### Markdown

Without `--format`, `lib`, `keywords` and `keyword` write Markdown. On a colour terminal it is rendered and paged like the other `robotcode` commands; with `--no-color`, in a pipe and in AI-agent sessions it is written as raw Markdown.

With `-o/--output FILE` the Markdown is written to FILE instead, as UTF-8 with `\n` line endings on every platform. A relative FILE is relative to the directory you run the command in, and a missing directory is created. `-o` cannot be combined with any `--format` other than `text`.

The page of `lib` has:

- the title with the type and the name (`Library *Collections*`), the version and the scope;
- `Introduction`, the documentation of the library, resource or suite file, when there is any;
- `Importing`, with the arguments of the library, when it takes any;
- `Keywords`, starting with an index that links to every keyword, followed by the keywords ordered by name as Libdoc orders them; keywords tagged `robot:private` are left out;
- `Data types`, the types the keywords use, with Robot Framework 6.1 or newer.

The headings get the anchors GitHub gives them, so the index, the table of contents and the links from one keyword to another work in GitHub's and in VS Code's Markdown preview. References to data types in the documentation link to their entry under `Data types`, and so do the types in the argument tables and the return types, such as `int` to `integer (Standard)`; the rest of a type, such as brackets, the values of a `Literal` and types without an entry, stays inline code. Robot Framework variables in the text, such as `${name}`, are written as inline code, so that Markdown renderers with math support do not show them as formulas; documentation written in HTML or reStructuredText stays as it is.

### JSON

With the global `--format json` (or `json_indent`), `lib` prints one object:

| Field | Content |
|---|---|
| `name` | The name of the library, resource file or suite. |
| `type` | `LIBRARY`, `RESOURCE` or `SUITE`. |
| `version`, `scope` | The version, empty when there is none, and the scope (`GLOBAL`, `SUITE` or `TEST`). |
| `source`, `lineno` | The file the documentation comes from, empty when it is unknown, and the line in it, `-1` when it is unknown. |
| `markdown` | The page, as `robotcode --no-color doc lib` prints it. |
| `keywords` | One entry per keyword, in the order of the page. |
| `types` | One entry per data type, in the order of the page, with `name` and `anchor`: the anchor of its heading in `markdown`, to which the links to the type point. |

A keyword entry has `name`, `anchor` (the anchor of its heading in `markdown`), `args` (the arguments as one line of text), `short_doc` (the first paragraph of the documentation, as one line), `tags` and `doc` (the documentation as Markdown). References in `doc` and `short_doc` are written as inline code.

`keywords` and `keyword` print an object with the same fields except `markdown` and `types`; its `keywords` holds only the selected keywords.

```bash
robotcode --format json doc keywords Collections dictionary | jq -r '.keywords[].name'
```

## `lib`: the full documentation

```bash
robotcode doc lib Collections
robotcode doc lib resources/common.resource
robotcode doc lib -o builtin.md BuiltIn
```

`lib` prints the page described in [Markdown](#markdown). The REPL's `.doc` command shows the same page for a library or resource the session has imported.

## `keywords`: an overview of the keywords

```bash
robotcode doc keywords Collections                            # every keyword
robotcode doc keywords Collections dictionary                 # names that contain "dictionary"
robotcode doc keywords Collections "get*list"                 # "get", later followed by "list": Get From List, …
robotcode doc keywords Collections append insert              # names that contain "append" or "insert"
robotcode doc keywords resources/common.resource --tag smoke  # keywords tagged "smoke"
```

`keywords` lists the keywords of the page, one per line, with the name, the arguments and the first paragraph of the documentation.

- A **PATTERN** selects the keywords whose name contains it; several patterns select the keywords that match any of them. `*` and `?` are wildcards. Case, spaces and underscores are ignored, so `get_from_list` finds `Get From List`.
- **`--tag TAG`**, which can be given more than once, selects the keywords with a tag that matches TAG as a whole, with the same wildcards and ignoring case, spaces and underscores. Patterns and tags apply together.

When no keyword matches, the output says so and the exit code is 0.

## `keyword`: the documentation of single keywords

```bash
robotcode doc keyword Collections "Get Match Count"
robotcode doc keyword BuiltIn "Should Be*"
robotcode doc keyword resources/common.resource "Open Chrome Browser"
```

`keyword` shows the full documentation of the keywords the NAMEs select, followed by the data types their arguments use. A NAME selects:

- the keyword whose name matches it, ignoring case, spaces and underscores;
- the keywords that match it as a pattern with `*` and `?`;
- the keywords with embedded arguments whose name matches it, so `Open Chrome Browser` shows `Open ${browser} Browser`.

A NAME that selects no keyword is reported on standard error, together with similar keyword names, and the exit code is 1. The keywords the other NAMEs select are still shown.

## `browse`: the documentation in the terminal viewer

```bash
robotcode doc browse Collections
```

`browse` opens the page of `lib` in the documentation viewer of the REPL. `Tab` moves through the links, `f` or `Enter` follows one, `[` and `]` go back and forward, and `/` searches; the REPL guide lists [all keys of the viewer](/guides/repl/#the-doc-viewer). `q` closes it.

`s` opens a sidebar with the outline of the page, as in Libdoc's HTML output: the sections of the introduction, `Importing`, every keyword and every data type. Typing filters the list with the rules of the [`keywords` patterns](#keywords-an-overview-of-the-keywords), `↑` and `↓` select an entry, the mouse wheel scrolls the list, `Enter` or a click jumps to the heading of the entry, and `Esc` hides the sidebar.

- **In a terminal with at least 94 columns**, the sidebar stands left of the page, which is rendered narrower. It stays open after a jump, and `s` moves the focus back to it. `Esc` on the page hides the sidebar; only the next `Esc` closes the viewer.
- **In a narrower terminal**, the sidebar lies over the left part of the page, which keeps its width, and closes after a jump.

In AI-agent sessions, in a pipe and without a terminal, `browse` prints the page as `robotcode doc lib` does.

## When a target cannot be loaded

Like Libdoc, `robotcode doc` documents nothing when the target cannot be found, imported or initialised. It reports the error on standard error and exits with 1:

- a library that cannot be imported, or whose initialisation with the given arguments fails — also when it could be loaded without the arguments;
- a library whose keywords cannot be read, such as `Remote` without a running server;
- a variable in the target or its arguments that is not defined;
- a resource or suite file that does not exist, or that can be read neither as a resource file nor as a suite file — the error is the one Robot Framework reports for it as a resource file;
- import arguments given to a resource or suite file;
- an option Robot Framework rejects, such as a language on Robot Framework 5.0.

Other load errors, such as a keyword of a library that cannot be created or an error in a variable file, are reported on standard error while everything else is documented, and the exit code is 0. So are the errors and warnings Robot Framework itself reports while it reads a file.

| Exit code | Meaning |
|---|---|
| `0` | The documentation was written. |
| `1` | The target could not be loaded, or a NAME of `keyword` selected no keyword. |
| `2` | Invalid usage, such as an empty target or `-o` together with `--format json`. |
| `251` | A dry run (`robotcode --dry doc …`) printed the target and the options it would load it with. |

## Libraries that need a running test

A library whose keywords only exist while Robot Framework runs — for example, one that calls `BuiltIn().get_variable_value(...)` in `get_keyword_names` — cannot be documented this way: the command aborts with the library's error, as Libdoc does. Import the library in the [REPL](/guides/repl/) or stop in it with [`robot-debug`](/guides/robot-debug/), and use `.doc <library>` there, which shows the documentation of the loaded library.

## VS Code

The RobotCode extension for VS Code shows the same documentation in the **Documentation Viewer**, an editor tab. The viewer runs `robotcode doc lib` for you and renders the page with VS Code's built-in Markdown support, styled like VS Code's Markdown preview. Code blocks marked `robotframework` or `robot` are highlighted as Robot Framework code, in the viewer and in the Markdown preview of any Markdown file.

### Opening a viewer

- **RobotCode: Open Documentation Viewer** in the command palette opens a new viewer on `BuiltIn`. Its target field has the focus, so you can type the target you want.
- **Show in Documentation Viewer** is the first source action (right-click → *Source Action…*). It is offered on the name of a `Library` or `Resource` import, on a keyword in a keyword call, setup, teardown or template, and on the name of a keyword definition. It shows the library, resource file or suite file and scrolls to the keyword. It is the preferred source action, so a key of your own can run it without the menu, see [A key for the source actions](#a-key-for-the-source-actions).
- **Show in New Documentation Viewer**, offered next to it, shows the same in a new viewer, for example to keep two libraries side by side.
- In the **Keywords** view, the book button of an import or keyword shows it in the Documentation Viewer, and its context menu has both actions, also for the keywords of the current file.
- The **links in documentation** that RobotCode shows in a hover, in the details of a completion item, in signature help and in the tooltips of the Keywords view open the viewer, see [Links in hovers and tooltips](#links-in-hovers-and-tooltips).
- **RobotCode: Open Documentation Viewer in New Window**, in the command palette and in the context menu of a viewer's tab, opens a second viewer in a new window, with the target of the active viewer, or else of the viewer you used last, or `BuiltIn` without any viewer. From a tab's context menu it also copies the active viewer, which need not be the viewer whose tab you clicked.

### A key for the source actions

VS Code has no key for its *Source Action…* menu, and RobotCode does not define one. You can bind VS Code's command `editor.action.sourceAction` to a key in your keyboard shortcuts (*Preferences: Open Keyboard Shortcuts (JSON)*). This binding shows the menu with `Ctrl+Shift+.`, one key more than `Ctrl+.` for *Quick Fix*:

```json
{
  "key": "ctrl+shift+[Period]",
  "command": "editor.action.sourceAction",
  "when": "editorTextFocus"
}
```

VS Code also uses `Ctrl+Shift+.`, for example for *Focus and Select Breadcrumbs* and, in an editor, for *Replace with Next Value*; while an editor has the focus, your binding takes their place.

To run *Show in Documentation Viewer* at once, without the menu, give the binding these arguments. *Show in Documentation Viewer* is the preferred source action, and the menu then shows your key next to it:

```json
"args": { "kind": "source", "preferred": true, "apply": "first" }
```

Where the cursor offers no documentation, for example in a comment, VS Code then reports that no preferred source action is available.

### Links in hovers and tooltips

In a hover, in the details of a completion item, in signature help and in the tooltips of the Keywords view, the documentation links into the viewer:

- The heading, such as `Keyword Log` or `Library Collections`, shows the library, resource file or suite file, at the keyword for a keyword. On the alias of an import and on the prefix of a keyword call, such as `Collections` in `Collections.Append To List`, it shows the page of that import from its start.
- The names of keywords, data types and sections of the same library or file, the types in the argument table and the return type show the page at that keyword, data type or section. Names of other libraries and private keywords stay inline code, as on the page.
- Links to a place in the documentation itself, such as the entries of a table of contents, show the page at that place.

The links show the documentation of the import that the analysis used, also for the second import of a library with other arguments, and in the viewer that [*Show in Documentation Viewer*](#which-viewer-an-action-uses) uses. When the arguments of an import fail and RobotCode loads the library without them (`LibraryLoadedWithoutArguments`), the links and *Show in Documentation Viewer* on that import show the library without arguments, as the hover does. The hovers of a Variables import, of a call that matches several keywords, of a variable and of a test case have no links, and links to a place in their documentation are text. When the links would make documentation longer than VS Code shows, only its heading is a link.

`command:` links written in the documentation of a library do nothing; only the links to the viewer run.

### The target field

The field in the toolbar shows what the viewer documents and takes a new target, as the [targets](#targets) of `robotcode doc`: `Name`, `Name::arg1::arg2`, or the path of a library, resource or suite file, relative to the workspace folder or absolute. `Enter` shows it in the same tab, which takes the name of the library or file as its title. Entering the target that is shown generates it again.

### Workspace folders

Each viewer belongs to a workspace folder: its pages are generated with the Python environment, the profiles and the settings of that folder. A viewer that shows documentation for an action from the editor or the Keywords view belongs to the folder of the file the action came from, also when the documented file lies in another folder. Typing an absolute path that lies in another folder switches the viewer to that folder.

In a workspace with more than one folder, the toolbar shows the name of the viewer's folder before the pin button. Click it to pick another folder; the viewer then shows its target for that folder, and back returns to the folder before.

### Outline and filter

The outline on the left lists the sections of the page, its keywords and its data types. Clicking an entry or pressing `Enter` shows its heading.

- `↑` and `↓` move through the entries, `→` and `←` open and close a section, `Home`, `End`, `Page Up` and `Page Down` move by more, and typing jumps to the next entry whose title starts with what you typed.
- The filter field above the outline keeps the entries whose titles match, with the rules of the [`keywords` patterns](#keywords-an-overview-of-the-keywords): contains, `*`, `?` and `[…]`, ignoring case, spaces and underscores. A section stays while it or one of its entries matches.

### Links, back and forward

Links to sections, keywords and data types move within the page. `http`, `https` and `mailto` links open outside VS Code.

Back and forward work as in a browser: with the buttons in the toolbar, with `Alt+←` and `Alt+→` (`Cmd+[` and `Cmd+]` on macOS) while the viewer has the focus, and with the back and forward buttons of the mouse. On Windows, `Alt+←` and `Alt+→` in a viewer navigate the viewer instead of VS Code's editor history.

### Find

`Ctrl+F` (`Cmd+F` on macOS) opens a find bar for the page, which shows the number of matches and the current one. `Enter` or `F3` goes to the next match, `Shift+Enter` or `Shift+F3` to the previous one, and `Esc` closes the bar. The outline is not searched.

A space in the search text matches any white space, also where the documentation breaks a line within a paragraph. While the bar is open, a page you go to opens where it would without it, and the first match in view becomes the current one.

### Arranging viewers

Several viewers can be open at the same time. You arrange them like editors: drag them into other editor groups or side by side, pin their tabs, or move one into a window of its own with VS Code's *Move Editor into New Window*. A viewer keeps its target, position, history and filter when its tab is hidden, when it is moved, and after a reload of the window. A viewer cannot be split or copied, and *Reopen Closed Editor* does not bring a closed viewer back.

### Which viewer an action uses

*Show in Documentation Viewer*, the links in hovers and tooltips and the book button of the Keywords view use:

1. the viewer you pinned with the pin button in its toolbar;
2. otherwise the viewer you used last;
3. otherwise a new viewer, beside the active editor, so that the focus stays in the editor.

*Show in New Documentation Viewer* always opens a new viewer, also when a viewer is pinned; the new viewer is then the viewer used last. Only one viewer can be pinned at a time. With the setting `robotcode.documentationViewer.openLocation` set to `active`, a new viewer opens in the active editor group instead. Links, the outline, the target field, back and forward always stay in their own viewer.

### What a page is generated with

The viewer runs `robotcode --format json doc lib TARGET` in the Python environment that RobotCode uses for the workspace folder, with:

- the profiles of `robotcode.profiles`;
- `robotcode.robot.pythonPath`, `robotcode.robot.languages`, `robotcode.robot.variables` and `robotcode.robot.variableFiles`, passed as `-P`, `--language`, `-v` and `-V`;
- the environment variables of `robotcode.robot.env`.

For an import of another file, such as a resource file that imports a resource file of its own, *Show in Documentation Viewer*, the links and the book button resolve the import against the directory of the file that contains it, as Robot Framework does.

The last page of each target is kept in VS Code's storage for the workspace, per workspace folder, Python environment, profiles and the settings above, also across restarts; the pages of the 50 most recently generated targets are kept. So a target that you show after you selected another profile or changed one of these settings is generated again. Showing a target shows its kept page at once and generates it again in the background, once per session. The refresh button in the toolbar generates it again whenever you want. When an action or a link shows a keyword, a data type or a place that the page does not have yet, such as a keyword you just added, the viewer generates the page again, and shows it from its start if the new page does not have it either. When the generation fails, the viewer shows the error, above the kept page if there is one, or with a *Retry* button.

### Open as Markdown

*Open as Markdown*, the button after the refresh button in the toolbar, opens the Markdown of the page the viewer shows, as `robotcode doc lib` writes it, as a new untitled document in the viewer's editor group. You can copy from it, or save it; saving asks for a file name. The viewer keeps its target, position and history. While the viewer shows no page, for example while the first page of a target is generated, the button is disabled.

### Limits

- Import arguments are passed to `robotcode doc` as text, so typed values such as `${True}` or lists arrive in their string form.
- Pages are generated from the saved files; unsaved changes in an editor are not shown.
- Libraries whose keywords exist only while a test runs cannot be documented; see [Libraries that need a running test](#libraries-that-need-a-running-test).
- The page needs VS Code's built-in extension *Markdown Language Features*. Without it, the viewer shows a notice and the page as plain Markdown text.
- Your Markdown settings, such as `markdown.preview.breaks`, and the Markdown plugins of other extensions apply to the page. Mathematical formulas are not laid out as in the Markdown preview, and mermaid diagrams stay source text.

### Open Documentation (deprecated)

The source action *Open Documentation (deprecated)* and *Show Documentation (deprecated)* in the context menu of the Keywords view are deprecated in favour of the Documentation Viewer. They still show Robot Framework's Libdoc HTML, served by the language server. In desktop VS Code these pages open beside the editor in VS Code's integrated browser, which reuses one tab for them. In VS Code for the Web, which has no integrated browser, they open in the Simple Browser.
