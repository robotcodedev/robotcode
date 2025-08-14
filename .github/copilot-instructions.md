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

## Agent Communication Guidelines

### Core Rules

- **REVIEW/ANALYZE/CHECK/EXAMINE:** READ-ONLY operations. Provide analysis and feedback, NEVER make changes
- **IMPLEMENT/ADD/CREATE/FIX/CHANGE:** Implementation required. ALWAYS ask for confirmation and wait for explicit user choice before proceeding
- **IMPROVE/OPTIMIZE/REFACTOR:** Always ask for specific approach before implementing
- **MANDATORY WAIT:** When presenting implementation options, ALWAYS wait for explicit user choice before proceeding

### Communication Flow

1. **Recognize Intent:** Review request vs. Implementation request?
2. **For Reviews:** Analyze and suggest, but don't change anything
3. **For Implementation:**
   - ALWAYS ask for confirmation before implementing
   - If multiple approaches exist, present numbered options A), B), C), D), ...)
   - ALWAYS end with "Other approach"
   - WAIT for user response before proceeding
   - NEVER start implementation until user explicitly chooses an option
4. **Critical Rule:** When presenting options, STOP and wait for user input. Do not continue with any implementation.

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

## General Coding Guidelines

### Clean Code Principles
- **Readability First:** Code is read more often than written - prioritize clarity over cleverness
- **Meaningful Names:** Use descriptive names for variables, functions, and classes that express intent
- **Single Responsibility:** Each function/class should have one reason to change
- **Small Functions:** Keep functions focused and under 20 lines when possible
- **No Magic Numbers:** Use named constants or enums instead of hardcoded values
- **Avoid Deep Nesting:** Use early returns and guard clauses to reduce cyclomatic complexity

### Code Organization
- **Consistent Structure:** Follow established patterns within each package
- **Separation of Concerns:** Keep business logic separate from infrastructure code
- **Interface Segregation:** Create focused interfaces rather than monolithic ones
- **Dependency Inversion:** Depend on abstractions, not concrete implementations

### Error Handling
- **Explicit Error Handling:** Use proper exception/error types and hierarchies
- **Fail Fast:** Validate inputs early and provide clear error messages
- **Resource Management:** Use appropriate resource cleanup patterns (try-with-resources, RAII, etc.)
- **Logging:** Provide meaningful log messages at appropriate levels

### Documentation Standards
- **Function Documentation:** All public functions/methods must have comprehensive documentation
- **Type Annotations:** Use static type checking where available (TypeScript, Python type hints, etc.)
- **README Files:** Each package/module should have clear usage documentation
- **Inline Comments:** Explain *why*, not *what* - the code should be self-documenting

### Project Language Requirement
- **English for code and docs (REQUIRED):** Regardless of the natural language a user speaks when interacting with contributors or tools, all project-facing text must use English. This includes:
  - Documentation and README content
  - Inline comments and docstrings
  - Public and internal variable, function, class, and module names (identifiers)
  - Commit messages and code review comments where project conventions apply

  This rule ensures consistency across the codebase, improves discoverability for international contributors, and enables reliable tooling (linters, analyzers, and internationalized docs). Use English even when writing examples or user-facing strings in tests; if localised strings are required, keep the canonical code-level names and primary docs in English and add separate localized resources.

### Commit Message Standard
- **Conventional Commits (REQUIRED):** This project uses the Conventional Commits specification for commit messages. Commit messages must follow the format:
  - <type>(<scope>): <short description>
  - Optionally include a longer body and/or footer for references (breaking changes, issue numbers).

  Common types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.

  Example:
  - feat(cli): add `--dry-run` flag to publish command

  Following this convention enables automated changelog generation, semantic versioning tools, and clearer git history.

  Brief rules (self-contained):
  - A commit message MUST start with a type, optionally a scope, then a short description. Example: `feat(cli): add --dry-run flag`.
  - Types indicate the kind of change (e.g., `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`).
  - The scope is optional and should be a noun describing the area affected (e.g., `cli`, `docs`).
  - An optional body may follow after a blank line to explain motivation and other details.
  - Breaking changes MUST be indicated in the footer with `BREAKING CHANGE: <description>`.
  - Multiple line footer entries can reference issues or metadata (e.g., `Closes #123`).

### Testing Requirements
- **Test Coverage:** Maintain high test coverage with meaningful test cases
- **Test Naming:** Use descriptive test names that explain the scenario
- **Test Structure:** Organize tests clearly with setup, execution, and verification phases
- **Test Independence:** Each test should be able to run in isolation

### Performance Considerations
- **Async Patterns:** Use proper asynchronous programming patterns where applicable
- **Resource Efficiency:** Minimize memory allocations and resource usage in hot paths
- **Lazy Loading:** Load resources only when needed
- **Caching Strategy:** Implement appropriate caching for expensive operations

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
