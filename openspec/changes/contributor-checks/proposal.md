# Proposal

## Why

The pre-commit hooks run ESLint on the TypeScript sources, but the CI does not, although CONTRIBUTING.md says that the hooks run "the same checks CI enforces". A pull request from a contributor without the hooks can bring ESLint errors, including the Prettier formatting that ESLint checks, into `main` unnoticed.

The dev container, which GitHub Codespaces also uses and which CONTRIBUTING.md offers as the easiest start, installs neither a JDK nor xvfb. The contribution guide now asks for the tests of every changed part, also the VS Code extension's (`npm test`, under `xvfb-run` on Linux without a display) and the PyCharm plugin's (`./gradlew test`, which needs a JDK). A contributor in the container or in a Codespace cannot run them.

## What Changes

- The `code-quality` job of the CI runs `npm run lint`, the same command as the pre-commit hook, next to `hatch run lint:style` and `hatch run lint:typing`. An ESLint error fails the job.
- The dev container installs a JDK 21 and xvfb with the libraries that VS Code needs to start, so that `./gradlew test` and `xvfb-run -a npm test` run in it and in Codespaces.
- CONTRIBUTING.md lists ESLint among the CI's checks, names `npm run lint` for the VS Code extension in the development workflow and in the PR checklist, and names the JDK and xvfb among the dev container's tools. The PR template's linting line names `npm run lint` as well.

Not part of this change:
- checking commit messages in the CI; the commit-msg hook stays the only check;
- a linter for the Kotlin sources;
- the unused `.devcontainer/Dockerfile`;
- starting an IDE in the container (`./gradlew runIde`, "Run Extension"), which needs a desktop;
- packaging in the container.

## Capabilities

### New Capabilities

- `development-container`: what the repository's dev container, and with it GitHub Codespaces, provides for working on RobotCode, starting with the tools that every test suite needs.

### Modified Capabilities

- `continuous-integration`: the code-quality checks also run ESLint.

## Impact

- `.github/workflows/build-test-package.yml`: one step in `code-quality`, which already installs Node.js and the npm dependencies. `npm run lint` takes about 2 seconds locally and finds nothing on `main` (2026-10-23).
- `.devcontainer/devcontainer.json`: the feature `ghcr.io/devcontainers/features/java:1` and more packages in the `apt install` of `postCreateCommand`. Creating a container takes longer, and the first `./gradlew test` downloads PyCharm, as on any other machine.
- `CONTRIBUTING.md`, `.github/PULL_REQUEST_TEMPLATE.md`.
