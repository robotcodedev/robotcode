# Spec Delta

## ADDED Requirements

### Requirement: Surround is offered for selections

For a selection that is not empty, when the request names no kinds or names `refactor.surround` or a kind above it such as `refactor`, the refactorings "Surround with TRY...EXCEPT", "Surround with TRY...FINALLY" and "Surround with TRY...EXCEPT...FINALLY" of kind `refactor.surround` SHALL be offered. Their edits SHALL be computed when an action is resolved.

#### Scenario: The three titles
- **WHEN** refactorings are requested for a selection of the step `Log    x`
- **THEN** "Surround with TRY...EXCEPT", "Surround with TRY...FINALLY" and "Surround with TRY...EXCEPT...FINALLY" are offered

### Requirement: Selections that Surround and Extract Keyword accept

Surround and Extract Keyword SHALL be enabled when the selection covers complete statements of one block level within one test or keyword, an inline IF included on every supported Robot Framework version. Otherwise they SHALL be disabled with the reason "A keyword call must be selected.", for example for settings, block headers or branches alone, only comments, or a selection that reaches into the next test or keyword.

#### Scenario: Inline IF
- **WHEN** refactorings are requested for a selection from the start to the end of the line `IF    ${TRUE}    Log    inline    ELSE    Log    other`
- **THEN** the Surround actions and "Extract keyword" are enabled, on Robot Framework 5.0 and 6.0 as on later versions

#### Scenario: Selection that reaches into the next test
- **WHEN** refactorings are requested for a selection that starts in a step of one test and ends in a step of the next test
- **THEN** the Surround actions and "Extract keyword" are disabled with the reason "A keyword call must be selected."

### Requirement: BREAK, CONTINUE and RETURN in the selection

The TRY variants of Surround SHALL accept `BREAK` and `CONTINUE`, which stay in the loop as part of the TRY branch, where Robot Framework allows them. Extract Keyword SHALL be disabled for a selection with `BREAK`, `CONTINUE` or `RETURN`, which in the new keyword would no longer act on the loop or the keyword they belong to.

#### Scenario: BREAK in a loop
- **WHEN** refactorings are requested for a selection of `Log    ${i}` and `BREAK` in the body of a FOR loop
- **THEN** the three TRY variants of Surround are enabled, and "Extract keyword" is disabled with the reason "A keyword call must be selected."

### Requirement: The code that Surround writes

Resolving a Surround action SHALL replace the whole lines of the selected statements, within the document, by `TRY`, the statements indented by four more spaces, an `EXCEPT    message` branch, a `FINALLY` branch or both, each with `Fail    Not Implemented`, and `END`, at the indentation of the first selected line. Afterwards `message` SHALL be selected, for TRY...FINALLY the `Fail    Not Implemented` of the FINALLY branch.

#### Scenario: TRY...EXCEPT
- **WHEN** "Surround with TRY...EXCEPT" is resolved for the step `    Log    x`
- **THEN** the line becomes `    TRY`, `        Log    x`, `    EXCEPT    message`, `        Fail    Not Implemented` and `    END`, and exactly `message` is selected

#### Scenario: TRY...FINALLY
- **WHEN** "Surround with TRY...FINALLY" is resolved for the step `    Log    x`
- **THEN** exactly `Fail    Not Implemented` in the FINALLY branch is selected

#### Scenario: Last line of the file
- **WHEN** "Surround with TRY...EXCEPT" is resolved for the last line of a file that does not end with a line break
- **THEN** the edit ends at the end of that line, and that line is the body of the TRY

### Requirement: The keyword that Extract Keyword writes

Resolving "Extract keyword" SHALL replace the selected lines by a call of `New Keyword`, or of the first free name `New Keyword 1`, `New Keyword 2` and so on, and insert that keyword where Create Keyword inserts one. Afterwards the name of the call SHALL be selected and renamed. The edits SHALL lie within the document and not overlap.

#### Scenario: Last line of a file without a keyword section
- **WHEN** "Extract keyword" is resolved for the last line of a file that has no keyword section and does not end with a line break
- **THEN** the edits do not overlap, lie within the document, and the file ends with a new keyword section that holds the new keyword

### Requirement: Arguments and return values of an extracted keyword

On every supported Robot Framework version, the variables that the selected lines use and that the test or keyword defines before them SHALL become the `[Arguments]` of the new keyword and the arguments of its call. The variables that the lines define and that the rest of the test or keyword uses SHALL be returned by `RETURN` and assigned by the call.

#### Scenario: Arguments and return value
- **WHEN** a test has the steps `${a}=    Set Variable    1`, `Log    ${a}`, `${b}=    Set Variable    ${a}` and `Log    ${b}`, and "Extract keyword" is resolved for the second and the third step
- **THEN** the new keyword has the line `[Arguments]    ${a}` and ends with `RETURN    ${b}`, and the two steps become `${b}    New Keyword    ${a}`
