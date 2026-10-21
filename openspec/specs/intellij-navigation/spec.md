# intellij-navigation Specification

## Purpose

Defines how the IntelliJ plugin presents navigation in Robot Framework files, such as what Show Usages and Find Usages call the place that is searched for.

## Requirements

### Requirement: Usages name the kind of what is searched for

When Show Usages or Find Usages starts in a Robot Framework file, the IDE SHALL name what is searched for by its kind: "Keyword" for a keyword call or definition, "Argument" for a keyword argument, "Variable" for a variable, "Namespace" for the name of an import or the prefix of a keyword call. A place of no known kind, such as a tag, SHALL be called "Symbol". No class name of the plugin or of LSP4IJ SHALL appear in its place.

#### Scenario: Keyword call in a setting

- **WHEN** Show Usages starts on `Open Shop As` in `Test Setup    Open Shop As    alice`
- **THEN** the popup's title is "Keyword Open Shop As" followed by the file name

#### Scenario: Keyword call as an argument of another keyword

- **WHEN** Show Usages starts on `Open Shop As` in `Run Keyword And Expect Error    Wrong password    Open Shop As    alice`
- **THEN** the popup's title starts with "Keyword Open Shop As"

#### Scenario: Keyword definition

- **WHEN** Show Usages starts on the name of the keyword definition `Open Shop As`
- **THEN** the popup's title starts with "Keyword Open Shop As"

#### Scenario: Keyword argument

- **WHEN** Show Usages starts on `${user}` in the body of a keyword whose `[Arguments]` declare `${user}`
- **THEN** the popup's title starts with "Argument user"

#### Scenario: Variable

- **WHEN** Show Usages starts on `${BASE_URL}`, a variable of the project
- **THEN** the popup's title starts with "Variable BASE_URL"

#### Scenario: Import

- **WHEN** Show Usages starts on `ShopLibrary` in `Library    ShopLibrary`
- **THEN** the popup's title starts with "Namespace ShopLibrary"

#### Scenario: Prefix of a keyword call

- **WHEN** Show Usages starts on `Collections` in `Collections.Append To List    ${items}    b`
- **THEN** the popup's title starts with "Namespace Collections"

#### Scenario: Tag

- **WHEN** Show Usages starts on `smoke` in `[Tags]    smoke`
- **THEN** the popup's title starts with "Symbol smoke"

#### Scenario: Find Usages

- **WHEN** Find Usages starts on the name of the keyword definition `Unused Helper`
- **THEN** the Find tool window names what it searched for "Keyword" and "Unused Helper", without a class name

#### Scenario: Before the language server has sent its tokens

- **WHEN** Show Usages starts on the keyword call `Add To Cart` in a test before the language server has analysed the file
- **THEN** the popup's title starts with "Keyword Add To Cart"

### Requirement: Usages show the name as it is written

When Show Usages or Find Usages starts in a Robot Framework file, the IDE SHALL name the place by its name as written in the file. For a variable this SHALL be the variable's name without the characters around it, never a part such as `${`.

#### Scenario: Local variable

- **WHEN** Show Usages starts on `${greeting}` in `Should Be Equal    ${greeting}    ${expected}`, after `${greeting}=    Greeting` in the same keyword
- **THEN** the popup's title starts with "Variable greeting"
- **AND** the title does not contain `${`
