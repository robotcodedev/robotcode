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

### When to Ask vs. Implement Directly

- **ALWAYS ASK when multiple valid approaches exist:** Present specific options and wait for user choice
- **ALWAYS ASK when requirements are incomplete:** Don't make assumptions about missing details
- **IMPLEMENT DIRECTLY only when:** Requirements are clear and there's one obvious correct approach
- **STOP and ASK if unsure:** Better to ask than to implement the wrong solution

### Question Format Rules

- **Wait for Response:** NEVER implement after asking - always wait for the user's explicit choice
- **Specific Options:** Provide concrete alternatives, not vague descriptions
- **Number Options:** Use "1), 2), 3)" format for easy selection
- **Always Include "Other":** End with "4) Other approach - please describe what you have in mind"
- **One Question at a Time:** Ask one focused question, get answer, then proceed or ask next question

### Implementation Flow

1. **Analyze Request:** Is this clear and unambiguous?
2. **If Unclear:** Ask specific question with numbered options and STOP
3. **Wait for Answer:** Do not proceed until user responds
4. **Confirm Understanding:** "I understand you want option X. I'll implement..."
5. **Then Implement:** Only after explicit user choice

### Example Interaction Pattern

```
User: "Add error handling to the function"

Agent: "I see several approaches for error handling. Which would you prefer?

1) Try-catch blocks with specific exception types
2) Return Result<T, Error> pattern with error types
3) Simple boolean return with logging
4) Other approach - please describe what you have in mind

Please let me know which option you'd like me to implement."

[WAIT FOR USER RESPONSE - DO NOT IMPLEMENT YET]
```

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
