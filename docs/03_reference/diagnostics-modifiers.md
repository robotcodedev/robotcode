# Controlling Diagnostics with Modifiers

RobotCode offers advanced static analysis for Robot Framework files. With **diagnostics modifiers** you can control directly in your Robot code which diagnostic messages (lint / analysis errors, warnings, hints) are shown and with what severity.

This allows you to, for example:

- hide specific rules for individual lines, blocks or files,
- adjust the severity of individual messages (hint → warning → error),
- temporarily disable diagnostics completely and re-enable them later.


## Basic Concept

RobotCode interprets special comments with the prefix `# robotcode:` as **diagnostics modifiers**.

General form:

```robot
# robotcode: <action>[code1,code2,...] [<action>[code1,code2,...]]...
```

- `action` is one of the predefined actions (see below).
- `code` are the diagnostic codes you want to influence (for example `variable-not-found`, `keyword-not-found`, `MultipleKeywords`). If omitted, the action applies to all diagnostics.
- You can chain multiple `<action>[...]` segments in the same comment; they are applied in the order written. If the same code appears more than once on the same line, the later action wins.

### Available Actions

- `ignore`: Ignore the given diagnostic codes completely (they will not be reported at all).
- `hint`: Treat the given codes as hints (lowest severity, usually rendered as faded or informational markers).
- `information` / `info`: Treat the given codes as informational messages (above hint, below warning).
- `warning` / `warn`: Treat the given codes as warnings (visible but not failing).
- `error`: Treat the given codes as errors (highest severity, typically used for CI or "problems" views).
- `reset`: Reset the given codes to their default level as defined by the underlying analyzer and any global configuration.
- `ignore` without list: Ignore **all** diagnostic messages in the affected scope.
- `reset` without list: Reset **all** diagnostic messages to their default; any previous `ignore`, `hint`, `information`, `warning` or `error` modifiers in scope are cleared.

Additional rules:

- Codes are matched case-insensitively and normalized internally, so `VariableNotFound` and `variable-not-found` are treated the same.
- Action names are also case-insensitive; `warn` = `warning`, `info` = `information`.
- In global configuration (for example `robot.toml`) you can use `"*"` as a wildcard to match all remaining diagnostics (for example `hint = ["*"]`).
- Inline `# robotcode:` modifiers on a specific line always override global configuration from `robot.toml` or CLI settings.
- If several modifiers affect the same line and code, the nearest one wins: inline (end-of-line) > indented block > top-level file comment > global/CLI settings. Within one comment the rightmost action for the same code wins.

### Where do the diagnostic codes come from?

- Every diagnostic emitted by RobotCode carries a `code` field (LSP `Diagnostic.code`). That value is exactly what you put into `ignore[...]`, `warn[...]`, etc.
- Core analyzers define their codes in `robotcode.robot.diagnostics.errors.Error` (for example `VariableNotFound`, `KeywordNotFound`, `MultipleKeywords`).
- The simplest way to read the code is in your editor’s Problems/Diagnostics view or in the CLI output of `robotcode analyze`, where the code appears in brackets before the message (e.g. `[W] KeywordNotFound: ...`).
- Custom analyzer plugins may emit additional codes; you handle them the same way via modifiers.

Common codes (core analyzer)

| Code                   | Meaning (short)                               |
| ---------------------- | --------------------------------------------- |
| VariableNotFound       | Variable reference could not be resolved.     |
| KeywordNotFound        | Keyword could not be resolved.                |
| MultipleKeywords       | Call matches multiple keywords (ambiguous).   |
| DeprecatedKeyword      | Called keyword is marked deprecated.          |
| PossibleCircularImport | Potential circular resource/variables import. |

Example CLI output (showing `code` before the message)

```bash
$ robotcode analyze code tests/example.robot
[W] KeywordNotFound: Some Undefined Keyword
    at tests/example.robot:5:5
[E] VariableNotFound: Variable '${missing}' not found
    at tests/example.robot:6:11
```


## Scope of a Modifier

The effect of a modifier depends on its position in the file.

### At the End of a Line

A modifier placed at the end of a line affects **only that line**.

```robot
*** Keywords ***
Keyword Name
    Log    ${arg1}    # robotcode: ignore[variable-not-found]
```

Here, the `variable-not-found` error is ignored only for this `Log` call.

### At the Beginning of a Line (Column 0)

A modifier placed at the very beginning of a line applies **from that line to the end of the file**, unless it is overridden or reset by another modifier.

```robot
# robotcode: ignore[keyword-not-found]
*** Test Cases ***
Example Test
    Log    Hello
    Some Undefined Keyword
```

From the position of this modifier to the end of the file, all `keyword-not-found` errors are ignored.

### Inside a Block (Indented)

A modifier that is indented and therefore lies inside a block (for example a Test Case, Keyword, IF, FOR) only applies to the **current block**.

```robot
*** Keywords ***
Example Keyword
    # robotcode: warn[variable-not-found]
    Log    ${arg1}
    Another Keyword
```

Within the `Example Keyword` block, `variable-not-found` errors are treated as warnings.


## Typical Use Cases

### Ignore a Single Diagnostic on One Line

