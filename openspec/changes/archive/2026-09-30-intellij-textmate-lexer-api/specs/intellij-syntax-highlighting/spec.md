# Spec Delta

## Purpose

Defines how the IntelliJ plugin highlights Robot Framework files with the TextMate grammar it bundles, on every platform version it supports, and how its lexers share the work of matching the grammar.

## ADDED Requirements

### Requirement: Robot Framework files are highlighted with the bundled grammar

The IntelliJ plugin SHALL highlight Robot Framework suite and resource files with the Robot Framework TextMate grammar it bundles (scope `source.robotframework`), in the editor and when it parses the file. It SHALL NOT bundle the grammar for Robot Framework code blocks in Markdown, which only the VS Code extension uses. The way the lexer is built SHALL NOT change which tokens a file is split into or which scopes they get.

#### Scenario: Suite file in the editor
- **WHEN** a `.robot` file with settings, variables, test cases, keywords and comments is opened in PyCharm or IntelliJ IDEA 2026.1
- **THEN** section headers, test case and keyword names, keyword calls, settings, variables and comments are highlighted with the colours of their scopes

#### Scenario: Same tokens after a change to the lexer construction
- **WHEN** the same Robot Framework files are lexed with the lexer before and after a change to how it is built
- **THEN** both produce the same tokens with the same offsets and scopes

### Requirement: The lexer uses no deprecated TextMate API of the supported platforms

The plugin SHALL build its TextMate lexer only from TextMate plugin API that is not deprecated in its minimum supported platform version, and SHALL use the replacement API where the minimum version already provides one.

#### Scenario: Plugin verification on the minimum and newer versions
- **WHEN** `verifyPlugin` checks the plugin against the minimum supported IDE version and the newer versions it is configured for
- **THEN** the report lists no deprecated TextMate API usage

#### Scenario: Compiler warnings
- **WHEN** the plugin is compiled against the minimum supported platform version
- **THEN** the compiler reports no deprecation warning for TextMate API

### Requirement: Lexers share their caches

All Robot Framework lexers of one IDE instance SHALL share one cache of compiled regular expressions, one cache of selector weights and one cache of rule matches, instead of each lexer starting with empty caches. Concurrent use from several editors and background parses SHALL be safe.

#### Scenario: Second file reuses compiled patterns
- **WHEN** a second Robot Framework file is opened while the first one is still open
- **THEN** its highlighter reuses the regular expressions already compiled for the first file instead of compiling them again

#### Scenario: Highlighter and parser share caches
- **WHEN** a Robot Framework file is highlighted and parsed
- **THEN** the highlighting lexer and the parsing lexer use the same caches
