---
layout: home

hero:
  name: RobotCode
  text: The complete Robot Framework toolkit
  image:
    src: /robotcode-toy-tray.png
    alt: RobotCode Logo
  actions:
    - theme: brand
      text: Get Started
      link: /02_get_started
    - theme: alt
      text: Install VS Code
      link: https://marketplace.visualstudio.com/items?itemName=d-biehl.robotcode
    - theme: alt
      text: Install JetBrains
      link: https://plugins.jetbrains.com/plugin/26216
    - theme: alt
      text: Star on GitHub
      link: https://github.com/robotcodedev/robotcode
    - theme: alt
      text: Sponsor
      link: /#sponsor-robotcode

features:
  - icon: "🧠"
    title: Code intelligence
    details: |
      Context-aware completion for keywords (incl. embedded args), variables, libraries and resources. Hover docs, go-to-definition, find references, signature help, and live diagnostics — all powered by Robot Framework's own parser. Optional <a href="https://robocop.readthedocs.io">Robocop</a> integration adds further linting and formatting checks on top.
    link: /01_about
    linkText: Learn more

  - icon: "✏️"
    title: Project-wide refactoring
    details: |
      Rename keywords, arguments, variables and files safely across your entire workspace, including resources, libraries and multi-root setups. Preview every change before applying it.
    link: /01_about
    linkText: Learn refactoring

  - icon: "🐞"
    title: Run, debug & test explorer
    details: |
      Discover and run tests from the editor's test panel or the CLI. Set breakpoints, step through keywords, inspect variables via the Debug Adapter Protocol, and jump straight to failures.
    link: /02_get_started
    linkText: Get Started

  - icon: "⚙️"
    title: One config everywhere
    details: |
      A unified <a href="/03_reference/config">robot.toml</a> with profiles for dev, staging, CI, OS-specific or browser-specific setups. Editor, CLI and CI all read the same configuration — what works locally works in CI.
    link: /03_reference/config
    linkText: robot.toml reference

  - icon: "🧰"
    title: Powerful CLI
    details: |
      A complete command-line interface for running, discovering, analyzing and inspecting Robot Framework projects. Every command is project-aware, JSON-friendly, and CI-ready.
    link: /03_reference/cli
    linkText: CLI reference

  - icon: "📓"
    title: REPL & notebooks
    details: |
      Try keywords interactively with <code>robotcode repl</code> or work in <code>.robotbook</code> files with a Jupyter Notebook-style UI. Great for experimentation, demos, and debugging snippets.
    link: /03_reference/cli#repl
    linkText: REPL docs

  - icon: "🧩"
    title: Multi-IDE, same core
    details: |
      One Robot Framework language server powers VS Code, JetBrains, Neovim, Sublime Text and any LSP-capable editor. Choose your IDE — capabilities stay aligned.
    link: /01_about
    linkText: IDE overview

  - icon: "🤝"
    title: Open source, built with the community
    details: |
      Free and open source — developed in close collaboration with the Robot Framework Core team and a worldwide community of testers, developers, and contributors.
    link: https://github.com/robotcodedev/robotcode
    linkText: GitHub

---

## See RobotCode in Action


![Code Completions](/autocomplete1.gif)
*Code completions for keywords, arguments and variables in the editor.*

---

![Running tests](/running_tests.gif)
*Running tests right from the editor.*


## Watch: RoboCon 2024 tutorial

<lite-youtube videoid="7Uad_250YuI" />

This recorded RoboCon 2024 tutorial walks through the core features of RobotCode and demonstrates how to integrate the Language Server into your daily Robot Framework workflow.

- Length: ~2 hours.
- Level: Beginner to intermediate — basic familiarity with Robot Framework and a working Python environment is recommended.

What you will learn:

- How to install and enable the RobotCode extension for VS Code and JetBrains.
- How the Language Server provides completion, hover documentation, and signature help to speed up test authoring.
- Running and debugging tests from the editor, setting breakpoints, and inspecting variables during execution.
- Using the built-in REPL and test discovery features to explore and iterate quickly.
- and many more...

## Sponsor RobotCode

**Individual:**
- [GitHub Sponsors](https://github.com/sponsors/robotcodedev) – monthly or one-time
- [Open Collective](https://opencollective.com/robotcode) – one-time or recurring

**Corporate:**
- [Open Collective](https://opencollective.com/robotcode) – direct, transparent, invoices, public ledger
- [Robot Framework Foundation membership](https://robotframework.org/foundation/) – ecosystem support, indirectly benefits RobotCode

See [Support & Contribute](/05_contributing/) for non-financial ways to help — bug reports, PRs, community help, and more.


## Powered by
[![imbus AG](images/imbus-web-logo.svg)](https://www.imbus.de)
[![Robot Framework Foundation](images/RFFoundation.svg)](https://robotframework.org/foundation)
[![JetBrains Logo](images/jetbrains.svg)](https://jb.gg/OpenSourceSupport)
