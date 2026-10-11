# Proposal

## Why

In PyCharm and IntelliJ IDEA, keyword calls in Robot Framework files take the colour of the IDE's language default *Function declaration*, the same colour as test case and keyword names. A keyword call is a call, not a declaration: the IDE's other languages show calls in the *Function call* colour, and Robot Framework files should follow the same convention.

## What Changes

- The Robot Framework colour setting "Keyword call" inherits from the language default *Function call* instead of *Function declaration*. The settings for inner keyword calls and name calls keep inheriting from "Keyword call" and follow it.
- "Test case name" and "Keyword name" keep inheriting from *Function declaration*.
- A colour scheme that gives *Function call* no colour of its own shows keyword calls as plain text, as it shows function calls in its other languages. Users who want coloured keyword calls set a colour for "Keyword call" on the Robot Framework colour page, or for *Function call* under Language Defaults.

Behaviour that users notice, for the release notes (not breaking): keyword calls take the colour scheme's function call colour instead of its function declaration colour, and in schemes without a function call colour they are plain text.

Not part of this change: the colours of other token classes, and the VS Code extension.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `intellij-syntax-highlighting`: keyword calls inherit from *Function call*; test case names and keyword names stay with *Function declaration*.

## Impact

- `intellij-client/src/main/kotlin/dev/robotcode/robotcode4ij/highlighting/Colors.kt`: the fallback of the "Keyword call" setting.
- `intellij-client/src/test/kotlin/dev/robotcode/robotcode4ij/highlighting/ColorsTest.kt`.
- Colours that users set for "Keyword call" stay as they are; nothing stored changes.
- No change to the language server, the grammar or the VS Code extension.
