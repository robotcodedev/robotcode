---
description: Kotlin IntelliJ Plugin Development Rules for RobotCode
applyTo: intellij-client/**
---

# Kotlin IntelliJ Plugin Development Rules

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
    - plugin_structure: intellij-client/src/main/kotlin/
  </file_conventions>
</ai_meta>

## Plugin Architecture

### LSP4IJ Integration
- **Language:** Kotlin
- **Integration:** LSP4IJ for Language Server communication
- **Build:** Gradle with kotlin-gradle-plugin

### Plugin Structure
```
intellij-client/
├── src/main/kotlin/       # Plugin implementation via LSP4IJ
└── build.gradle.kts       # Gradle build configuration
```

## Development Commands

### Building & Packaging
```bash
cd intellij-client && gradle buildPlugin  # IntelliJ plugin
```

## LSP4IJ Best Practices

### Language Server Communication
- **IMPLEMENT** proper LSP4IJ bridge patterns
- **HANDLE** multiple workspace folders with error isolation
- **MAINTAIN** robust communication with RobotCode language server

### Multi-Platform Consistency
- **ENSURE** consistent behavior with VS Code extension
- **MAINTAIN** unified configuration approach
- **DOCUMENT** platform-specific differences where necessary

## Configuration System

### robot.toml Integration
- **SUPPORT** robot.toml parsing and profile management
- **VALIDATE** configuration options consistently with other platforms
- **MAINTAIN** cross-platform configuration compatibility

## Error Handling Standards

### Plugin Lifecycle
- **IMPLEMENT** proper plugin lifecycle management
- **HANDLE** startup and shutdown gracefully
- **MANAGE** resources properly to prevent memory leaks

### LSP Communication
- **ISOLATE** error handling per workspace
- **MAINTAIN** robust communication with language server
- **HANDLE** connection failures gracefully

---

*These Kotlin development rules ensure consistent, high-quality IntelliJ plugin development.*
