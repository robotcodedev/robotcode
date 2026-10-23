# Tasks

## 1. ESLint in the CI

- [x] 1.1 Add `- run: npm run lint` with `if: always()` to `code-quality` in `.github/workflows/build-test-package.yml`, directly after `hatch run lint:typing`. Verify that the workflow still parses as YAML (`python -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" .github/workflows/build-test-package.yml`) and that `npm run lint` passes locally.
- [x] 1.2 Update the contribution guide for ESLint:
  - CONTRIBUTING.md, "What the CI runs": the code checks on Linux include `npm run lint`;
  - step 4 of the development workflow and the PR checklist's linting item name `npm run lint` for the VS Code extension next to `hatch run lint:all`;
  - step 5 names the commands that fix findings, `hatch run lint:fix` and `npm run lint-fix`, instead of `hatch run lint:style`, which only checks; the list of additional commands describes `hatch run lint:style` as a check, too;
  - the linting item of `.github/PULL_REQUEST_TEMPLATE.md` names `npm run lint` as well.

  Verify by reading the changed passages against `hatch.toml`, `package.json` and the workflow.
  - Done 2026-10-23. Also corrected: the note on documentation-only changes in Running Tests said that `hatch run lint:all` runs ESLint; it now names `hatch run lint:all` and `npm run lint`.

## 2. Dev container

- [x] 2.1 In `.devcontainer/devcontainer.json`, change the image to `mcr.microsoft.com/devcontainers/base:resolute`, and add `openjdk-21-jdk-headless xvfb libasound2t64 libgbm1 libgtk-3-0t64 libnss3` to the `apt install` of `postCreateCommand`. Verify that the Dev Containers CLI reads the file (`npx @devcontainers/cli read-configuration --workspace-folder .`).
  - Done 2026-10-23. Planned first with the feature `ghcr.io/devcontainers/features/java:1` on jammy; the trial build in 2.2 showed that the feature breaks the build with podman, and the maintainer then chose Ubuntu 26.04 with the JDK from apt (see design.md).
- [x] 2.2 Build the container with the Dev Containers CLI (`npx @devcontainers/cli up --workspace-folder . --docker-path podman`) and run in it with `devcontainer exec`: `java -version` (21), `./gradlew test` in `intellij-client/`, `xvfb-run -a npm test` and `hatch run test.rf75:test`. If VS Code does not start because a library is missing, add its package in 2.1 and build again. If the Dev Containers CLI does not work with podman here, ask the maintainer to check the container in a Codespace instead. Note the results here.
  - Checked 2026-10-23 in a shallow clone of `main` (4d56474a) with the configuration of 2.1, plus `--userns=keep-id` for rootless podman 6.1.4 in a copy passed with `--override-config`. The container built and `postCreateCommand` finished. In it: OpenJDK 21.0.12.1, `xvfb-run`, Python 3.14.4, Hatch 1.18.1; `./gradlew test` BUILD SUCCESSFUL, 501 tests in 102 classes, 1 skipped (`RobotCodeEnvironmentProbeTest`); `xvfb-run -a npm test` 60 passing with VS Code 1.127.0; `hatch run test.rf75:test` 5484 passed, 96 skipped, 3 xfailed. Codespaces itself was not checked.
  - Full check 2026-10-23 in the same way on `main` 909be3b. Passed: `hatch run lint:all`, `npm run lint`, `npm run compile`, `xvfb-run -a npm test` (74 passing), `./gradlew buildPlugin`, `./gradlew verifyPlugin` (Compatible with PY-261 and PY-262), `npm run docs:build` (74 pages) and `hatch run test:test` (all nine Robot Framework versions on Python 3.14). `./gradlew test` had one failure, `RobotCodeEnvironmentTest.testSdkChangeChecksAnyInterpreterThatIsNotUsable` (expected 1 check, got 2), which failed again in one of three reruns of its class: a flaky test, not checked outside the container. `hatch run build:package` built the wheels and the VSIX and stopped at `gradle: not found`, as the non-goal in design.md expects.
- [x] 2.3 CONTRIBUTING.md, dev container option: the container also installs a JDK 21 and xvfb, so that all three test suites run in it and in Codespaces. Verify by reading the passage against `devcontainer.json`.
- [x] 2.4 `.pre-commit-config.yaml`: `python3` instead of `python3.10` as the hooks' Python, and `conventional-pre-commit` v4.4.0 (changed by the maintainer, see design.md). Verify in the dev container that `pre-commit install --install-hooks` succeeds, that a commit with a valid message passes all hooks, and that the commit-message hook rejects an invalid message.
  - Checked 2026-10-23 with pre-commit 4.7.0: the hooks installed; commits with the message `docs: check the hooks` and with a changed Python and TypeScript file passed Python style, Python typing, ESLint and Conventional Commit; the message `check the hooks` was rejected and made no commit.

## 3. Verification

- [x] 3.1 After the maintainer pushes, check the first CI run: `code-quality` runs the ESLint step after the Python checks, and the step passes.
  - Checked 2026-10-23 in run 39966973935 (push of 7e78d472): `code-quality` succeeded; its step 12, "Run npm run lint", ran after "Run hatch run lint:style" and "Run hatch run lint:typing" and passed.

## Workflow follow-up

- Archive the change after 3.1.
