# RobotCode - The Ultimate Robot Framework Toolset

[![License](https://img.shields.io/github/license/robotcodedev/robotcode?style=flat&logo=apache)](https://github.com/robotcodedev/robotcode/blob/main/LICENSE)
[![Build Status](https://img.shields.io/github/actions/workflow/status/robotcodedev/robotcode/build-test-package-publish.yml?branch=main&style=flat&logo=github)](https://github.com/robotcodedev/robotcode/actions?query=workflow:build_test_package_publish)
[![VS Code Marketplace](https://img.shields.io/visual-studio-marketplace/v/d-biehl.robotcode?style=flat&label=VS%20Marketplace&logo=visual-studio-code)](https://marketplace.visualstudio.com/items?itemName=d-biehl.robotcode)
[![Installs](https://img.shields.io/visual-studio-marketplace/i/d-biehl.robotcode?style=flat)](https://marketplace.visualstudio.com/items?itemName=d-biehl.robotcode)
[![JetBrains Marketplace](https://img.shields.io/jetbrains/plugin/v/26216.svg)](https://plugins.jetbrains.com/plugin/26216)
[![Downloads](https://img.shields.io/jetbrains/plugin/d/26216.svg)](https://plugins.jetbrains.com/plugin/26216)
[![PyPI - Version](https://img.shields.io/pypi/v/robotcode.svg?style=flat)](https://pypi.org/project/robotcode)
[![Python Version](https://img.shields.io/pypi/pyversions/robotcode.svg?style=flat)](https://pypi.org/project/robotcode)
[![Downloads](https://img.shields.io/pypi/dm/robotcode.svg?style=flat&label=downloads)](https://pypi.org/project/robotcode)

---

## What is RobotCode?

RobotCode is a complete Robot Framework toolkit: a language server, IDE extensions for VS Code and the JetBrains platform, a powerful command-line interface, and a unified `robot.toml`-based configuration model. It is designed for everyday Robot Framework work — from your first keyword to scaling multi-team test suites in CI.

Built on Robot Framework Core, RobotCode is developed in close collaboration with the Robot Framework Core team and supported by the [Robot Framework Foundation](https://robotframework.org/foundation/).


## Key Features

### Editor / IDE

- **Code intelligence** — completion for keywords, variables, libraries, and resources; hover documentation; go-to-definition; find references; signature help.
- **Keywords explorer** — browse, navigate, and insert keywords from imported libraries and resources via a dedicated sidebar view.
- **Refactoring** — project-wide rename of keywords, variables, and arguments.
- **Live diagnostics** — errors and warnings as you type, out of the box. Optional [Robocop](https://robocop.readthedocs.io/) integration adds further linting and formatting checks on top.
- **Debugging** — Robot Framework debugging via the [Debug Adapter Protocol](https://microsoft.github.io/debug-adapter-protocol/), with breakpoints in keywords and step-through control.
- **Syntax highlighting** — full Robot Framework grammar including embedded arguments, Python expressions, and environment variables with defaults.
- **Snippets** — quick insertion of common Robot Framework patterns.
- **Test view** — discover, run, debug, and inspect Robot Framework tests in the editor's test panel.
- **Interactive REPL & `.robotbook` notebooks** — try keywords live in a REPL or work in a Jupyter Notebook-style notebook format.
- **Multi-root workspaces** — manage multiple projects with different Python environments side by side.

### Configuration

One configuration model that follows your project from the editor into CI — no scattered command-line flags, no duplicated setups.

- **A single source of truth** — paths, variables, Python paths, listeners, modifiers, and every Robot Framework option live in `robot.toml` (or `pyproject.toml`). Editor, CLI, and CI all read the same setup; personal tweaks stay out of git via `.robot.toml`.
- **Profiles for every scenario** — keep dev, staging, CI, OS-specific, or browser-specific settings as named overlays. Activate with a single flag, layer them, inherit between them.
- **Total transparency** — see exactly what Robot Framework will receive after all files, profile overlays, and CLI flags are merged.
- **Schema-guided editing** — autocomplete and validation while you write your config catches typos and unsupported keys before you run.

### Command line

A complete command-line toolkit that knows your project as well as the editor does — same `robot.toml`, same profiles, same Python environment — so what runs in the IDE runs the same way on the CLI and in CI.

- **Run with everything wired up** — execute Robot Framework with your profiles, paths, variables, listeners, and modifiers automatically applied.
- **Find tests by anything** — search and filter suites, tasks, tags, sources, documentation, or even keyword calls inside test bodies, and narrow the run accordingly.
- **Drill into failures fast** — explore logs, stats, and diffs across runs, and compare today's run against yesterday's in a single command — without ever parsing `output.xml` by hand.
- **CI gates with editor-quality diagnostics** — project-wide static analysis that matches what you see while typing; reclassify, mask, or ignore categories per project.
- **Docs that actually find your project** — library and keyword documentation that resolves your project's resources, custom libraries, and Python paths the way Robot itself does.
- **Live experimentation** — try keywords interactively inside your project's environment before they land in a test.
- **Built for automation** — every command can speak JSON, so CI pipelines, dashboards, AI agents, and other tools consume the output without screen-scraping.

For the complete feature reference, see the [official documentation](https://robotcode.io).

## Requirements

**Runtime (always required):**
- Python 3.10 or newer
- Robot Framework 5.0 or newer

**Editor / IDE — any LSP-capable editor works.** For the dedicated extensions you need one of:
- Visual Studio Code 1.108.0 or newer
- PyCharm / IntelliJ IDEA 2025.3 or newer

Other editors (Neovim, Sublime Text, Helix, Emacs, …) connect to the language server via the `languageserver` extra from PyPI — see [Command Line and Other Editors](#command-line-and-other-editors) below.


## Getting Started

### Visual Studio Code

1. **Install the RobotCode Extension** from the [Visual Studio Marketplace](https://marketplace.visualstudio.com/items?itemName=d-biehl.robotcode).
2. **Continue with the [Getting Started Guide](https://robotcode.io/02_get_started/)** for setup, your first `robot.toml`, and running your first test.

**Extensions:**
RobotCode declares dependencies on the [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python) and [Python Debugger](https://marketplace.visualstudio.com/items?itemName=ms-python.debugpy) extensions so VS Code installs them when required. Additional extensions may be needed depending on your project.


### IntelliJ IDEA or PyCharm

1. **Install the RobotCode Plugin** — choose one of:

   - **Built-in Plugin Marketplace:** <kbd>Settings/Preferences</kbd> > <kbd>Plugins</kbd> > <kbd>Marketplace</kbd> > search for "RobotCode" > <kbd>Install</kbd>.
   - **[JetBrains Marketplace](https://plugins.jetbrains.com/plugin/26216):** click <kbd>Install to ...</kbd> if your IDE is running.
   - **Manual:** download the [latest release](https://github.com/robotcodedev/robotcode/releases/latest) and use <kbd>Settings/Preferences</kbd> > <kbd>Plugins</kbd> > <kbd>⚙️</kbd> > <kbd>Install plugin from disk...</kbd>.

2. **Continue with the [Getting Started Guide](https://robotcode.io/02_get_started/)** for setup, your first `robot.toml`, and running your first test.

**Plugins:**
RobotCode declares a dependency on [LSP4IJ](https://plugins.jetbrains.com/plugin/23257) so your IDE installs it automatically. Additional plugins may be required depending on your project needs.


### Command Line and Other Editors

For CI pipelines, the command line, or LSP-compatible editors like Neovim, Sublime Text, or Helix, install RobotCode from PyPI. The base `robotcode` package is only the CLI core; the actual commands live in extras such as `runner`, `analyze`, `debugger`, `languageserver`, and `repl`:

```bash
pip install robotcode[runner,analyze]
```

Pick the extras that match your use case — see the [CLI reference](https://robotcode.io/03_reference/cli) for the available packages and how to install them.


## Documentation

For detailed instructions, visit our **[official documentation](https://robotcode.io)**. Additional resources:

- **[Q&A](https://github.com/robotcodedev/robotcode/discussions/categories/q-a):** Answers to common questions about RobotCode.
- **[Tips & Tricks](https://robotcode.io/04_tip_and_tricks/):** Common pitfalls, editor customization, and setup recipes.
- **[Command Line Tools Reference](https://robotcode.io/03_reference/cli):** Comprehensive documentation on using RobotCode's CLI tools.
- **[Changelog](https://github.com/robotcodedev/robotcode/blob/main/CHANGELOG.md):** Track changes, updates, and new features in each release.
- **[Support & Contribute](https://robotcode.io/05_contributing/):** Ways to back the project — financial, code, feedback.


## Sponsor RobotCode

RobotCode is driven by the passion of its lead developer and a growing community. Financial support keeps the project sustainable and lets us continue adding features, improving stability, and expanding the ecosystem.

**Individual:**
- [GitHub Sponsors](https://github.com/sponsors/robotcodedev) – monthly or one-time
- [Open Collective](https://opencollective.com/robotcode) – one-time or recurring

**Corporate:**
- [Open Collective](https://opencollective.com/robotcode) – direct, transparent, invoices, public ledger
- [Robot Framework Foundation membership](https://robotframework.org/foundation/) – ecosystem support, indirectly benefits RobotCode


## Get Involved

You don't need to sponsor to help. Every contribution — feedback, code, advocacy — moves the project forward.

- Star the repository
- Leave a review on the [VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=d-biehl.robotcode) and [JetBrains Marketplace](https://plugins.jetbrains.com/plugin/26216)
- Ask questions & help others on [Slack #robotcode](https://slack.robotframework.org/), the [Forum](https://forum.robotframework.org), or [Discussions](https://github.com/robotcodedev/robotcode/discussions)
- Report bugs in the [issue tracker](https://github.com/robotcodedev/robotcode/issues)
- Suggest enhancements or features (issues or [Discussions](https://github.com/robotcodedev/robotcode/discussions))
- Share usage patterns & integration ideas in [Discussions](https://github.com/robotcodedev/robotcode/discussions)
- Improve tests (edge cases, large suites, multi-root, versions)
- Contribute code ([good first issue](https://github.com/robotcodedev/robotcode/labels/good%20first%20issue) / [help wanted](https://github.com/robotcodedev/robotcode/labels/help%20wanted))


## License

This project is licensed under the [Apache 2.0 License](https://spdx.org/licenses/Apache-2.0.html).

---

## Powered by

[Robot Framework Foundation](https://robotframework.org/foundation)


[JetBrains](https://jb.gg/OpenSourceSupport)
