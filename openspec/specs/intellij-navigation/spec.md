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

### Requirement: Ctrl+hover underlines the name under the mouse

In a Robot Framework file, holding Ctrl over the name of a keyword call, a library or resource prefix, an import or a variable SHALL underline that name as the language server marks it, and nothing beyond it. A keyword call SHALL be underlined also in a setting such as `Test Setup` and as an argument of another keyword.

#### Scenario: Keyword call

- **WHEN** Ctrl is held and the mouse rests on `Add To Cart` in `Add To Cart    coffee`
- **THEN** `Add To Cart` is underlined

#### Scenario: Keyword in a setting

- **WHEN** Ctrl is held and the mouse rests on `Open Shop As` in `Test Setup    Open Shop As    alice`
- **THEN** `Open Shop As` is underlined

#### Scenario: Keyword as an argument of another keyword

- **WHEN** Ctrl is held and the mouse rests on `Open Shop As` in `Run Keyword And Expect Error    Wrong password    Open Shop As    alice`
- **THEN** `Open Shop As` is underlined

#### Scenario: Keyword after a prefix

- **WHEN** Ctrl is held and the mouse rests on `Log` in `BuiltIn.Log    ${arg2}`
- **THEN** only `Log` is underlined

#### Scenario: Prefix of a keyword call

- **WHEN** Ctrl is held and the mouse rests on `BuiltIn` in `BuiltIn.Log    ${arg2}`
- **THEN** only `BuiltIn` is underlined

#### Scenario: Keyword whose name contains a dot

- **WHEN** a suite defines a keyword `Shop.Open` and Ctrl is held with the mouse on `Shop.Open` in a call of it
- **THEN** `Shop.Open` is underlined as one name

#### Scenario: Variable with a type

- **WHEN** Ctrl is held and the mouse rests on `arg2` in `[Arguments]    ${arg1}    ${arg2: str}`
- **THEN** `arg2` is underlined, without `: str`

### Requirement: Ctrl+click goes to the target of the name under the mouse

In a Robot Framework file, Ctrl+click on the name of a keyword call, a library or resource prefix or an import SHALL go to the target of that name: the keyword's definition, the library or resource the prefix names, or the import.

#### Scenario: Keyword after a prefix

- **WHEN** Ctrl+click on `Log` in `BuiltIn.Log    ${arg2}`
- **THEN** the definition of the keyword `Log` of the BuiltIn library opens

#### Scenario: Prefix of an imported library

- **WHEN** Ctrl+click on `Collections` in `Collections.Append To List    ${items}    b`, in a file that has `Library    Collections`
- **THEN** the editor goes to that `Library    Collections` import

#### Scenario: Keyword in a setting

- **WHEN** Ctrl+click on `Open Shop As` in `Test Setup    Open Shop As    alice`
- **THEN** the definition of `Open Shop As` in `shop.resource` opens

### Requirement: The Ctrl+hover hint describes the target of the name

Holding Ctrl over a name in a Robot Framework file SHALL show the hint of that name's target, not of another part of the same cell.

#### Scenario: Keyword after a prefix

- **WHEN** Ctrl is held and the mouse rests on `Log` in `BuiltIn.Log    ${arg2}`
- **THEN** the hint describes the keyword `Log`, not the library `BuiltIn`

#### Scenario: Prefix of a keyword call

- **WHEN** Ctrl is held and the mouse rests on `Collections` in `Collections.Append To List    ${items}    b`
- **THEN** the hint describes the library `Collections`

### Requirement: Usages search for the name under the caret

In a Robot Framework file, Find Usages and Show Usages SHALL search for the name under the caret as the language server marks it, not for the first name of its cell. On the keyword of a call with a library or resource prefix they SHALL find the keyword's usages, and on the prefix those of the library or resource.

#### Scenario: Find Usages on the keyword after a prefix

- **WHEN** Find Usages starts on `Log` in `BuiltIn.Log    ${arg2}`
- **THEN** it finds the usages of the keyword `Log`, among them calls of `Log` without a prefix
- **AND** the Find tool window names what it searched for "Keyword" and "Log"

#### Scenario: Show Usages on the keyword after a prefix

- **WHEN** Show Usages starts on `Append To List` in `Collections.Append To List    ${items}    b`
- **THEN** the popup lists the usages of the keyword `Append To List` under the title "Keyword Append To List"

#### Scenario: Find Usages on the prefix

- **WHEN** Find Usages starts on `BuiltIn` in `BuiltIn.Log    ${arg2}`
- **THEN** it finds the usages of the library BuiltIn

#### Scenario: Keyword after a BDD prefix

- **WHEN** Find Usages starts on `Open Shop As` in `Given Open Shop As    bob`
- **THEN** it finds the usages of the keyword `Open Shop As`

### Requirement: LSP Reference(s) on a prefix shows the usages of its library or resource

In a Robot Framework file, **LSP Reference(s)** on the prefix of a keyword call SHALL show the imports and the prefixed calls of the library or resource file that the prefix names.

#### Scenario: Library prefix

- **WHEN** LSP Reference(s) runs on `Collections` in `Collections.Append To List    ${items}    b`
- **THEN** a popup lists the imports of `Collections` and the calls with the prefix `Collections.`

#### Scenario: Resource prefix

- **WHEN** LSP Reference(s) runs on `shop` in `shop.Open Shop As    alice`
- **THEN** a popup lists the imports of `shop.resource` and the calls with the prefix `shop.`

#### Scenario: Library without an import

- **WHEN** LSP Reference(s) runs on `BuiltIn` in `BuiltIn.Log    ${arg2}`, in a project with a second call prefixed with `BuiltIn.`
- **THEN** a popup lists both calls

### Requirement: LSP Reference(s) shows the usages of library keywords and file variables

In a Robot Framework file, **LSP Reference(s)** SHALL show the usages of a keyword from a library and of a variable from a Python variables file, together with the definition, as it does for a keyword from a resource file.

#### Scenario: Library keyword

- **WHEN** LSP Reference(s) runs on `Log` in `Log    Opened ${BASE_URL} as ${user}`
- **THEN** a popup lists the calls of `Log` in the project and the definition of `Log`

#### Scenario: Library keyword after a prefix

- **WHEN** LSP Reference(s) runs on `Append To List` in `Collections.Append To List    ${items}    b`
- **THEN** a popup lists the calls of `Append To List` and its definition

#### Scenario: Variable from a Python variables file

- **WHEN** LSP Reference(s) runs on `${GREETING}`, which a suite imports from a Python variables file
- **THEN** a popup lists the uses of `${GREETING}` and its definition in the Python file

#### Scenario: Keyword from a resource file

- **WHEN** LSP Reference(s) runs on `Add To Cart`, a keyword of a resource file
- **THEN** a popup lists the calls of `Add To Cart` and its definition, as before
