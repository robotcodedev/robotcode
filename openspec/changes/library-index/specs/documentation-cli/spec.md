# Spec Delta

<!-- `robotcode doc` is the working name of the command; the final name is design question Q2 of doc-cli. -->

## MODIFIED Requirements

### Requirement: Only explicitly named targets are documented

`robotcode doc` SHALL document exactly the targets given on its command line, one or more per call, in the given order. A target SHALL be a library name (a standard library, a module or `module.Class`), a path to a library file or directory, either of them followed by import arguments in Libdoc's `Name::arg1::arg2` form, or a path to a file with an extension Robot Framework accepts for resource imports in the installed version (suite files included, documented with their keywords). Without a target the command SHALL document nothing: when none of `-k/--keyword`, `--list`, `--search` and `--search-regex` is given and `-o/--output` does not name a directory, it SHALL show the index of the available libraries and resources (requirement "robotcode doc without targets shows the index" of `library-discovery`); otherwise it SHALL fail with a usage error. `robotcode libdoc` SHALL remain an unchanged pass-through to Robot Framework's Libdoc.

#### Scenario: Library and resource in one call
- **WHEN** `robotcode doc Collections resources/common.resource` is run with the output piped
- **THEN** the output contains the canonical documentation of `Collections` followed by that of `common`

#### Scenario: No target
- **WHEN** `robotcode doc` is run without a target and with the output piped
- **THEN** it writes the Markdown listing of the index and exits with code 0

#### Scenario: Lookup option without a target
- **WHEN** `robotcode doc --list` or `robotcode doc --search dictionary` is run without a target
- **THEN** it prints a usage error and exits with code 2

#### Scenario: Directory output without a target
- **WHEN** `robotcode doc -o site/` is run without a target
- **THEN** it prints a usage error and exits with code 2
