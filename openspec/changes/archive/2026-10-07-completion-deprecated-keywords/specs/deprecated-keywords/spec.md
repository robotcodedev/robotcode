# Spec Delta

## Purpose

Defines how keyword completion treats deprecated keywords, so that the editor shows which keywords Robot Framework will warn about, puts them behind the others and lets users hide them.

## ADDED Requirements

### Requirement: Deprecated keywords are marked in every keyword list

Keyword completion SHALL mark every deprecated keyword it offers as deprecated, in the list without a prefix, in the list after a library name and in the list after a resource name. A keyword is deprecated when its documentation starts with `*DEPRECATED`, on every supported Robot Framework version.

#### Scenario: Deprecated library keyword after the library name
- **WHEN** a suite imports the library `DepLib` whose keyword `Old Lib Kw` has the documentation `*DEPRECATED* Use New Lib Kw.`, and completion is requested after `DepLib.`
- **THEN** the list contains `Old Lib Kw`, marked as deprecated

#### Scenario: Deprecated resource keyword without a prefix
- **WHEN** a suite imports a resource file whose keyword `Old User Kw` has the documentation `*DEPRECATED!* Use something else.`, and completion is requested in a test case
- **THEN** the list contains `Old User Kw`, marked as deprecated

### Requirement: Deprecated keywords sort after the other keywords

Keyword completion SHALL sort deprecated keywords after the keywords of the same list that are neither deprecated nor private keywords of other files. Private keywords of other files, when they are shown, SHALL stay after the deprecated ones.

#### Scenario: Order in the list without a prefix
- **WHEN** completion is requested in a test case of a suite that offers the keywords `Click Element`, `Click Link` and the deprecated `Click Old Element`
- **THEN** `Click Old Element` sorts after `Click Element` and `Click Link`

#### Scenario: Order after the library name
- **WHEN** completion is requested after `DepLib.`, where `DepLib` has the keyword `New Lib Kw` and the deprecated `Old Lib Kw`
- **THEN** `Old Lib Kw` sorts after `New Lib Kw`

### Requirement: Setting to hide deprecated keywords

The setting `robotcode.completion.hideDeprecatedKeywords` SHALL be off when it is not set. While it is on, keyword completion SHALL NOT offer deprecated keywords in any keyword list, whichever file defines them, including the file being edited.

#### Scenario: Setting not set
- **WHEN** a workspace does not set `robotcode.completion.hideDeprecatedKeywords` and completion is requested in a test case of a suite that offers `Old User Kw`
- **THEN** the list contains `Old User Kw`, marked as deprecated

#### Scenario: Setting switched on
- **WHEN** `robotcode.completion.hideDeprecatedKeywords` is `true` and completion is requested without a prefix and after `DepLib.`
- **THEN** neither list contains `Old User Kw` or `Old Lib Kw`

#### Scenario: Deprecated keyword of the file being edited
- **WHEN** `robotcode.completion.hideDeprecatedKeywords` is `true` and a suite file defines the deprecated keyword `Own Old Kw`, and completion is requested in a test case of that suite file
- **THEN** the list does not contain `Own Old Kw`
