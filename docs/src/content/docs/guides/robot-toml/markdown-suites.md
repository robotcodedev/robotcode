---
title: Markdown Suites and Resources
description: Which Markdown files are suites, how imported Markdown resources are read, what the editor offers in the code blocks, and the limits.
sidebar:
  label: Markdown Suites
  order: 100.16
---

Since Robot Framework 7.5, a test suite or a resource file can be a Markdown document: the tests, keywords and settings live in fenced code blocks marked as `robot` or `robotframework`, and everything around them is ordinary Markdown that renders as documentation. Robot Framework reads only those code blocks, as one text, and from 7.5.1 on it reports the line and column numbers of the Markdown file. RobotCode reads Markdown files the same way: the analysis, the editor features and `robotcode analyze code` work on the code blocks, at the positions in the file, and the prose around them stays untouched.

A Markdown suite looks like this:

````markdown title="tests/shop.robot.md"
# Shop

Buying works for every customer, with or without an account.

```robot
*** Test Cases ***
Buy As A Guest
    Open Shop
    Buy    Book
```

The keywords stay next to the tests that use them.

```robot
*** Keywords ***
Open Shop
    Log    Opening the shop
```
````

The code blocks of a file belong together: a block without a section header continues the section of the block before it, so a test can go on in the next block after a paragraph of prose.

## Which Markdown files are suites

RobotCode serves the Markdown files that Robot Framework runs with your configuration, from Robot Framework 7.5.1 on. Without further settings, these are the files ending in `.robot.md`: Robot Framework parses them by default, next to `.robot` files. So `tests/shop.robot.md` is a suite as soon as it exists, and a `README.md` stays plain documentation.

Two settings of your [robot.toml](/guides/robot-toml/) change which files count, for Robot Framework and RobotCode alike.

`extensions` is the `--extension` option of Robot Framework. It replaces Robot Framework's default extensions, so list `robot` too:

```toml title="robot.toml"
extensions = "robot:md"
```

| Extension | Files |
| --- | --- |
| `robot.md` | only files ending in `.robot.md`, such as `shop.robot.md` |
| `md` | every `.md` file, including `README.md`, the other documentation of the project and the `.robot.md` files |
| `markdown` | every `.markdown` file |

With `md`, every Markdown file in the project is a suite for RobotCode and for Robot Framework; a file without `robot` code blocks simply has no tests. An `extensions` without a Markdown extension, such as `extensions = "robot"`, leaves out the Markdown files altogether.

`parse-include` is the `--parseinclude` option. A pattern with a Markdown extension makes Robot Framework parse the Markdown files that match it, and the patterns limit the files of every extension:

```toml title="robot.toml"
parse-include = ["*.robot", "docs/*.md"]
```

With this setting, the `.robot` files and the `.md` files directly in `docs` are suites, and a `.robot.md` file is not, since no pattern matches it. A pattern with a path is taken from the project root, where `robotcode robot` runs Robot Framework.

Like every setting, both can also go into a [profile](/guides/robot-toml/profiles/). To check which files your configuration lets Robot Framework parse, run:

```bash
robotcode discover info
```

Its output ends with the document formats Robot Framework parses and their extensions; without `extensions` and `parse-include`, that is:

```markdown
## Document Formats

- _robot:_ `robot`
- _json:_ `rbt`
- _rest:_ `robot.rst`
- _markdown:_ `robot.md`
```

The Markdown suites are the files of the `markdown` format. RobotCode serves no `json` and `rest` files. `robotcode -p <profile> discover info` shows the formats for a profile, and `robotcode --format json discover info` lists them as `documentFormats`. The patterns of `parse-include` do not show up there.

## Markdown resources

A `Resource` import of a `.md` or `.markdown` file needs no configuration. Robot Framework reads a resource file by its extension, whatever `extensions` says, and RobotCode does the same with Robot Framework 7.5.1 or newer: the keywords and variables come from the file's code blocks, and go to definition opens the Markdown file at the keyword's line.

```robot title="tests/checkout.robot"
*** Settings ***
Resource    ../resources/keywords.md
```

## In the editor

In VS Code a Markdown suite stays a Markdown document, with its preview and the other features of Markdown files. Inside the `robot` and `robotframework` code blocks, RobotCode adds what it offers in a `.robot` file, such as diagnostics, hover, completion, go to definition and references. Completion appears only on the lines of a code block, and code that a code action adds, such as a new keyword from **Create Keyword**, goes into a code block, with the block's indentation.

VS Code switches off suggestions while typing for Markdown files, and that holds in the code blocks too: there the completion list opens with **Ctrl+Space**, or after a character that opens it, such as a space after a keyword or `${`. To get it while typing, switch on quick suggestions for Markdown in your project's `.vscode/settings.json`, and switch off the word suggestions, which would otherwise offer the words of the file while you write prose:

```json title=".vscode/settings.json"
{
  "[markdown]": {
    "editor.quickSuggestions": { "other": "on" },
    "editor.wordBasedSuggestions": "off"
  }
}
```

The setting applies to every Markdown file of the project. RobotCode offers nothing outside the code blocks.

Breakpoints can be set on the lines of the code blocks of a Markdown suite, as in a `.robot` file, and debugging stops there.

VS Code asks `robotcode discover info` for the extensions of the `markdown` format when it starts the language server of a folder. After a change of the robot.toml, the language server restarts and serves the Markdown files of the new configuration.

## Analysis and formatting

`robotcode analyze code` checks the Markdown suites like `.robot` files and leaves the other Markdown files alone.

Robocop checks and formats Markdown files with its own support for them, which needs Robocop 9.2 or newer. Robocop reads each code block on its own: findings and formatting follow the blocks, not the text that Robot Framework puts together from them. A block that continues a test of the previous block can therefore get findings that the same code in one block would not get, and formatting can put a `*** Comments ***` header above such a block. Robocop also takes `shop.robot` as the suite name of `shop.robot.md`, where Robot Framework names the suite `Shop`, and so reports `not-allowed-char-in-filename` (`NAME15`) for every `.robot.md` file. Formatting works on the whole file; **Format Selection** leaves a Markdown file unchanged.

## Limits

- PyCharm does not support Markdown suites yet.
- `__init__.robot.md` is a suite file, not an initialization file, since Robot Framework reads it that way. With `md` in `extensions`, `__init__.md` is the initialization file of its folder.
- The Test Explorer does not refresh its tests when a Markdown file changes.
- Robot Framework 7.5.0 reads Markdown files too, but counts the lines of its code blocks put together instead of the lines of the file, so RobotCode reads Markdown suites and resources only from 7.5.1 on.

## See also

- [How RobotCode Finds Robot Framework Files](/guides/robot-toml/ignoring-files/) — which files RobotCode walks and how to keep folders out.
- [Settings](/guides/robot-toml/settings/) — how the settings of robot.toml map to the options of Robot Framework.
