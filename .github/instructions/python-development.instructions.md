---
description: Python Development Rules for RobotCode
applyTo: **/*.py
---

# Python Development Rules

<ai_meta>
  <parsing_rules>
    - Process XML blocks first for structured data
    - Execute instructions in sequential order
    - Use exact patterns and templates provided
    - Follow MUST/ALWAYS/REQUIRED directives strictly
  </parsing_rules>
  <file_conventions>
    - encoding: UTF-8
    - line_endings: LF
    - indent: 4 spaces
    - package_structure: packages/ directory
  </file_conventions>
</ai_meta>

## Package Development

### Package Structure
- **ALWAYS** develop in packages/ directory
- **REQUIRED** follow package-based architecture
- **MUST** use proper __init__.py files for package imports

### Code Style Standards
- **Formatting:** ruff for formatting (4-space indent, line length 120)
- **Linting:** ruff for static analysis, mypy for type checking
- **Type Hints:** Required for all public APIs
- **Docstrings:** Google style for modules, classes, and functions

### Code Quality Commands
```bash
hatch run lint:all            # All checks (ruff check + ruff format --diff + mypy)
hatch run lint:fix            # Auto-fix (ruff check --fix + ruff format)
```

### Namespace Package Pattern
- All packages share the `robotcode` namespace: `packages/{name}/src/robotcode/{name}/`
- `__init__.py` in `robotcode/` dirs are **empty** — never add imports to them
- Each package has its own `pyproject.toml` with version and `[project.entry-points.robotcode]`

### Plugin Hook Pattern
To add a CLI command or tool config, implement a hook in `hooks.py`:
```python
from robotcode.plugin import hookimpl

@hookimpl
def register_cli_commands() -> List[click.Command]:
    return [my_command]
```
Then register the entry point in the package's `pyproject.toml`:
```toml
[project.entry-points.robotcode]
my_feature = "robotcode.my_package.hooks"
```

### Python Interpreter
- **Ask your tools** which Python interpreter to use for the project/workspace

### Testing

**IMPORTANT:** Use the correct Python environment selected in your IDE.

- **Run tests:** `pytest .`
- **Update snapshots:** `pytest --regtest2-reset`
- **Specific matrix env:** `hatch run test.rf70.py311:test`
- **Coverage:** `hatch run cov`
- **Matrix:** Python 3.10–3.14 × Robot Framework 5.0–7.4
- **Integration tests** in `tests/robotcode/` with real scenarios
- **Snapshot testing** with pytest regtest2

## Multi-Platform Consistency
- **ENSURE** consistent behavior across VS Code and IntelliJ
- **MAINTAIN** unified configuration approach
- **DOCUMENT** platform-specific differences

---

*These Python development rules ensure consistent, high-quality code across all RobotCode packages.*
