# keyword-breakpoints Specification

## Purpose

Defines how keyword breakpoints of the command-line debugger (`.break`, `.tbreak` and `robotcode robot-debug --break`) match the keywords that run.

## Requirements

### Requirement: Keyword names match like Robot Framework

A keyword breakpoint SHALL stop at a keyword whose name matches the breakpoint's name case-, space- and underscore-insensitively, as Robot Framework matches keyword names. The name SHALL match with or without the keyword's owner prefix (`Library.Keyword`).

#### Scenario: Name with underscores
- **WHEN** `.break get_price` is set and the test calls `Get Price`
- **THEN** the debugger stops at that call

#### Scenario: Name in another case
- **WHEN** `.break should be equal` is set and the test calls `Should Be Equal`
- **THEN** the debugger stops at that call

#### Scenario: Name with owner prefix
- **WHEN** `.break BuiltIn.Should Be Equal` is set and the test calls `Should Be Equal`
- **THEN** the debugger stops at that call

#### Scenario: Breakpoint on the command line
- **WHEN** `robotcode robot-debug --break get_price` runs a test that calls `Get Price`
- **THEN** the debugger stops at that call

### Requirement: Glob patterns

A keyword breakpoint's name SHALL support the glob patterns `*` (any characters), `?` (one character) and `[chars]` (one of the characters), as Robot Framework's `--removekeywords name:` and `--flattenkeywords name:` do.

#### Scenario: Every keyword of a library
- **WHEN** `.break BuiltIn.*` is set
- **THEN** the debugger stops at every BuiltIn keyword the test calls

#### Scenario: Part of a name
- **WHEN** `.break *Price` is set and the test calls `Get Price`
- **THEN** the debugger stops at that call

### Requirement: Keywords with embedded arguments

For a keyword with embedded arguments, a keyword breakpoint SHALL also match the keyword's definition name, so that it stops at every call of the keyword. A breakpoint with the name of a single call SHALL stop at the calls written that way; argument values SHALL NOT be evaluated.

#### Scenario: Definition name
- **WHEN** `.break Select ${animal} From List` is set and the test calls `Select dog From List` and `Select cat From List`
- **THEN** the debugger stops at both calls

#### Scenario: Pattern for the definition
- **WHEN** `.break Select * From List` is set and the test calls `Select dog From List` and `Select cat From List`
- **THEN** the debugger stops at both calls

#### Scenario: Name of a single call
- **WHEN** `.break Select dog From List` is set and the test calls `Select dog From List` and `Select cat From List`
- **THEN** the debugger stops at `Select dog From List` only

#### Scenario: Value from a variable
- **WHEN** `.break Select dog From List` is set and the test calls `Select ${pet} From List` with `${pet}` set to `dog`
- **THEN** the debugger doesn't stop at that call
