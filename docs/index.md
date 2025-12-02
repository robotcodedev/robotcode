---
layout: home

hero:
  name: RobotCode
  text: Robot Framework IDE & CLI, the friendly way.
  tagline: Language server, debugger, analyzer, REPL, and shareable profiles for IDE & CI
  image:
    src: /robotcode-vintage-christmas.png
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
      text: CLI Reference
      link: /03_reference
    - theme: alt
      text: Star on GitHub
      link: https://github.com/robotcodedev/robotcode
    - theme: alt
      text: Sponsor
      link: /05_contributing/#how-you-can-support-robotcode

features:
  - icon: "🧠"
    title: Autocomplete and IntelliSense
    details: |
      Get fast, context‑aware suggestions for libraries, resources, keywords (incl. embedded args), variables and namespaces.
      Signature help, hover docs and inline diagnostics are powered by Robot Framework’s native parser for accuracy in both IDEs.

    link: /01_about
    linkText: Learn more

  - icon: "🐞"
    title: Run and Debug
    details: |
      Execute and debug tests directly from the editor or CLI. Set breakpoints, step through keywords, inspect variables,
      and jump to failures. Works with suites, folders or single tests and integrates with Robot Framework logs/reports.

    link: /02_get_started
    linkText: Get Started

  - icon: "✏️"
    title: Refactor with Confidence
    details: |
      Project‑wide rename for keywords, arguments, variables and files with safe previews. References in resources,
      libraries and tests are updated consistently across your workspace (incl. multi‑root setups).
    link: /01_about
    linkText: Learn refactoring

  - icon: "⚙️"
    title: Powerful CLI + robot.toml
    details: |
      A unified CLI (enhanced <code>robot</code>, <code>rebot</code>, <code>libdoc</code>, <code>discover</code>) plus a central <a href="/03_reference/config">robot.toml</a> for profiles,
      environments and repeatable execution. Ideal for local dev and CI pipelines.
    link: /03_reference/config
    linkText: robot.toml Reference

  - icon: "🧪"
    title: Test Discovery & Explorer
    details: |
      Automatically discover tests and suites. Filter by tags, names and glob patterns. Use the Test Explorer to run suites,
      folders or single cases — or leverage the <code>discover</code> command from the CLI.

    link: /03_reference/cli
    linkText: CLI discover

  - icon: "🔎"
    title: Hover, Go to Definition & Peek
    details: |
      Navigate precisely across libraries, resources, variables and keywords. Peek to definitions inline, jump with F12,
      and rely on consistent cross‑references — the same engine powers VS Code and JetBrains.

    link: /01_about
    linkText: Navigation features

  - icon: "🧹"
    title: Linting and Formatting with Robocop
    details: |
      Optional integration with <a href="https://robocop.readthedocs.io">Robocop</a>: configurable rules, severities and ignores.
      Run in the IDE or via CLI; keep quality high with actionable diagnostics and rule links. Configure via <code>robot.toml</code>.

    link: https://robocop.readthedocs.io
    linkText: Robocop Docs

  - icon: "🧩"
    title: Multi‑IDE, same core
    details: |
      One LSP core powers both VS Code and JetBrains for a consistent experience: completion, navigation, refactoring and diagnostics.
      Choose your IDE — capabilities stay aligned.

    link: /01_about
    linkText: IDE overview

  - icon: "📓"
    title: REPL & Notebooks
    details: |
      Try keywords interactively and prototype flows quickly. Use <code>robotcode repl</code> for local sessions or <code>repl-server</code> in headless setups.
      Great for experimentation, demos and debugging snippets.

    link: /03_reference/cli#repl
    linkText: REPL Docs

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

## Support RobotCode

- [GitHub Sponsors](https://github.com/sponsors/robotcodedev)
- [Open Collective](https://opencollective.com/robotcode)


## Powered by
[![imbus AG](images/imbus-web-logo.svg)](https://www.imbus.de)
[![Robot Framework Foundation](images/RFFoundation.svg)](https://robotframework.org/foundation)
[![JetBrains Logo](images/jetbrains.svg)](https://jb.gg/OpenSourceSupport)
