---
description: TypeScript VS Code Extension Development Rules for RobotCode
applyTo: vscode-client/**/*.ts

---

# TypeScript VS Code Extension Development Rules

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
    - extension_structure: vscode-client/extension/
  </file_conventions>
</ai_meta>

## Extension Architecture

### Manager Pattern
- **MUST** implement disposal pattern for all managers
- **REQUIRED** proper lifecycle management
- **ALWAYS** register disposables in constructor

### Manager Template
```typescript
class XyzManager {
  private _disposables: vscode.Disposable;

  constructor() {
    this._disposables = vscode.Disposable.from(
      // ... register all disposables
    );
  }

  dispose(): void {
    this._disposables.dispose();
  }
}
```

## Code Style Standards

### TypeScript Formatting
- **Formatting:** 4-space indentation, semicolons required
- **Naming:** PascalCase for classes, camelCase for methods/variables
- **Patterns:** Manager pattern with dispose() lifecycle
- **Exports:** Named exports preferred over default exports

### File Organization
- **Manager-based structure** in vscode-client/extension/
- **Manager files:** `*Manager.ts` pattern
- **Tests:** Mirror source structure

## Development Commands

### Building & Packaging
```bash
npm run compile                     # Dev build (esbuild)
npm run package                     # Production build (esbuild --production)
npm run lint                        # ESLint
npm run lint-fix                    # ESLint auto-fix
```

### Key Build Notes
- Uses **esbuild** (not webpack) — configured in `esbuild.mjs`
- Main entry compiles to `./out/extension.js`
- Log renderer compiles to `./out/rendererLog.js`

## Critical Development Patterns

### Test Discovery Protocol
**ALWAYS** use `--read-from-stdin` with real-time document content:
```typescript
const openFiles = {};
vscode.workspace.textDocuments.forEach(doc => {
  if (this.isRobotFrameworkFile(doc)) {
    openFiles[doc.uri.toString()] = doc.getText();
  }
});

const result = await this.executeRobotCode(
  folder,
  ["discover", "--read-from-stdin", "all"],
  [],
  JSON.stringify(openFiles)
);
```

### Race Condition Prevention
**MUST** use mutex for async operations:
```typescript
await this.refreshMutex.dispatch(async () => {
  await this.refreshItem(item, token);
});
```

### Multi-Workspace Support
- **HANDLE** Multiple Robot Framework projects simultaneously
- **ISOLATE** Error handling per workspace
- **ENSURE** Proper context switching

### Activation & File Types
- Extension activates on `*.robot`, `*.resource`, `*.robotrepl`, `*.robotscript`, `robot.toml`, or debug sessions
- Supports `robotframework-repl` notebook type (`.robotbook` files)
- Custom notebook renderer for log output

## Error Handling Standards

### Extension Manager Disposal
- **IMPLEMENT** proper disposal pattern to prevent memory leaks
- **REGISTER** all disposables in constructor

### LSP Communication
- **HANDLE** multiple workspace folders with error isolation
- **MAINTAIN** robust communication with language server

### Development Server Conflicts
- **CHECK** for running development servers before starting tasks
- **PREVENT** port conflicts during testing

## VS Code Extension Development Workflow

### Adding New Features
1. **ALWAYS** Use manager pattern for new functionality
2. **REQUIRED** Implement proper disposal
3. **MUST** Handle race conditions with mutex
4. **ESSENTIAL** Test discovery with `--read-from-stdin`

### Manager Lifecycle
- **MUST** follow consistent lifecycle pattern
- **REQUIRED** proper disposal implementation
- **ALWAYS** register disposables in constructor

---

*These TypeScript development rules ensure consistent, high-quality VS Code extension development.*
