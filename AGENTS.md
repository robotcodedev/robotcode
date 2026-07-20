# Repository Guidelines

This file is a short orientation layer for automated contributors. For complete contributor details, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Quick Orientation

RobotCode is a multi-package Robot Framework toolkit.

- Root CLI: `src/robotcode/cli/`
- Python packages: `packages/*/src/robotcode/`
- Tests: `tests/robotcode/`
- VS Code extension: `vscode-client/`
- IntelliJ plugin: `intellij-client/src/main/kotlin/`, with tests in `intellij-client/src/test/kotlin/`
- Documentation: `docs/`
- Planning & design notes (roadmaps, design rationale, ideas): `dev-docs/`
- Maintenance scripts: `scripts/`

## Task Routing

- Python CLI/packages:
	- Owning paths: `src/robotcode/cli/`, `packages/*/src/robotcode/`.
	- Mirror tests under `tests/robotcode/`.
	- Keep namespace package `__init__.py` files empty.
- VS Code extension:
	- Owning path: `vscode-client/extension/`.
- IntelliJ plugin:
	- Owning path: `intellij-client/src/main/kotlin/`.
	- Run Gradle commands from `intellij-client/`.
- Docs:
	- Owning paths: `docs/`, root Markdown files.
- Planning & design notes (not user-facing):
	- Owning path: `dev-docs/` — versioned roadmaps, design rationale, and idea collections (unlike the git-ignored `playground/`). It is reference/ideas, not a status tracker: progress for OpenSpec work under `openspec/` is tracked there, not in `dev-docs/`.
- Generated or bundled outputs (do not edit by hand):
	- Includes `bundled/libs/`, syntax files, schemas, and version files.
	- Regenerate with the documented scripts and note the command used.

## Common Commands

Use `hatch run test:test` as the default test command. It runs the full Robot Framework matrix against the default Python and is fast enough for pre-commit. Reach for `devel:test` only when you suspect a Python-version-specific issue — it spins up 40 environments and is significantly slower.

- `hatch run test:test`
	- Default: full Robot Framework matrix on the default Python.
- `hatch run test.<rf-env>:test`
	- Focused Robot Framework version. Available: `rf50`, `rf60`, `rf61`, `rf70`, `rf71`, `rf72`, `rf73`, `rf74`.
- `hatch run devel:test`
	- Full Python × Robot Framework matrix (5 × 8 = 40 envs). Slow; use only for Python-version-specific changes.
- `hatch run devel.<py-env>-<rf-env>:test`
	- Focused Python × Robot Framework combination. Python envs: `py3.10`, `py3.11`, `py3.12`, `py3.13`, `py3.14`.
- `hatch run lint:all`
	- Ruff style checks plus mypy typing checks.
- `hatch run lint:fix`
	- Ruff fixes and formatting.
- `npm run lint`
	- TypeScript/JavaScript linting.
- `npm run compile` / `npm run package`
	- VS Code extension build commands.
- `npm run docs:dev` / `npm run docs:build`
	- Docs site development server or build.
- `(cd intellij-client && ./gradlew test)`
	- IntelliJ/Kotlin tests.
- `(cd intellij-client && ./gradlew buildPlugin)`
	- IntelliJ plugin package.
- `(cd intellij-client && ./gradlew verifyPlugin)`
	- IntelliJ plugin verification.

## Commits and Pull Requests

These rules are enforced — a violation will block the PR or fail a pre-commit hook, often after you have already pushed.

- **Conventional Commits** are required (`type(scope): subject`). Allowed types and scopes are listed in [CONTRIBUTING.md § Commit Messages](CONTRIBUTING.md#commit-messages).
- **Cryptographically signed commits** are mandatory (`git commit -S`, GPG/SSH). Unsigned commits in a PR are auto-blocked. This is separate from the DCO `Signed-off-by` trailer (`-s`).
- **AI / tooling disclosure** is required when an AI agent contributed substantially. See [AI_POLICY.md](AI_POLICY.md).
- Keep changes focused. No unrelated refactors or formatting noise in the same PR.

## Agent Notes

- Make small, focused changes and avoid unrelated refactors.
- Update [CONTRIBUTING.md](CONTRIBUTING.md) when contributor rules change; update this file when the orientation, task routing, or common commands change.
