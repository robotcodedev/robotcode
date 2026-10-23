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

**Checked in trial builds, 2026-10-23** (Dev Containers CLI with rootless podman 6.1.4, `--userns=keep-id` only for the trial):
- **Without a JDK, the wrapper doesn't start:** `./gradlew` stops with "JAVA_HOME is not set and no 'java' command could be found in your PATH". It downloads Gradle, and the foojay resolver could download the toolchain JDK, but the wrapper itself needs a JVM to start; Gradle 9 runs on Java 17 or newer.
- **The feature `ghcr.io/devcontainers/features/java:1` breaks the podman build.** The step that installs it leaves `/tmp` with mode 755 instead of 1777 and empties the apt lists. The Python feature after it then runs `apt-get update`, and apt's `_apt` user cannot create its temporary files in `/tmp`. The same configuration without the Java feature builds. The feature itself never changes `/tmp`: a watcher in the build step saw 1777 until the step ended, and only the layer that podman stored has 755. It happens when the feature runs from `/tmp/dev-container-features/java_1`, as the CLI runs every feature; run from `/root`, or run with `podman run`, it doesn't. Other features in that directory don't cause it either. The environment was rootless podman 6.1.4 with its native overlay driver on btrfs. Docker, which Codespaces uses, was not available to compare. On Ubuntu 26.04 the same happens: `/tmp` is 1777 before the Java step and 755 after it, and the Node feature that follows fails at `apt-get update`.
- **Packages from apt:** jammy offers `openjdk-21-jdk-headless` (21.0.12), and so does Ubuntu 26.04 (`base:resolute`, 26.04.1 LTS). On 26.04 the libraries are called `libasound2t64` and `libgtk-3-0t64`, and `libgbm1`, `libnss3` and `xvfb` keep their names. The image has the user `vscode` with UID 1000 and no Python; the Python feature (`os-provided`) installs Python 3.14.4 from apt. Hatch 1.18.1 creates the `devel` environments for Python 3.10 to 3.15 and downloads the Python versions it doesn't find.
- **The three test suites in the 26.04 container** with the planned configuration: `./gradlew test` 501 tests in 102 classes, one skipped, in 3:10 minutes including the downloads; `xvfb-run -a npm test` 60 passing with VS Code 1.127.0; `hatch run test.rf75:test` 5484 passed, 96 skipped, 3 xfailed.
- **pre-commit in the 26.04 container:**
  - `.pre-commit-config.yaml` asked for `python3.10` (`default_language_version`). That setting applies only to `conventional-pre-commit`, the one hook written in Python, which requires Python 3.8 or newer. ruff and mypy run through Hatch, whose lint environment asks for Python 3.10 itself.
  - `pre-commit install --install-hooks` failed with "failed to find interpreter for Builtin discover of python_spec='python3.10'". With the hooks installed, every commit stops at this error; this was reproduced in a scratch repository with a Python version that doesn't exist.
  - On the maintainer's machine it works without a Python 3.10 on the `PATH`, because virtualenv takes a Python 3.10 that uv manages (`~/.local/share/uv/python`).
  - The pinned version moved from 3.8 (2022) to 3.9 and to 3.10 (2025), without a reason in the commits.

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

### Ubuntu 26.04 as the base image

`mcr.microsoft.com/devcontainers/base:resolute` instead of `base:jammy`: Ubuntu 26.04, the newest LTS, instead of 22.04. The maintainer asked for a newer base, and every package this change needs is in its apt sources. The features stay as they are. The system Python becomes 3.14; RobotCode's environments don't depend on it, because Hatch provides the Python version each of them asks for.

Alternatives:
- Ubuntu 24.04 (`base:noble`): it would work the same way, with Python 3.12, but is two years older.
- Staying on jammy: Ubuntu 22.04 ends its standard support in 2027.

### The JDK from apt

`openjdk-21-jdk-headless` in the `apt install` of `postCreateCommand`, next to `gdb`. Version 21 is the build's toolchain, so Gradle neither looks for nor downloads another JDK, and the wrapper stays the only Gradle in the container. Headless, because the tests need no desktop.

Alternatives:
- The feature `ghcr.io/devcontainers/features/java:1`: it breaks the build with podman (see Context).
- A JDK 17 only to start Gradle, with the toolchain's JDK 21 downloaded by foojay: every new container would download a second JDK.
- The JetBrains Runtime, as in the CI: no package or feature provides it. The plugin builds with any JDK 21.

### xvfb and VS Code's libraries in `postCreateCommand`

The packages join the same `apt install`: `xvfb` (it brings `xvfb-run`) and the libraries of the VS Code documentation's container example under their Ubuntu 26.04 names, `libasound2t64 libgbm1 libgtk-3-0t64 libnss3`. The trial build showed that VS Code needs no more than these.

Alternatives:
- The feature `desktop-lite`, a VNC desktop: it was removed from the container in 2024 (340c6d04), and the tests need no desktop.
- A Dockerfile: the container would need its own build instead of an image with features, only for a few packages.

### Any Python 3 for the pre-commit hooks

The maintainer changed `default_language_version` to `python3`, so that pre-commit sets up `conventional-pre-commit` with the Python 3 it finds, and moved the hook from v4.0.0 to v4.4.0, its newest tag. v4.4.0 accepts the same commit types by default (feat and fix, plus build, chore, ci, docs, perf, refactor, revert, style and test) and also requires Python 3.8 or newer.

Alternatives:
- A Python 3.10 in the container, through uv (`uv python install 3.10`) or through the Python feature with `version: "3.10"`: more setup in every container for a hook that needs no particular Python version.
- Removing `default_language_version`: pre-commit would take the Python it runs with itself, with nearly the same effect.

### Checking the container by building it

This change touches only the container's definition. So the check is to build the container with the Dev Containers CLI (`npx @devcontainers/cli up --workspace-folder .`, here with `--docker-path podman`) and to run in it `./gradlew test` in `intellij-client/`, `xvfb-run -a npm test`, and as a smoke check of the Python tests `hatch run test.rf75:test`. Codespaces uses the same configuration.

The check runs in a shallow clone of the repository in a scratch directory, so that the container's `npm install` and Gradle build don't touch the working tree. Rootless podman needs `--userns=keep-id` to make the workspace writable for `vscode`; the trial passes it in a copy of the configuration (`--override-config`), and the repository's configuration doesn't get it, because Docker and Codespaces don't need it.

## Risks / Trade-offs

- [A newer VS Code needs a library that the list lacks] → VS Code fails to start, and its log names the library. The CI does not build the container, so the gap shows only when someone runs the tests there; the fix is one more package in the list.
- [Another base image renames packages, as 26.04 did with `libasound2t64`] → The image is pinned to `resolute`. A change of the base image has to recheck the list.
- [`hatch run test:test` runs with Python 3.14 in the container] → It also runs the Robot Framework versions that don't support 3.14, as on any machine with 3.14 as its default Python; CONTRIBUTING.md says that Robot Framework itself may fail there and that the CI is authoritative.
- [Creating a container takes longer] → The JDK and the libraries are installed once per container. The downloads of the test runs (VS Code, PyCharm) are the same as on any other machine.
- [Contributors without the hooks now see ESLint failures in their pull requests] → That is the intent. `npm run lint-fix` corrects most findings, Prettier's formatting among them.
