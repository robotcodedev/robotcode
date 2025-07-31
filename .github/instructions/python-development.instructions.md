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
    - indent: 2 spaces
    - package_structure: packages/ directory
  </file_conventions>
</ai_meta>

## Package Development

### Package Structure
- **ALWAYS** develop in packages/ directory
- **REQUIRED** follow package-based architecture
- **MUST** use proper __init__.py files for package imports

### Code Style Standards
- **Formatting:** we use ruff for formatting
- **Type Hints:** Required for all APIs
- **Docstrings:** Google style for modules, classes, and functions, but follows clean code principles
- **linting:** use ruff for static analysis and mypy for type checking


### Code Quality
```bash
hatch run lint:all            # All linting checks (black, isort, flake8)
hatch run lint:fix            # Auto-fix style issues
```

### Testing Requirements

### Python Interpreter
- **ask your tools** wich python interpreter to use for the project/workspace

### Matrix Testing
- **COMPREHENSIVE** testing across Python 3.8-3.13
- **MATRIX** testing with Robot Framework 5.0-7.3
- **INTEGRATION** tests in tests/robotcode/ with real scenarios
- **SNAPSHOT** testing with pytest regtest2

### Test Execution

**IMPORTANT**use the correct Python environment selected in your IDE

- **USE** `pytest .` to run unit tests,
- **USE** `pytest --regtest2-reset` to update snapshots
- **RUN** specific environments: `hatch run test.rf70.py311:test`
- **COVERAGE** reporting with `hatch run cov`

## Multi-Platform Consistency
- **ENSURE** consistent behavior across VS Code and IntelliJ
- **MAINTAIN** unified configuration approach
- **DOCUMENT** platform-specific differences

---

*These Python development rules ensure consistent, high-quality code across all RobotCode packages.*
