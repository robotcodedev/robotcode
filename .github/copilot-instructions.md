# RobotCode Development Guidelines

> Last Updated: 2025-01-25
> Version: 1.0
> Override Priority: Highest

<ai_meta>
  <parsing_rules>
    - Process development patterns in sequential order
    - Use exact patterns and templates provided
    - Follow MUST/ALWAYS/REQUIRED directives strictly
    - Never deviate from established architectural patterns
  </parsing_rules>
  <file_conventions>
    - encoding: UTF-8
    - line_endings: LF
    - indent: 2 spaces (Python) / 4 spaces (TypeScript)
    - package_structure: packages/ for Python, vscode-client/ for TypeScript
  </file_conventions>
</ai_meta>

RobotCode is a comprehensive Robot Framework toolkit that provides IDE extensions (VS Code, IntelliJ), CLI tools, and Language Server Protocol implementation. It uses Robot Framework's native parser for full compatibility while extending it with modern development tools like DAP debugging, test discovery, and multi-workspace support.

## Tech Stack

### Core Technologies
- **Language Server:** Python 3.8-3.13 with asyncio
- **Protocol:** Language Server Protocol (LSP) + Debug Adapter Protocol (DAP)
- **Parser:** Robot Framework native parser for full compatibility
- **Build System:** Hatch for package management and testing

### VS Code Extension
- **Language:** TypeScript
- **Pattern:** Manager-based lifecycle with proper disposal
- **Dependencies:** @vscode/test-electron, webpack, esbuild

### IntelliJ Plugin
- **Language:** Kotlin
- **Integration:** LSP4IJ for Language Server communication
- **Build:** Gradle with kotlin-gradle-plugin

### Testing Matrix
- **Python Versions:** 3.8, 3.9, 3.10, 3.11, 3.12, 3.13
- **Robot Framework:** 5.0, 6.0, 6.1, 7.0, 7.1, 7.2, 7.3
- **Test Framework:** pytest with regtest2 for snapshot testing

## Architecture Patterns

### Package Structure
```
packages/
├── core/                   # Base utilities and shared functionality
├── language_server/        # LSP implementation for IDE integration
├── debugger/              # Debug Adapter Protocol implementation
├── runner/                # Enhanced Robot Framework execution tools
├── analyze/               # Static code analysis and validation
├── jsonrpc2/              # JSON-RPC communication layer
├── plugin/                # Plugin system foundation
├── repl/                  # Interactive Robot Framework shell
├── repl_server/           # REPL server for remote connections
├── robot/                 # Robot Framework integration utilities
└── modifiers/             # Code transformation tools

vscode-client/             # VS Code extension (TypeScript)
├── extension/             # Main extension code with manager pattern
└── rendererLog/           # Log rendering components

intellij-client/           # IntelliJ/PyCharm plugin (Kotlin)
├── src/main/kotlin/       # Plugin implementation via LSP4IJ
└── build.gradle.kts       # Gradle build configuration
```

### Multi-Platform Support
- **Python CLI:** Cross-platform command-line tools
- **VS Code:** TypeScript extension with manager pattern
- **IntelliJ:** Kotlin plugin via LSP4IJ bridge
