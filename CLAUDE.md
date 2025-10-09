# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RobotCode is a comprehensive Robot Framework toolkit that provides IDE extensions, CLI tools, and Language Server Protocol implementation. It consists of:

- **VS Code Extension** (TypeScript) - Main IDE integration with debugging, testing, and language features
- **IntelliJ Plugin** (Kotlin) - IntelliJ/PyCharm support via LSP4IJ bridge
- **Python Packages** - Modular architecture with 12 specialized packages
- **Multi-language Support** - Robot Framework integration across platforms

## Development Commands

### Python/Backend Development
```bash
# Setup development environment
hatch env create devel

# Install all packages in development mode
hatch run install-packages

# Run tests
hatch run test:test
hatch run test:test-reset  # Reset regression test snapshots

# Linting and formatting
hatch run lint:all      # Run mypy and ruff checks
hatch run lint:fix      # Auto-fix formatting and linting issues
hatch run lint:typing   # Type checking only
hatch run lint:style    # Code style checks only

# Build and packaging
hatch run build:package     # Build packages
hatch run build:publish     # Publish to PyPI
```

### VS Code Extension Development
```bash
# Install dependencies
npm install --include=dev

# Build extension
npm run compile         # Development build
npm run package         # Production build

# Testing
npm run test
```

### IntelliJ Plugin Development
```bash
cd intellij-client

# Build plugin
./gradlew build

# Run development instance
./gradlew runIde
```

## Architecture and Package Structure

### Core Python Packages (`packages/`)
- **core/**: Shared utilities, type definitions, document management, event system
- **language_server/**: LSP implementation with common protocol parts and Robot Framework-specific features
- **debugger/**: Debug Adapter Protocol implementation with Robot Framework debugging
- **runner/**: Enhanced Robot Framework execution with CLI tools (robot, rebot, libdoc, testdoc)
- **analyze/**: Static code analysis and validation tools
- **jsonrpc2/**: JSON-RPC protocol implementation for client-server communication
- **plugin/**: Plugin system foundation with click helpers and manager
- **robot/**: Robot Framework integration utilities (config, diagnostics, AST helpers)
- **repl/** & **repl_server/**: Interactive Robot Framework shell and server
- **modifiers/**: Code transformation and diagnostic modification tools

### Extension Structure
- **vscode-client/extension/**: VS Code extension with manager-based lifecycle pattern
- **vscode-client/rendererLog/**: Notebook log rendering components
- **intellij-client/**: Kotlin plugin using LSP4IJ for Language Server communication

### Key Architectural Patterns
- **Modular Design**: Each package has specific responsibilities with minimal dependencies
- **Protocol-Based**: Uses LSP/DAP for consistent IDE integration across platforms
- **Manager Pattern**: VS Code extension uses managers for lifecycle management
- **Native Parser**: Built on Robot Framework's native parser for full compatibility
- **Multi-workspace Support**: Handles complex project structures with different Python environments

## Testing Strategy

### Test Matrix
- **Python Versions**: 3.10, 3.11, 3.12, 3.13, 3.14
- **Robot Framework Versions**: 5.0, 6.0, 6.1, 7.0, 7.1, 7.2, 7.3

### Running Tests
```bash
# Run full test suite
hatch run test

# Test specific environment
hatch run devel.py312-rf73:test

# Coverage reporting
hatch run cov
```

### Test Configuration
- Uses pytest with asyncio support
- Regression testing with regtest2 for snapshot testing
- HTML reporting for coverage analysis
- Test data in `tests/` directory with Robot Framework fixtures

## Configuration Files

### Build System
- **hatch.toml**: Package management, environments, and build scripts
- **pyproject.toml**: Python project configuration with tool settings (ruff, mypy, pytest)

### Code Quality
- **ruff**: Python linting and formatting (configured in pyproject.toml)
- **mypy**: Static type checking with strict mode
- **eslint.config.mjs**: TypeScript/JavaScript linting for VS Code extension

### Robot Framework
- **robot.toml**: Robot Framework configuration for testing
- **Language Server**: Supports robot.toml configuration files with JSON schema validation

## Important Development Notes

### Version Management
- Uses semantic versioning across all packages
- Version synchronization handled by scripts in `scripts/` directory
- Release automation through GitHub Actions

### Multi-Platform Considerations
- Python packages support Windows, macOS, Linux
- VS Code extension requires Node.js environment
- IntelliJ plugin requires Java/Kotlin environment

### Key Integration Points
- Language Server Protocol bridges Python backend to IDE frontends
- Debug Adapter Protocol enables Robot Framework debugging
- Native Robot Framework parser ensures full compatibility
- Plugin system allows extensibility through hooks

### Dependencies
- **Python**: Robot Framework, asyncio, typing extensions, click, platformdirs
- **VS Code**: TypeScript, vscode-languageclient, esbuild
- **IntelliJ**: Kotlin, LSP4IJ plugin
- **Build**: Hatch for Python packaging, npm for Node.js, Gradle for Kotlin