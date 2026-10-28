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

### Requirement: Usages of an import

In a Robot Framework file, Find Usages and Show Usages on the name of a library or resource import SHALL list the imports of that library or file and the calls with its name as prefix.

#### Scenario: Find Usages on a resource import

- **WHEN** Find Usages starts on `../resources/shop.resource` in `Resource    ../resources/shop.resource`
- **THEN** the Find tool window lists the imports of `shop.resource` and the call `shop.Open Shop As`

#### Scenario: Show Usages on a resource import

- **WHEN** Show Usages starts on `../resources/shop.resource` in `Resource    ../resources/shop.resource`
- **THEN** a popup lists the imports of `shop.resource` and the call `shop.Open Shop As`

#### Scenario: Library import

- **WHEN** Find Usages starts on `Collections` in `Library    Collections`
- **THEN** the Find tool window lists the imports of `Collections` and the calls with the prefix `Collections.`, as before

### Requirement: Usages search from the name at the caret

In a Robot Framework file, Find Usages and Show Usages started in the editor SHALL search from the name at the caret, also when that name resolves to a place in a Robot Framework file. Started from another view, such as the Structure tool window, they SHALL behave as before and SHALL NOT search from the caret of an editor.

#### Scenario: Prefix of a resource call

- **WHEN** Find Usages starts on `shop` in `shop.Open Shop As    alice`
- **THEN** the Find tool window lists the imports of `shop.resource` and the calls with the prefix `shop.`

#### Scenario: Use of a keyword argument

- **WHEN** Show Usages starts on `${user}` in `Log In    ${user}    ${password}` in the body of `Open Shop As`
- **THEN** the popup lists the declaration and the uses of `${user}`, under the title "Argument user"

#### Scenario: Keyword from a resource file

- **WHEN** Find Usages starts on `Open Shop As` in `Given Open Shop As    bob`
- **THEN** the Find tool window lists the definition and the calls of `Open Shop As`, as before

#### Scenario: Structure tool window

- **WHEN** the caret of the editor rests on `Log` and Find Usages starts on the keyword `Open Shop As` in the Structure tool window of `shop.resource`
- **THEN** the result is the same as before this change, and no search for `Log` starts

### Requirement: The Ctrl+hover hint shows the documentation without extra empty lines

Holding Ctrl over a name in a Robot Framework file SHALL show the documentation in its hint with the spacing of Quick Documentation. A table SHALL follow its heading directly, headings and paragraphs SHALL get no additional empty line, and code blocks SHALL keep their line breaks. Quick Documentation and the hover without Ctrl SHALL show the same documentation without any markup as text.

#### Scenario: Arguments of a keyword

- **WHEN** Ctrl is held and the mouse rests on `Open Shop As` in `shop.Open Shop As    alice`
- **THEN** the hint shows the rows of the argument table below the heading "Arguments:", spaced as in Quick Documentation

#### Scenario: Library import

- **WHEN** Ctrl is held and the mouse rests on `Collections` in `Library    Collections`
- **THEN** the hint shows the library's version and scope below the heading "Library *Collections*", spaced as in Quick Documentation

#### Scenario: Paragraphs of the documentation

- **WHEN** Ctrl is held and the mouse rests on `Log` in `Log    Opened ${BASE_URL} as ${user}`
- **THEN** the paragraphs of the keyword's documentation are as far apart as in Quick Documentation

#### Scenario: Code block

- **WHEN** Ctrl is held and the mouse rests on `shopvars.py` in `Variables    ../libraries/shopvars.py`
- **THEN** the hint shows each variable of the file on its own line

#### Scenario: Quick Documentation and the hover without Ctrl

- **WHEN** Quick Documentation is opened on `Collections` in `Library    Collections`, or the mouse rests on it without Ctrl
- **THEN** the documentation shows the heading, the library's version and scope and the introduction, and no markup as text

### Requirement: Ctrl+click on a keyword definition shows its usages

In a Robot Framework file, Ctrl+click and **Navigate | Declaration or Usages** on the name of a keyword definition SHALL open the usages popup of that keyword, with the title and the places that Show Usages on that name lists.

#### Scenario: Keyword used in other files

- **WHEN** Ctrl+click on `Open Shop As` in its definition in `shop.resource`
- **THEN** a popup titled "Keyword Open Shop As" lists the definition and the calls in `cart.robot`, `login.robot` and `orders.robot`

#### Scenario: Declaration or Usages

- **WHEN** **Navigate | Declaration or Usages** runs with the caret in `Open Shop As` in its definition in `shop.resource`
- **THEN** the same popup opens

### Requirement: Ctrl+hover on a keyword definition shows its documentation

In a Robot Framework file, holding Ctrl over the name of a keyword definition SHALL underline that name and show the keyword's documentation in the hint, as holding Ctrl over a call of the keyword does.

#### Scenario: Name of a keyword definition

- **WHEN** Ctrl is held and the mouse rests on `Open Shop As` in its definition in `shop.resource`
- **THEN** `Open Shop As` is underlined
- **AND** the hint shows the keyword's documentation with its arguments, as over `Open Shop As` in `Test Setup    Open Shop As    alice`
