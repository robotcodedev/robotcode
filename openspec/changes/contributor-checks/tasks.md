# Tasks

## 1. ESLint in the CI

- [ ] 1.1 Add `- run: npm run lint` with `if: always()` to `code-quality` in `.github/workflows/build-test-package.yml`, directly after `hatch run lint:typing`. Verify that the workflow still parses as YAML (`python -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" .github/workflows/build-test-package.yml`) and that `npm run lint` passes locally.
- [ ] 1.2 Update the contribution guide for ESLint:
  - CONTRIBUTING.md, "What the CI runs": the code checks on Linux include `npm run lint`;
  - step 4 of the development workflow and the PR checklist's linting item name `npm run lint` for the VS Code extension next to `hatch run lint:all`;
  - step 5 names the commands that fix findings, `hatch run lint:fix` and `npm run lint-fix`, instead of `hatch run lint:style`, which only checks; the list of additional commands describes `hatch run lint:style` as a check, too;
  - the linting item of `.github/PULL_REQUEST_TEMPLATE.md` names `npm run lint` as well.

  Verify by reading the changed passages against `hatch.toml`, `package.json` and the workflow.

## 2. Dev container

- [ ] 2.1 In `.devcontainer/devcontainer.json`, add the feature `"ghcr.io/devcontainers/features/java:1": { "version": "21" }`, and add `xvfb libasound2 libgbm1 libgtk-3-0 libnss3` to the `apt install` of `postCreateCommand`. Verify that the Dev Containers CLI reads the file (`npx @devcontainers/cli read-configuration --workspace-folder .`).
- [ ] 2.2 Build the container with the Dev Containers CLI (`npx @devcontainers/cli up --workspace-folder . --docker-path podman`) and run in it with `devcontainer exec`: `java -version` (21), `./gradlew test` in `intellij-client/`, `xvfb-run -a npm test` and `hatch run test.rf75:test`. If VS Code does not start because a library is missing, add its package in 2.1 and build again. If the Dev Containers CLI does not work with podman here, ask the maintainer to check the container in a Codespace instead. Note the results here.
- [ ] 2.3 CONTRIBUTING.md, dev container option: the container also installs a JDK 21 and xvfb, so that all three test suites run in it and in Codespaces. Verify by reading the passage against `devcontainer.json`.

## 3. Verification

- [ ] 3.1 After the maintainer pushes, check the first CI run: `code-quality` runs the ESLint step after the Python checks, and the step passes.

## Workflow follow-up

- Archive the change after 3.1.
