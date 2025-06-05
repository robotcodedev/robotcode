<!-- omit in toc -->
# Contributing to robotcode

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
- [I Want To Contribute](#i-want-to-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Enhancements](#suggesting-enhancements)
  - [Your First Code Contribution](#your-first-code-contribution)
    - [Development Environment Setup](#development-environment-setup)
    - [IDE Configuration](#ide-configuration)
    - [Development Workflow](#development-workflow)
    - [Pull Request Guidelines](#pull-request-guidelines)
    - [Running Tests](#running-tests)
    - [Building the Project](#building-the-project)
    - [Additional Development Commands](#additional-development-commands)
    - [Troubleshooting Development Setup](#troubleshooting-development-setup)
    - [Development Tools & Code Generation](#development-tools--code-generation)
  - [Improving The Documentation](#improving-the-documentation)
- [Styleguides](#styleguides)
  - [Commit Messages](#commit-messages)
- [Join The Project Team](#join-the-project-team)


## Code of Conduct

This project and everyone participating in it is governed by the
[robotcode Code of Conduct](https://github.com/robotcodedev/robotcode/blob/master/CODE_OF_CONDUCT.md).
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

<!--
You might want to create a separate issue tag for questions and include it in this description. People should then tag their issues accordingly.

Depending on how large the project is, you may want to outsource the questioning, e.g. to Stack Overflow or Gitter. You may add additional contact and information possibilities:
- IRC
- Slack
- Gitter
- Stack Overflow tag
- Blog
- FAQ
- Roadmap
- E-Mail List
- Forum
-->

## I Want To Contribute

> ### Legal Notice <!-- omit in toc -->
> When contributing to this project, you must agree that you have authored 100% of the content, that you have the necessary rights to the content and that the content you contribute may be provided under the project license.

### Reporting Bugs

<!-- omit in toc -->
#### Before Submitting a Bug Report

A good bug report shouldn't leave others needing to chase you up for more information. Therefore, we ask you to investigate carefully, collect information and describe the issue in detail in your report. Please complete the following steps in advance to help us fix any potential bug as fast as possible.

- Make sure that you are using the latest version.
- Determine if your bug is really a bug and not an error on your side e.g. using incompatible environment components/versions (Make sure that you have read the [documentation](https://robotcode.io). If you are looking for support, you might want to check [this section](#i-have-a-question)).
- To see if other users have experienced (and potentially already solved) the same issue you are having, check if there is not already a bug report existing for your bug or error in the [bug tracker](https://github.com/robotcodedev/robotcode/issues?q=label%3Abug).
- Look or ask in the [Robot Framework Slack](https://robotframework.slack.com) in the channel [#vscode](https://robotframework.slack.com/archives/C0103745J7P) or in the [Robot Framework Forum](https://forum.robotframework.org) in the [Tools/Visual Studio Code(ium)](https://forum.robotframework.org/c/tools/vscode/28) category to see if other users have experienced (and potentially already solved) the same issue you are having.
  - for questions about the intellj plugin there are also channels for pycharm
- Also make sure to search the internet (including Stack Overflow) to see if users outside of the GitHub community have discussed the issue.
- Collect information about the bug:
  - Stack trace (Traceback)
  - OS, Platform and Version (Windows, Linux, macOS, x86, ARM)
  - Version of the interpreter, compiler, SDK, runtime environment, package manager, depending on what seems relevant.
  - Possibly your input and the output
  - Can you reliably reproduce the issue? And can you also reproduce it with older versions?

<!-- omit in toc -->
#### How Do I Submit a Good Bug Report?

> You must never report security related issues, vulnerabilities or bugs including sensitive information to the issue tracker, or elsewhere in public. Instead sensitive bugs must be sent by email to <support@robotcode.io>.
<!-- You may add a PGP key to allow the messages to be sent encrypted as well. -->

We use GitHub issues to track bugs and errors. If you run into an issue with the project:

- Open an [Issue](https://github.com/robotcodedev/robotcode/issues/new). (Since we can't be sure at this point whether it is a bug or not, we ask you not to talk about a bug yet and not to label the issue.)
- Explain the behavior you would expect and the actual behavior.
- Please provide as much context as possible and describe the *reproduction steps* that someone else can follow to recreate the issue on their own. This usually includes your code. For good bug reports you should isolate the problem and create a reduced test case.
- Provide the information you collected in the previous section.

Once it's filed:

- The project team will label the issue accordingly.
- A team member will try to reproduce the issue with your provided steps. If there are no reproduction steps or no obvious way to reproduce the issue, the team will ask you for those steps and mark the issue as `needs-repro`. Bugs with the `needs-repro` tag will not be addressed until they are reproduced.
- If the team is able to reproduce the issue, it will be marked `needs-fix`, as well as possibly other tags (such as `critical`), and the issue will be left to be [implemented by someone](#your-first-code-contribution).

<!-- You might want to create an issue template for bugs and errors that can be used as a guide and that defines the structure of the information to be included. If you do so, reference it here in the description. -->


### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion for robotcode, **including completely new features and minor improvements to existing functionality**. Following these guidelines will help maintainers and the community to understand your suggestion and find related suggestions.

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
- You may want to **include screenshots and animated GIFs** which help you demonstrate the steps or point out the part which the suggestion is related to. <!-- this should only be included if the project has a GUI -->
- **Explain why this enhancement would be useful** to most robotcode users. You may also want to point out the other projects that solved it better and which could serve as inspiration.

<!-- You might want to create an issue template for enhancement suggestions that can be used as a guide and that defines the structure of the information to be included. If you do so, reference it here in the description. -->

### Your First Code Contribution

Welcome to your first code contribution! Here's how to set up your development environment and get started.

#### Development Environment Setup

**Option 1: Using GitHub Codespaces (Easiest)**

The quickest way to get started without any local setup:

1. **Setup:**
   - Go to the [robotcode repository](https://github.com/robotcodedev/robotcode)
   - Click the green "Code" button
   - Select "Codespaces" tab
   - Click "Create codespace on main"
   - Wait for the codespace to initialize (this uses the same dev container configuration)

GitHub Codespaces provides a full VS Code environment in your browser with all dependencies pre-installed.

**Option 2: Using Dev Container (Local)**

For local development with containers:

1. **Prerequisites:**
   - Install [Docker](https://www.docker.com/get-started)
   - Install [Visual Studio Code](https://code.visualstudio.com/)
   - Install the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

2. **Setup:**
   - Clone the repository: `git clone https://github.com/robotcodedev/robotcode.git`
   - Open the project in VS Code
   - When prompted, click "Reopen in Container" or use the Command Palette (`Cmd+Shift+P` / `Ctrl+Shift+P`) and select "Dev Containers: Reopen in Container"
   - The container will automatically install all dependencies including Python, Node.js, and required packages

**Option 3: Local Development**

If you prefer to set up locally:

1. **Prerequisites:**
   - Python 3.8+ (system Python is fine)
   - Node.js 16+
   - Git

2. **Setup:**
   ```bash
   git clone https://github.com/robotcodedev/robotcode.git
   cd robotcode

   # Install Hatch (choose one method):
   # Option A: Using system package manager (if available)
   # Ubuntu/Debian: sudo apt install hatch
   # Fedora: sudo dnf install hatch
   # Arch: sudo pacman -S hatch

   # Option B: Using pipx (recommended if not in package manager)
   pip install pipx
   pipx install hatch

   # Option C: Check https://hatch.pypa.io/latest/install/ for other methods

   # Create development environment
   hatch env create devel

   # install needed packages for the vscode and intellij packaging
   hatch run build:install-bundled-editable

   # Install Node.js dependencies
   npm install --also-dev
   ```

#### IDE Configuration

The project includes VS Code settings optimized for development:
- Python testing with pytest
- Code formatting with Prettier and Ruff
- Type checking with mypy
- Debugging configuration
- Recommended extensions are automatically suggested

**Important: Python Interpreter Selection**

After setting up the development environment with `hatch env create devel`, you need to select the correct Python interpreter in VS Code:

1. Open the Command Palette (`Cmd+Shift+P` or `Ctrl+Shift+P` or `F1`)
2. Type "Python: Select Interpreter"
3. Choose the interpreter from the Hatch environment
4. Select the desired Python/Robot Framework version environment

Hatch creates separate Python environments for each supported Python/Robot Framework version combination in your system's cache directory.

You can also check available environments with: `hatch env show`

#### Development Workflow

1. **Create a branch:** `git checkout -b feature/your-feature-name`
2. **Make your changes** following the project's coding standards
3. **Run tests:** `hatch run devel.py312-rf73:test` (single combination for faster development)
4. **Run linting:** `hatch run lint:all` (or use the VS Code task)
5. **Fix linting issues:** `hatch run lint:style` for formatting
6. **Commit your changes** with a descriptive commit message
7. **Push and create a pull request**

#### Pull Request Guidelines

Before submitting your pull request:

1. **Ensure all tests pass:** Run `hatch run test.rf73:test` (or your preferred combination)
2. **Check linting:** Run `hatch run lint:all` and fix any issues
3. **Write descriptive PR description:**
   - Explain what changes you made and why
   - Reference any related issues
   - Include screenshots for UI changes
   - List any breaking changes
4. **Keep PRs focused:** One feature/fix per PR when possible
5. **Update documentation:** Include relevant documentation updates
6. **Sign your commits:** All commits must be signed (see [Signed Commits](#signed-commits-required))

**PR Review Process:**
- Automated checks must pass (tests, linting, etc.)
- At least one maintainer review is required
- Address any feedback promptly
- Keep your PR up to date with the main branch

#### Running Tests

**Basic Test Execution:**
- Use VS Code's built-in test runner (Testing tab in the sidebar)
- Or run from terminal: `hatch run test` (⚠️ **Warning**: This runs tests against ALL Python/Robot Framework combinations in the matrix - can take a very long time!)
- Run specific tests: `hatch run test tests/specific_test.py` (also runs against all matrix combinations)

**Testing with Specific Python/Robot Framework Versions:**

The project supports multiple Python and Robot Framework versions. You can run tests against specific combinations:

```bash
# Run tests with specific Robot Framework versions (single combination)
hatch run test:test          # ⚠️ Runs ALL matrix combinations (RF 4.1-7.3)
hatch run test.rf70:test      # Robot Framework 7.0.x
hatch run test.rf71:test      # Robot Framework 7.1.x
hatch run test.rf72:test      # Robot Framework 7.2.x
hatch run test.rf73:test      # Robot Framework 7.3.x (recommended for development)
hatch run test.rf61:test      # Robot Framework 6.1.x
hatch run test.rf60:test      # Robot Framework 6.0.x
hatch run test.rf50:test      # Robot Framework 5.0.x
hatch run test.rf41:test      # Robot Framework 4.1.x

# Run tests in specific development environments (single combination)
hatch run devel:test          # ⚠️ Runs ALL matrix combinations (Python 3.8-3.13 × RF 4.1-7.3)
hatch run devel.py39-rf73:test  # Python 3.9 with Robot Framework 7.3.x (single combination)
hatch run devel.py311-rf70:test # Python 3.11 with Robot Framework 7.0.x (single combination)
hatch run devel.py312-rf73:test # Python 3.12 with Robot Framework 7.3.x (single combination)
hatch run devel.py313-rf73:test # Python 3.13 with Robot Framework 7.3.x (single combination)

# Test against development versions of Robot Framework
hatch run rfbeta:test         # Robot Framework beta/RC versions
hatch run rfmaster:test       # Robot Framework master branch
hatch run rfdevel:test        # Local Robot Framework development version
```

**⚠️ Important Matrix Behavior:**
- `hatch run test` executes tests for **all combinations** in the matrix (48 combinations: 6 Python versions × 8 RF versions)
- `hatch run devel:test` also runs **all matrix combinations**
- For faster development, use specific combinations like `hatch run devel.py312-rf73:test`
- For CI/full testing, use the matrix commands

**Available Environment Matrix:**
- **Python versions**: 3.8, 3.9, 3.10, 3.11, 3.12, 3.13
- **Robot Framework versions**: 4.1.x, 5.0.x, 6.0.x, 6.1.x, 7.0.x, 7.1.x, 7.2.x, 7.3.x

#### Building the Project

- Package for distribution: `hatch run build:package`

#### Additional Development Commands

**Code Quality & Linting:**
- Type checking: `hatch run lint:typing`
- Code style check and formatting: `hatch run lint:style`
- Run all linting checks: `hatch run lint:all`

**Project Maintenance & Code Generation:**
- Generate Robot Framework syntax files: `hatch run generate-tmlanguage`
- Create JSON schema for robot.toml: `hatch run create-json-schema`
- Generate Robot Framework options: `hatch run generate-rf-options`
- Install bundled packages in editable mode: `hatch run build:install-bundled-editable`

**Release & Documentation:**
- Update changelog: `hatch run build:update-changelog`
- Update git versions: `hatch run build:update-git-versions`
- Bump version: `hatch run build:bump [major|minor|patch]`
- Package for distribution: `hatch run build:package`
- Publish to PyPI, VS Code Marketplace, etc.: `hatch run build:publish`
  - you need the specific credentials set up in your environment for this to work

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

#### Development Tools & Code Generation

The robotcode project includes several development tools and code generation scripts:

**Syntax & Language Support:**
- `hatch run generate-tmlanguage` - Regenerate VS Code syntax highlighting files for Robot Framework
- `hatch run create-json-schema` - Create JSON schema for robot.toml configuration validation
- `hatch run generate-rf-options` - Generate Robot Framework command-line options documentation

**Maintenance & Release Tools:**
- `hatch run build:update-changelog` - Update project changelog
- `hatch run build:update-git-versions` - Update version information from git
- `hatch run build:update-doc-links` - Update documentation links
- `hatch run build:bump [major|minor|patch]` - Bump project version using semantic versioning

These tools are typically used by maintainers, but contributors might need some of them when working on specific features (e.g., syntax highlighting changes require `generate-tmlanguage`).

### Improving The Documentation

Documentation is crucial for helping users understand and use robotcode effectively. Here are ways you can help improve it:

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

The documentation is built using modern web technologies and is located in the `docs/` folder:

```bash
cd docs
npm install
npm run dev  # Start development server at http://localhost:3000
npm run build  # Build for production
npm run preview  # Preview production build
```

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

**Setting up commit signing:**
- Follow GitHub's guide: [Managing commit signature verification](https://docs.github.com/en/authentication/managing-commit-signature-verification)
- Configure Git to sign commits automatically: `git config --global commit.gpgsign true`
- Verify your commits are signed: `git log --show-signature`

**For pull requests:**
- All commits in the PR must be signed
- The PR will be automatically blocked if unsigned commits are detected
- You can sign previous commits using: `git rebase --exec 'git commit --amend --no-edit -S' -i HEAD~<number-of-commits>`

## Join The Project Team

We're always looking for dedicated contributors to join the robotcode project team! If you've been actively contributing and are interested in taking on more responsibility, here's how you can get involved:

#### Ways to Get More Involved

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

#### How to Apply

If you're interested in joining the project team:

1. **Build a track record** of meaningful contributions over time
2. **Engage with the community** by helping other users and contributors
3. **Reach out** to existing maintainers via email at <support@robotcode.io>
4. **Express your interest** in specific areas where you'd like to contribute more

#### What We Look For

- **Technical expertise** in relevant areas (Python, Robot Framework, VS Code extensions)
- **Communication skills** for working with contributors and users
- **Reliability** in following through on commitments
- **Collaborative mindset** and willingness to help others
- **Alignment** with project goals and values

We value diversity and welcome contributors from all backgrounds. The robotcode project benefits from different perspectives and experiences.

<!-- omit in toc -->
## Attribution
This guide is based on the **contributing-gen**. [Make your own](https://github.com/bttger/contributing-gen)!