```robot
*** Keywords ***
Show Debug Value
    Log    ${possibly_undefined}    # robotcode: ignore[variable-not-found]
```

Useful when you deliberately work with optional or dynamic variables.

### Treat a Rule Globally as "Hint"

```robot
# robotcode: hint[MultipleKeywords]
*** Test Cases ***
My Test
    Some Keyword
    Another Keyword
```

The `MultipleKeywords` diagnostic is treated as a hint from this point onward instead of a warning or error.

### Warning Instead of Error for a Specific Rule

```robot
# robotcode: warn[variable-not-found]
*** Test Cases ***
Experimental Test
    Log    ${undefined_variable}
```

`variable-not-found` stays visible but does not block you as an error.

### Combine Multiple Actions in One Comment

```robot
# robotcode: warn[keyword-not-found] ignore[variable-not-found]
*** Test Cases ***
Mixed Strictness
    Some Undefined Keyword
    Log    ${maybe_missing}
```

Here, `keyword-not-found` is downgraded to a warning while `variable-not-found` is ignored for the same lines; the actions are applied left to right.

### Enforce Strict Checking for a Single Rule

```robot
# robotcode: error[keyword-not-found]
*** Test Cases ***
Critical Test
    Some Undefined Keyword
```

`keyword-not-found` is treated as an error in this area, even if it is globally configured as a warning or hint.

### Fine-Grained Control with `reset`

```robot
# robotcode: error[variable-not-found]
*** Test Cases ***
Example Test
    Log    ${undefined_variable}

# robotcode: reset[variable-not-found]
Another Test
    Log    ${undefined_variable}
```

- Until the `reset` modifier, `variable-not-found` is treated as an error.
- After `reset[variable-not-found]` the global default severity for this rule is used again.

### Ignore All Diagnostics

```robot
# robotcode: ignore
*** Test Cases ***
Example Test
    Log    ${undefined_variable}
    Some Undefined Keyword
```

From this point on, all diagnostics are ignored.

### Reset All Diagnostics

```robot
# robotcode: ignore
*** Test Cases ***
Example Test
    Log    ${undefined_variable}

# robotcode: reset
Another Test
    Some Undefined Keyword
```

- Until the `reset` modifier, all diagnostics are ignored.
- After `reset`, all messages are reported again with their default severity.


## Best Practices

- **Keep modifiers local:** Prefer modifiers that are limited to a single line or block instead of globally disabling diagnostics for large parts of a file.
- **Document commonly used diagnostic codes:** If you use modifiers frequently in a project, document the most important codes (for example `variable-not-found`, `keyword-not-found`, `MultipleKeywords`) for your team.
- **Use `reset` consistently:** Especially when using `ignore` or `error` at the top of a file, make sure there is a clear `reset` later so that the effect does not unintentionally extend when code is moved or added.
- **Consider code review:** Because modifiers change the analysis results, they should be part of code review and consciously approved.


### Configuration via `robot.toml`

Global diagnostic modifiers are usually configured in the
`[tool.robotcode-analyze.modifiers]` section of a TOML configuration file,
typically the workspace-level `robot.toml` or the local `.robot.toml` file (see
[config.md](config.md) for details).

```toml
[tool.robotcode-analyze.modifiers]
# Completely ignore very noisy diagnostics
ignore = ["MultipleKeywords"]

# Downgrade selected rules to warnings
warning = ["variable-not-found"]

# Upgrade important rules to errors
error = ["keyword-not-found"]

# Optional: treat all remaining diagnostics as hints
hint = ["*"]
```

- `ignore`, `error`, `warning`, `information`, `hint` are lists of diagnostic
    codes that are merged into the global modifier configuration.
- If you want to **add** to existing lists without replacing them (for example when an extension provides defaults), use the matching `extend-*` keys, e.g. `extend-warning = ["variable-not-found"]`. See [config.md](config.md) for the full set.
- You can use `"*"` as a wildcard to match all remaining diagnostics if needed.

RobotCode tools such as the analyzer, runner and CLI commands read these values
from the configured TOML files and pass them as defaults into the diagnostics
modifier engine. Inline `# robotcode:` modifiers in `.robot` files are then
applied on top and always win for the affected line or block.

### Overriding via editor / language server settings

In addition to TOML configuration, the language server can also receive
equivalent diagnostic modifier settings from the editor (for example VS Code
`settings.json`). These modifier lists are combined with the values from
`[tool.robotcode-analyze.modifiers]` and provide a convenient way to override
or tweak project defaults per workspace or per developer.

In VS Code the corresponding settings live under the
`robotcode.analysis.diagnosticModifiers.*` keys, for example:

```jsonc
{
    "robotcode.analysis.diagnosticModifiers.ignore": [
        "MultipleKeywords"
    ],
    "robotcode.analysis.diagnosticModifiers.warning": [
        "variable-not-found"
    ],
    "robotcode.analysis.diagnosticModifiers.error": [
        "keyword-not-found"
    ]
}
```

Typical scenarios are:

- keep the canonical, shared configuration in `robot.toml`, and
- use editor settings only to temporarily relax or tighten certain rules
        (for example on a CI agent or for a specific developer machine).
