# Design

## Context

See proposal.md for the motivation.

**The CI's code-quality job** (`.github/workflows/build-test-package.yml`, `code-quality`):
- runs on Ubuntu;
- sets up Node.js 26 with the newest npm, runs `npm install --include=dev`, and sets up Python 3.10, Hatch, Java 21 and Gradle;
- then runs `hatch run lint:style`, `hatch run lint:typing` and the two plugin verifier steps, each with `if: always()`.

So Node.js and the npm dependencies are already installed there, and nothing runs ESLint.

**ESLint:**
- The pre-commit hook `eslint` runs `npm run lint` (`eslint .`) for every commit that stages JavaScript or TypeScript files. With `pass_filenames: false`, it lints the whole repository.
- `eslint.config.mjs` ignores `docs/`, `packages/`, `intellij-client/`, the build output and `.vscode-test/`. It applies typescript-eslint's recommended rules and Prettier through `eslint-plugin-prettier`, so formatting differences are ESLint errors.
- On 2026-10-23, `npm run lint` found nothing on `main` and took about 2 seconds.

**The dev container** (`.devcontainer/devcontainer.json`), also used by Codespaces:
- the image `mcr.microsoft.com/devcontainers/base:jammy` (Ubuntu 22.04);
- the features `common-utils`, `node` and `python` (`os-provided`, Python 3.10 on jammy);
- `postCreateCommand`: `apt update`, `apt upgrade`, `apt install gdb`, `npm install --also-dev`, `pipx install hatch`, `hatch env create devel`.

There is no JDK and no X server. `.devcontainer/Dockerfile`, an Arch Linux image, is not referenced by `devcontainer.json`.

**What the test suites need:**
- **PyCharm plugin:** the Gradle wrapper (Gradle 9.8.0) needs a JVM to start. The build uses `jvmToolchain(21)`, and the CI uses Java 21.
- **VS Code extension:**
  - `npm test` downloads VS Code and the extensions `ms-python.python` and `ms-python.debugpy` into `.vscode-test/`;
  - on Linux, VS Code needs a display;
  - the run terminal's tests need `python3` 3.10 or newer, which jammy has;
  - the CI's Ubuntu runners have the libraries that VS Code needs. The VS Code documentation's GitLab CI example (Continuous Integration page) installs `libasound2 libgbm1 libgtk-3-0 libnss3 xvfb` for a container.

## Goals / Non-Goals

**Goals:**

- One command for ESLint everywhere: the hook, the CI and the contribution guide all name `npm run lint`.
- A dev container, and with it a Codespace, in which all three test suites run right after it is created.

**Non-Goals:**

- Running the CI's jobs in the dev container. The CI keeps its runners, and the container is not built in the CI.
- `hatch run build:package` in the container: `scripts/package.py` calls `gradle buildPlugin`, not the wrapper, and the container gets no Gradle of its own.

## Decisions

### ESLint as a step of the code-quality job

`- run: npm run lint` with `if: always()` directly after `hatch run lint:typing`. It is the same command as the hook, without extra flags, so the hook and the CI cannot diverge. With `if: always()`, a failed Python check does not hide an ESLint finding, as for the steps before it.

Alternatives:
- A job of its own costs a checkout and an `npm install` for a check of about 2 seconds.
- A step in `test-vscode` would run six times, once per operating system and VS Code version, and would mix lint failures with test failures.

### The JDK from the dev container feature `java`

`"ghcr.io/devcontainers/features/java:1": { "version": "21" }`. The feature installs the newest Java 21 through SDKMAN, by default the Microsoft Build of OpenJDK, as the container's default `java`. Version 21 is the build's toolchain, so Gradle neither looks for nor downloads another JDK. The feature installs no Gradle (`installGradle` defaults to `false`), so the wrapper stays the only Gradle in the container.

Alternatives:
- The JetBrains Runtime, as in the CI: no feature provides it, so `postCreateCommand` would have to download and unpack it by hand. The plugin builds with any JDK 21.
- A JDK from apt would tie the version to what Ubuntu 22.04 offers.

### xvfb and VS Code's libraries in `postCreateCommand`

The packages join the `apt install` of `postCreateCommand` that installs `gdb` today: `xvfb` (it brings `xvfb-run`) and the libraries of the VS Code documentation's container example, `libasound2 libgbm1 libgtk-3-0 libnss3`. Building the container decides the final list. If VS Code still fails to start because a library is missing, that library is added.

Alternatives:
- The feature `desktop-lite`, a VNC desktop: it was removed from the container in 2024 (340c6d04), and the tests need no desktop.
- A Dockerfile: the container would need its own build instead of an image with features, only for a few packages.

### Checking the container by building it

This change touches only the container's definition. So the check is to build the container with the Dev Containers CLI (`npx @devcontainers/cli up --workspace-folder .`, here with `--docker-path podman`) and to run in it `./gradlew test` in `intellij-client/`, `xvfb-run -a npm test`, and as a smoke check of the Python tests `hatch run test.rf75:test`. Codespaces uses the same configuration.

## Risks / Trade-offs

- [A newer VS Code needs a library that the list lacks] → VS Code fails to start, and its log names the library. The CI does not build the container, so the gap shows only when someone runs the tests there; the fix is one more package in the list.
- [A newer base image renames packages, such as `libasound2t64` on Ubuntu 24.04] → The image is pinned to jammy. A change of the base image has to recheck the list.
- [Creating a container takes longer] → The JDK and the libraries are installed once per container. The downloads of the test runs (VS Code, PyCharm) are the same as on any other machine.
- [Contributors without the hooks now see ESLint failures in their pull requests] → That is the intent. `npm run lint-fix` corrects most findings, Prettier's formatting among them.
