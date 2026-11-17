## ADDED Requirements

### Requirement: Deprecated keywords in JSON

In the JSON output of `doc lib`, `doc keywords` and `doc keyword`, the entry of a deprecated keyword SHALL have the field `deprecated` with the value `true`. The entry of a keyword that is not deprecated SHALL NOT have the field. A keyword is deprecated when keyword completion marks it as deprecated.

#### Scenario: Deprecated library keyword
- **WHEN** `robotcode --format json doc keywords DepLib` is run for a library `DepLib` whose keyword `Old Lib Kw` has the documentation `*DEPRECATED!!* Use New Lib Kw instead.`
- **THEN** the entry of `Old Lib Kw` has `deprecated` with the value `true`

#### Scenario: Keyword that is not deprecated
- **WHEN** the same command is run and `DepLib` also has the keyword `New Lib Kw` with the documentation `Does the new thing.`
- **THEN** the entry of `New Lib Kw` has no field `deprecated`

#### Scenario: Whole library
- **WHEN** `robotcode --format json doc lib DepLib` is run
- **THEN** the entry of `Old Lib Kw` has `deprecated` with the value `true`, and the entry of `New Lib Kw` has no field `deprecated`

#### Scenario: Deprecated resource keyword
- **WHEN** `robotcode --format json doc keyword dep.resource "Old User Kw"` is run for a resource file whose keyword `Old User Kw` has the `[Documentation]` `*DEPRECATED* Use something else.`
- **THEN** the entry of `Old User Kw` has `deprecated` with the value `true`
