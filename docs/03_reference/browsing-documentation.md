# Browsing Library Documentation

::: tip Installation
The `robotcode doc` command comes from the optional **`repl`** package. If it isn't installed yet, add it:

```bash
pip install robotcode[repl]   # or: pip install robotcode[all]
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

For the exhaustive option list see the auto-generated [CLI reference](cli.md#doc).

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

The headings get the anchors GitHub gives them, so the index, the table of contents and the links from one keyword to another work in GitHub's and in VS Code's Markdown preview. References to data types in the documentation link to their entry under `Data types`. Robot Framework variables in the text, such as `${name}`, are written as inline code, so that Markdown renderers with math support do not show them as formulas; documentation written in HTML or reStructuredText stays as it is.

### JSON

With the global `--format json` (or `json-indent`), `lib` prints one object:

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

`browse` opens the page of `lib` in the documentation viewer of the REPL. `Tab` moves through the links, `f` or `Enter` follows one, `[` and `]` go back and forward, and `/` searches; the REPL guide lists [all keys of the viewer](repl.md#the-doc-viewer). `q` closes it.

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

A library whose keywords only exist while Robot Framework runs — for example, one that calls `BuiltIn().get_variable_value(...)` in `get_keyword_names` — cannot be documented this way: the command aborts with the library's error, as Libdoc does. Import the library in the [REPL](repl.md) or stop in it with [`robot-debug`](robot-debug.md), and use `.doc <library>` there, which shows the documentation of the loaded library.
