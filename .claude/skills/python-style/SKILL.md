---
name: python-style
description: Python coding conventions for the RobotCode repository. Use when writing or reviewing Python code under `src/robotcode/`, `packages/*/src/robotcode/`, or `tests/robotcode/`. Covers project-specific style rules that are not obvious from reading the code and that ruff/mypy alone do not catch.
---

# Python Style — RobotCode

These rules apply to all Python code in this repository. Ruff and mypy enforce most of the mechanical style; this skill covers the conventions a tool cannot guess from a single file.

## Hard rules

### No `from __future__ import annotations`

The project targets Python 3.10+ (`requires-python = ">=3.10"`, `ruff target-version = "py310"`, `mypy python_version = "3.10"`). PEP 604 union syntax (`X | Y`), built-in generics (`list[int]`, `dict[str, int]`), and forward references already work natively. The future-import is redundant and is not used anywhere in the codebase — do not add it.

If you find one in a file you are editing, leave it alone unless the change is otherwise justified — do not introduce noise PRs just to remove it.

### Namespace package `__init__.py` files stay empty

`src/robotcode/` and every `packages/*/src/robotcode/` are PEP 420 / explicit-base namespace packages (`mypy explicit_package_bases = true`, `namespace_packages = true`). Their top-level `__init__.py` files are intentionally empty. Do not add re-exports, version constants, or side-effect imports there.

Sub-packages below the namespace root behave normally and may have non-empty `__init__.py`.

### Mock where the symbol is used, not where it is defined

When patching for tests, target the full consumer-namespace path (the module that imports the symbol), not the module that defines it. Never reshape a production import just so a patch lands. This is a recurring source of brittle tests in this repo.

```python
# good — patch the consumer
mocker.patch("robotcode.runner.cli.do_thing")

# bad — patch the definition; misses re-imports
mocker.patch("robotcode.core.internals.do_thing")
```

## Mechanical style (enforced by tooling)

Run before committing:

```bash
hatch run lint:fix    # ruff format + autofix
hatch run lint:all    # ruff check + mypy (no autofix)
```

Key settings (see [pyproject.toml](../../../pyproject.toml) for the full list):

- **Line length:** 120
- **Quote style:** double quotes (ruff `Q`)
- **Import order:** ruff `I`, first-party = `robotcode`
- **Typing:** `mypy --strict`, `warn_unreachable`, `warn_unused_ignores`, `implicit_reexport = false`

A `# type: ignore[...]` must be specific (named code) and worth a one-line comment explaining why. Bare `# type: ignore` will be flagged by `warn_unused_ignores` once the underlying issue moves.

## Tests

- Tests mirror the package layout under `tests/robotcode/`.
- Pytest style: no parentheses on `@pytest.fixture` / marker decorators without arguments (ruff `PT`, `fixture-parentheses = false`, `mark-parentheses = false`).
- See also the [mock-where-used](#mock-where-the-symbol-is-used-not-where-it-is-defined) rule above.

## Out of scope

This skill covers Python source style only. Repo-wide contributor rules (signed commits, AI disclosure, test commands) live in [AGENTS.md](../../../AGENTS.md) and [CONTRIBUTING.md](../../../CONTRIBUTING.md).
