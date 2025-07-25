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
- **Formatting:** Follow Black code style with line length 88
- **Imports:** isort with profile=black
- **Type Hints:** Required for all public APIs
- **Docstrings:** Google style for modules, classes, and functions

### Environment Setup
```bash
hatch run install-packages    # Install all packages in development mode
```

### Testing Commands
```bash
hatch run test.rf70:test      # Test with Robot Framework 7.0
hatch run test.rf70.py311:test # Specific Python + RF combination
hatch run cov                 # Run with coverage reporting
pytest --regtest2-reset      # Update test snapshots
```

### Code Quality
```bash
hatch run lint:all            # All linting checks (black, isort, flake8)
hatch run lint:fix            # Auto-fix style issues
```

## CLI Error Handling Pattern

**REQUIRED** pattern for all CLI tools:
```python
try:
  result = execute_command()
except Exception as e:
  app.error(f"Failed to execute: {e}")
```

## Package-Specific Guidelines

### Core Package (`packages/core/`)
- **Base utilities and shared functionality**
- **MUST** be importable by all other packages
- **NO** dependencies on other RobotCode packages

### Language Server (`packages/language_server/`)
- **LSP implementation for IDE integration**
- **ALWAYS** use asyncio patterns
- **REQUIRED** proper error isolation per workspace

### Debugger (`packages/debugger/`)
- **Debug Adapter Protocol implementation**
- **MUST** handle multi-workspace scenarios
- **REQUIRED** proper session management

### Runner (`packages/runner/`)
- **Enhanced Robot Framework execution tools**
- **ALWAYS** use Robot Framework native parser
- **REQUIRED** configuration via robot.toml

### Testing Requirements

### Matrix Testing
- **COMPREHENSIVE** testing across Python 3.8-3.13
- **MATRIX** testing with Robot Framework 5.0-7.3
- **INTEGRATION** tests in tests/robotcode/ with real scenarios
- **SNAPSHOT** testing with pytest regtest2

### Test Execution
- **USE** `pytest --regtest2-reset` to update snapshots
- **RUN** specific environments: `hatch run test.rf70.py311:test`
- **COVERAGE** reporting with `hatch run cov`

## Configuration System

### robot.toml Configuration
- **IMPLEMENT** robot.toml parsing throughout CLI and language server
- **SUPPORT** profile management and inheritance
- **VALIDATE** configuration options

### Multi-Platform Consistency
- **ENSURE** consistent behavior across VS Code and IntelliJ
- **MAINTAIN** unified configuration approach
- **DOCUMENT** platform-specific differences

---

*These Python development rules ensure consistent, high-quality code across all RobotCode packages.*
