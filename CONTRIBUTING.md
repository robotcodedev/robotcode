<!-- omit in toc -->
# Contributing to RobotCode

First off, thanks for taking the time to contribute! ❤️

All types of contributions are encouraged and valued. See the [Table of Contents](#table-of-contents) for different ways to help and details about how this project handles them. Please make sure to read the relevant section before making your contribution. It will make it a lot easier for us maintainers and smooth out the experience for all involved. The community looks forward to your contributions. 🎉

And if you like the project, but just don't have time to contribute, that's fine. There are other easy ways to support the project and show your appreciation, which we would also be very happy about:
- Star the project
- Tweet about it
- Refer this project in your project's readme
- Mention the project at local meetups and tell your friends/colleagues
- Sponsor this project by clicking on the sponsor button on the project page

<!-- omit in toc -->
## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [I Have a Question](#i-have-a-question)
- [Project-Wide Rules](#project-wide-rules)
  - [AI and Automated Contributions](#ai-and-automated-contributions)
  - [Payment, Bounty, and Monetization Requests](#payment-bounty-and-monetization-requests)
- [I Want To Contribute](#i-want-to-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Enhancements](#suggesting-enhancements)
  - [Your First Code Contribution](#your-first-code-contribution)
    - [Development Environment Setup](#development-environment-setup)
    - [IDE Configuration](#ide-configuration)
    - [Pre-commit Hooks](#pre-commit-hooks)
    - [Development Workflow](#development-workflow)
    - [Pull Request Guidelines](#pull-request-guidelines)
    - [Running Tests](#running-tests)
    - [Additional Development Commands](#additional-development-commands)
    - [Troubleshooting Development Setup](#troubleshooting-development-setup)
  - [Improving The Documentation](#improving-the-documentation)
- [Styleguides](#styleguides)
  - [Commit Messages](#commit-messages)
- [Join The Project Team](#join-the-project-team)


## Code of Conduct

This project and everyone participating in it is governed by the
[RobotCode Code of Conduct](https://github.com/robotcodedev/robotcode/blob/main/CODE_OF_CONDUCT.md).
By participating, you are expected to uphold this code. Please report unacceptable behavior
to <support@robotcode.io>.


## I Have a Question

If you want to ask a question, we assume that you have read the available [Documentation](https://robotcode.io).

Before you ask a question, it is best to search for existing [Issues](https://github.com/robotcodedev/robotcode/issues) that might help you. In case you have found a suitable issue and still need clarification, you can write your question in this issue. It is also advisable to search the internet for answers first.

If you then still feel the need to ask a question and need clarification, we recommend the following:

- Open an [Issue](https://github.com/robotcodedev/robotcode/issues/new/choose) of type `Question`.
- Provide as much context as you can about what you're running into.
- Provide project and platform versions (robotframework, python, vscode, etc), depending on what seems relevant.

We will then take care of the issue as soon as possible.

You can also ask questions in the Robot Frameworks [Slack](https://robotframework.slack.com) in the channel [#vscode](https://robotframework.slack.com/archives/C0103745J7P) or in the [Robot Framework Forum](https://forum.robotframework.org) in the [Tools/Visual Studio Code(ium)](https://forum.robotframework.org/c/tools/vscode/28) category.

## Project-Wide Rules

These rules apply to all interactions with the RobotCode project — pull requests, issues, discussions, comments, code review replies, and any other contribution. Please read them before opening a contribution of any kind.

### AI and Automated Contributions

AI-assisted or automated contributions, including agent-generated ones, must follow our [AI and Automated Contribution Policy](AI_POLICY.md). In short: the human submitter must understand, review, test, and maintain the contribution, and must disclose AI or tool assistance in the pull request, issue, or comment.

### Payment, Bounty, and Monetization Requests

RobotCode is an open-source project, not a lead-generation or micro-bounty platform.

Do not include payment links, invoices, donation requests, wallet addresses, "paid fix" notes, bounty claims, sponsorship requests, or similar monetization requests in pull requests, issues, discussions, comments, or any other project interaction unless paid work or a bounty process was explicitly agreed with the maintainers before the work started.

Unsolicited monetization requests attached to contributions are not accepted. Pull requests containing such requests may be closed without review, and issues or discussions containing such requests may be declined or closed.

If a contribution is part of an agreed paid engagement, sponsored work, or bounty process, disclose that context clearly and follow the agreed process. Do not add ad-hoc payment requests to the contribution body.

Contributions are reviewed on their technical merit, usefulness to RobotCode users, and compliance with the project's contribution standards — not on payment requests attached to them.

## I Want To Contribute

> [!IMPORTANT]
> **Legal Notice**
>
> When contributing to this project, you must agree that you have the right to submit the contribution under the project license.
>
> This means that the contribution was created in whole or in part by you, is based on previous work that you are allowed to submit under a compatible license, or was otherwise lawfully provided to you for contribution.
>
> This corresponds to the spirit of the [Developer Certificate of Origin](https://developercertificate.org/). You are encouraged to add a DCO sign-off to your commits with `git commit -s` — this only adds a `Signed-off-by` trailer and is separate from the cryptographic commit signature (`-S`, GPG/SSH) required by [Signed Commits Required](#signed-commits-required) below.
>
> If AI tools or automated agents were used, you remain the human submitter responsible for the contribution and must follow the AI and Automated Contribution Policy.

### Reporting Bugs

<!-- omit in toc -->
#### Before Submitting a Bug Report

A good bug report shouldn't leave others needing to chase you up for more information. Therefore, we ask you to investigate carefully, collect information and describe the issue in detail in your report. Please complete the following steps in advance to help us fix any potential bug as fast as possible.

- Make sure that you are using the latest version.
- Determine if your bug is really a bug and not an error on your side e.g. using incompatible environment components/versions (Make sure that you have read the [documentation](https://robotcode.io). If you are looking for support, you might want to check [this section](#i-have-a-question)).
- To see if other users have experienced (and potentially already solved) the same issue you are having, check if there is not already a bug report existing for your bug or error in the [bug tracker](https://github.com/robotcodedev/robotcode/issues?q=label%3Abug).
- Look or ask in the [Robot Framework Slack](https://robotframework.slack.com) in the channel [#vscode](https://robotframework.slack.com/archives/C0103745J7P) or in the [Robot Framework Forum](https://forum.robotframework.org) in the [Tools/Visual Studio Code(ium)](https://forum.robotframework.org/c/tools/vscode/28) category.
  - for questions about the IntelliJ plugin there are also channels for PyCharm
- Also make sure to search the internet (including Stack Overflow) to see if users outside of the GitHub community have discussed the issue.
- Collect information about the bug:
  - Stack trace (Traceback)
  - OS, Platform and Version (Windows, Linux, macOS, x86, ARM)
  - Version of the interpreter, compiler, SDK, runtime environment, package manager, depending on what seems relevant.
  - Possibly your input and the output
  - Can you reliably reproduce the issue? And can you also reproduce it with older versions?

<!-- omit in toc -->
#### How Do I Submit a Good Bug Report?

> [!WARNING]
> Never report security related issues, vulnerabilities or bugs including sensitive information to the issue tracker, or elsewhere in public. Send sensitive bugs by email to <support@robotcode.io> instead.

We use GitHub issues to track bugs and errors. If you run into an issue with the project:

- Open an [Issue](https://github.com/robotcodedev/robotcode/issues/new). (Since we can't be sure at this point whether it is a bug or not, we ask you not to talk about a bug yet and not to label the issue.)
- Explain the behavior you would expect and the actual behavior.
- Please provide as much context as possible and describe the *reproduction steps* that someone else can follow to recreate the issue on their own. This usually includes your code. For good bug reports you should isolate the problem and create a reduced test case.
- Provide the information you collected in the previous section.

Once it's filed:

- The project team will label the issue accordingly.
- A team member will try to reproduce the issue with your provided steps. If there are no reproduction steps or no obvious way to reproduce the issue, the team will ask you for those steps and mark the issue as `needs-repro`. Bugs with the `needs-repro` tag will not be addressed until they are reproduced.
- If the team is able to reproduce the issue, it will be marked `needs-fix`, as well as possibly other tags (such as `critical`), and the issue will be left to be [implemented by someone](#your-first-code-contribution).

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion for RobotCode, **including completely new features and minor improvements to existing functionality**. Following these guidelines will help maintainers and the community to understand your suggestion and find related suggestions.

<!-- omit in toc -->
#### Before Submitting an Enhancement

- Make sure that you are using the latest version.
- Read the [documentation](https://robotcode.io) carefully and find out if the functionality is already covered, maybe by an individual configuration.
- Perform a [search](https://github.com/robotcodedev/robotcode/issues) to see if the enhancement has already been suggested. If it has, add a comment to the existing issue instead of opening a new one.
- Find out whether your idea fits with the scope and aims of the project. It's up to you to make a strong case to convince the project's developers of the merits of this feature. Keep in mind that we want features that will be useful to the majority of our users and not just a small subset. If you're just targeting a minority of users, consider writing an add-on/plugin library.

<!-- omit in toc -->
#### How Do I Submit a Good Enhancement Suggestion?

Enhancement suggestions are tracked as [GitHub issues](https://github.com/robotcodedev/robotcode/issues).

- Use a **clear and descriptive title** for the issue to identify the suggestion.
- Provide a **step-by-step description of the suggested enhancement** in as many details as possible.
- **Describe the current behavior** and **explain which behavior you expected to see instead** and why. At this point you can also tell which alternatives do not work for you.
- You may want to **include screenshots and animated GIFs** which help you demonstrate the steps or point out the part which the suggestion is related to.
- **Explain why this enhancement would be useful** to most RobotCode users. You may also want to point out the other projects that solved it better and which could serve as inspiration.

### Your First Code Contribution

Welcome to your first code contribution! Here's how to set up your development environment and get started.

#### Development Environment Setup

**Option 1: Using GitHub Codespaces (Easiest)**

The quickest way to get started without any local setup:

1. Go to the [RobotCode repository](https://github.com/robotcodedev/robotcode).
2. Click the green "Code" button.
3. Select the "Codespaces" tab.
4. Click "Create codespace on main".
5. Wait for the codespace to initialize — it uses the same dev container configuration as Option 2.

GitHub Codespaces provides a full VS Code environment in your browser with all dependencies pre-installed.

**Option 2: Using Dev Container (Local)**

For local development with containers:

1. **Prerequisites** (see each project's site for install instructions):
   - [Docker](https://www.docker.com/get-started)
   - [Visual Studio Code](https://code.visualstudio.com/)
   - [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) for VS Code

2. **Setup:**
   - Clone the repository: `git clone https://github.com/robotcodedev/robotcode.git`.
   - Open the project in VS Code.
   - When prompted, click "Reopen in Container" — or use the Command Palette (`Cmd+Shift+P` / `Ctrl+Shift+P`) and run "Dev Containers: Reopen in Container".
   - The container automatically installs all dependencies (Python, Node.js, etc.).

**Option 3: Local Development**

If you prefer to set up locally:

1. **Prerequisites** (see each project's site for install instructions):
   - [Python](https://www.python.org/) (system Python is fine)
   - [Node.js](https://nodejs.org/)
   - [Git](https://git-scm.com/)
   - [Hatch](https://hatch.pypa.io/latest/install/)

   Supported Python and Node.js versions are declared in [`pyproject.toml`](pyproject.toml) and [`package.json`](package.json) respectively. Hatch will tell you if your interpreter is too old when you create the dev environment.

2. **Setup:**
   ```bash
   git clone https://github.com/robotcodedev/robotcode.git
   cd robotcode
   hatch env create devel
   hatch run build:install-bundled-editable   # bundled packages for VS Code / IntelliJ packaging
   npm install --also-dev                     # Node.js deps for the extension and docs
   ```

#### IDE Configuration

The project includes VS Code settings optimized for development:
- Python testing with pytest
- Code formatting with Prettier and Ruff
- Type checking with mypy
- Debugging configuration
- Recommended extensions are automatically suggested

> [!IMPORTANT]
> After setting up the development environment with `hatch env create devel`, you need to select the correct Python interpreter in VS Code:
>
> 1. Open the Command Palette (`Cmd+Shift+P` or `Ctrl+Shift+P` or `F1`).
> 2. Type "Python: Select Interpreter".
> 3. Choose the interpreter from the Hatch environment.
> 4. Select the desired Python/Robot Framework version environment.

Hatch creates separate Python environments for each supported Python/Robot Framework version combination in your system's cache directory. See [Running Tests](#running-tests) for how to list and locate them with `hatch env show` and `hatch env find`.

#### Pre-commit Hooks

The project ships a [`.pre-commit-config.yaml`](.pre-commit-config.yaml) that runs the same checks CI enforces, locally and automatically before every commit/push:

- Conventional Commits check on the commit message
- Python style (`hatch run lint:style`) and typing (`hatch run lint:typing`)
- JavaScript/TypeScript lint (`npm run lint`)

We strongly recommend installing the hooks once — they catch most lint/format/commit-message issues before CI does. Install [pre-commit](https://pre-commit.com/#install), then from the repo root:

```bash
pre-commit install --install-hooks
```

This installs the `pre-commit`, `commit-msg` and `pre-push` hooks. To run all hooks manually against the whole repo: `pre-commit run --all-files`.

#### Development Workflow

1. **Create a branch:** `git checkout -b feature/your-feature-name`
2. **Make your changes** following the project's coding standards
3. **Run tests:** `hatch run test:test` (runs the full test suite against all supported Robot Framework versions with the default Python — run this before committing or pushing, not only the tests you added or changed)
4. **Run linting:** `hatch run lint:all` (or use the VS Code task) — the [pre-commit hooks](#pre-commit-hooks) run style and typing checks automatically if installed
5. **Fix linting issues:** `hatch run lint:style` for formatting
6. **Commit your changes** with a descriptive commit message
7. **Push and create a pull request**

#### Pull Request Guidelines

When you open a pull request, GitHub will pre-fill the [pull request template](.github/PULL_REQUEST_TEMPLATE.md). Please keep its checklist intact and tick the boxes that apply.

##### PR Checklist

Before submitting your pull request, make sure that:

- [ ] The change is **focused** on a single concern (no unrelated refactors or formatting noise).
- [ ] **Tests** for the change have been added or updated, and `hatch run test:test` passes locally (RF matrix against the default Python). See [Running Tests](#running-tests) for faster iteration options and the full matrix.
- [ ] **Linting** passes: `hatch run lint:all` (also enforced by the [pre-commit hooks](#pre-commit-hooks) if installed).
- [ ] **Documentation** has been updated where relevant (user docs, code comments, README).
- [ ] **Generated files** (if any) were regenerated with the documented script, not edited by hand.
- [ ] **Commits** follow [Conventional Commits](#commit-messages) and are [cryptographically signed](#signed-commits-required) (`git commit -S`, GPG/SSH).
- [ ] **AI / tooling disclosure** is included if AI tools or automated agents were used for a substantial part of the change (see [AI_POLICY.md](AI_POLICY.md)).
- [ ] No payment, bounty, or monetization requests are attached (see [Payment, Bounty, and Monetization Requests](#payment-bounty-and-monetization-requests)).

##### PR Description

A good PR description:
- Explains **what** changed and **why**.
- References any related issues (e.g. `Fixes #123`).
- Includes screenshots for UI changes.
- Lists any breaking changes explicitly.

##### PR Review Process

- Automated checks must pass (tests, linting, etc.).
- At least one maintainer review is required.
- Address feedback promptly.
- Keep your PR up to date with the main branch.

#### Running Tests

**Recommended default:**

```bash
hatch run test:test
```

This runs the full test suite across all supported Robot Framework versions using the default Python interpreter. Run it before committing or pushing a change, even if you already ran the newly added or modified tests locally: it gives good coverage without spinning up the full Python × RF matrix.

**Fast iteration during development:**

Run a single Robot Framework version:

```bash
hatch run test.<rf-env>:test      # e.g. hatch run test.rf74:test
```

For running individual tests or test files interactively, use VS Code's built-in test runner (Testing tab in the sidebar) — it's the most convenient way to iterate on a single test or debug a failure.

**Full Python × RF matrix (CI-style, slow):**

```bash
hatch run devel:test                       # all combinations in the matrix
hatch run devel.<py-env>-<rf-env>:test     # e.g. hatch run devel.py3.12-rf74:test
```

Only use this when you suspect a Python-version-specific issue — it is significantly slower than `test:test`.

**Discovering available environments:**

Run `hatch env show` to list every environment, including the `test.*` and `devel.*` matrix combinations and their Python/Robot Framework versions. Use `hatch env find <env-name>` to print the interpreter path for a specific env.

> [!NOTE]
> `hatch run test` (without an env prefix) runs only in the `default` environment against the Robot Framework version pinned there — it does **not** cover the RF matrix. Use `hatch run test:test` for the full RF matrix, or `hatch run devel:test` for the full Python × RF matrix (slow).

#### Additional Development Commands

These commands are mainly used by maintainers, but contributors may need some of them when working on specific features (e.g., syntax-highlighting changes require `generate-tmlanguage`).

**Code Quality & Linting:**
- `hatch run lint:typing` — Type checking with mypy.
- `hatch run lint:style` — Code style check and formatting.
- `hatch run lint:all` — Run all linting checks.

**Code Generation:**
- `hatch run generate-tmlanguage` — Regenerate VS Code syntax-highlighting files for Robot Framework.
- `hatch run create-json-schema` — Create JSON schema for `robot.toml` configuration validation.

**Build & Release:**
- `hatch run build:install-bundled-editable` — Install bundled packages in editable mode.
- `hatch run build:sync-chat-plugin` — Refresh the bundled chat-plugin under `chat-plugins/robotcode/` from a local clone of [robotframework-agent-plugins](https://github.com/robotcodedev/robotframework-agent-plugins) (source of truth; expects the clone as a sibling directory or pass `--source <path>`). Add `--check` to verify the mirror without writing.
- `hatch run build:update-changelog` — Update project changelog.
- `hatch run build:update-git-versions` — Update version information from git.
- `hatch run build:update-doc-links` — Update documentation links.
- `hatch run build:bump [major|minor|patch]` — Bump project version using semantic versioning.
- `hatch run build:package` — Package for distribution.
- `hatch run build:publish` — Publish to PyPI, VS Code Marketplace, etc. (requires the specific credentials set up in your environment).

#### Troubleshooting Development Setup

**Common Issues:**

1. **Hatch environment creation fails:**
   ```bash
   # Clear Hatch cache and try again
   hatch env prune
   hatch env create devel
   ```

2. **VS Code doesn't find the Python interpreter:**
   - Use `hatch env find devel` to get the exact path
   - Manually select the interpreter in VS Code using this path

3. **Tests fail with import errors:**
   - Ensure you're in the correct hatch environment
   - Run `hatch run build:install-bundled-editable` to install development packages

4. **Node.js dependencies issues:**
   ```bash
   # Clean and reinstall npm dependencies
   rm -rf node_modules package-lock.json
   npm install --also-dev
   ```

### Improving The Documentation

Documentation is crucial for helping users understand and use RobotCode effectively. Here are ways you can help improve it:

#### Types of Documentation Contributions

1. **User Documentation** (`docs/` folder)
   - Getting started guides
   - Feature explanations
   - Configuration examples
   - Troubleshooting guides

2. **Code Documentation**
   - Docstrings for classes and functions
   - Inline comments for complex logic
   - Type hints and annotations

3. **README Updates**
   - Installation instructions
   - Quick start examples
   - Feature highlights

#### Documentation Setup

The documentation is built using modern web technologies and is located in the `docs/` folder. Node.js dependencies are already installed by the [dev environment setup](#development-environment-setup):

```bash
npm run docs:dev      # Start documentation development server
npm run docs:build    # Build documentation for production
npm run docs:preview  # Preview production documentation build
```

You can also run the equivalent commands from the `docs/` folder: `npm run dev`, `npm run build`, and `npm run preview`.

#### Documentation Standards

- **Clear and concise:** Write for users of all skill levels
- **Examples:** Include practical code examples
- **Screenshots:** Add visual aids where helpful (stored in `docs/images/`)
- **Links:** Reference related concepts and external resources
- **Testing:** Verify that code examples actually work

#### Making Documentation Changes

1. **Small fixes:** Edit files directly and submit a pull request
2. **Major changes:** Open an issue first to discuss the approach
3. **New sections:** Follow the existing structure in the `docs/` folder
4. **Images:** Store in `docs/images/` and use relative paths

#### Documentation Review Process

- All documentation changes go through the same review process as code
- Maintainers will check for accuracy, clarity, and consistency
- Community feedback is encouraged on documentation pull requests

## Styleguides
### Commit Messages

Good commit messages help maintain a clean project history and make it easier to understand changes. Please follow these guidelines:

#### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

#### Types

- **feat:** A new feature
- **fix:** A bug fix
- **docs:** Documentation only changes
- **style:** Changes that do not affect the meaning of the code (white-space, formatting, etc)
- **refactor:** A code change that neither fixes a bug nor adds a feature
- **perf:** A code change that improves performance
- **test:** Adding missing tests or correcting existing tests
- **chore:** Changes to the build process or auxiliary tools and libraries

#### Scope

The scope should indicate the package or area affected:
- **core:** Core functionality
- **language-server:** Language server features
- **debugger:** Debugging functionality
- **runner:** Test runner
- **analyze:** Code analysis
- **plugin:** Plugin system
- **docs:** Documentation
- **vscode:** VS Code extension

#### Examples

```
feat(language-server): add auto-completion for robot keywords

Add intelligent auto-completion that suggests Robot Framework
keywords based on imported libraries and current context.

Closes #123
```

```
fix(debugger): resolve breakpoint not hit in nested keywords

Fixed an issue where breakpoints in nested keywords were not
being triggered during debugging sessions.

Fixes #456
```

```
docs(contributing): update development setup instructions

Updated the contributing guide to include dev container setup
and improved local development instructions.
```

#### Guidelines

- **Subject line:** 50 characters or less, imperative mood ("add" not "added")
- **Body:** Wrap at 72 characters, explain what and why (not how)
- **Footer:** Reference issues and breaking changes
- **Breaking changes:** Start footer with "BREAKING CHANGE:" followed by description

#### Signed Commits Required

**All commits and pull requests must be signed** to be accepted into the project. This helps ensure the authenticity and integrity of the codebase.

This refers to the **cryptographic commit signature** (`git commit -S`, GPG/SSH/X.509) — not to be confused with the DCO `Signed-off-by` trailer (`git commit -s`) mentioned in the [Legal Notice](#i-want-to-contribute).

**Setting up commit signing:**
- Follow GitHub's guide: [Managing commit signature verification](https://docs.github.com/en/authentication/managing-commit-signature-verification)
- Configure Git to sign commits automatically: `git config --global commit.gpgsign true`
- Verify your commits are signed: `git log --show-signature`

**For pull requests:**
- All commits in the PR must be signed
- The PR will be automatically blocked if unsigned commits are detected
- You can sign previous commits using: `git rebase --exec 'git commit --amend --no-edit -S' -i HEAD~<number-of-commits>`

## Join The Project Team

We're always looking for dedicated contributors to join the RobotCode project team! If you've been actively contributing and are interested in taking on more responsibility, here's how you can get involved:

### Ways to Get More Involved

**Regular Contributors:**
- Consistently submit high-quality pull requests
- Help with code reviews and testing
- Assist in triaging and responding to issues
- Contribute to documentation improvements

**Maintainer Responsibilities:**
- Review and merge pull requests
- Manage releases and versioning
- Guide project direction and roadmap
- Mentor new contributors

### How to Apply

If you're interested in joining the project team:

1. **Build a track record** of meaningful contributions over time
2. **Engage with the community** by helping other users and contributors
3. **Reach out** to existing maintainers via email at <support@robotcode.io>
4. **Express your interest** in specific areas where you'd like to contribute more

### What We Look For

- **Technical expertise** in relevant areas (Python, Robot Framework, VS Code extensions)
- **Communication skills** for working with contributors and users
- **Reliability** in following through on commitments
- **Collaborative mindset** and willingness to help others
- **Alignment** with project goals and values

We value diversity and welcome contributors from all backgrounds. The RobotCode project benefits from different perspectives and experiences.
