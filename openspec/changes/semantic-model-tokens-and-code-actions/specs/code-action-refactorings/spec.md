# Spec Delta

## ADDED Requirements

### Requirement: Surround with IF, FOR, WHILE and GROUP

Besides the TRY variants, "Surround with IF", "Surround with FOR", "Surround with WHILE" and, from Robot Framework 7.2 on, "Surround with GROUP" of kind `refactor.surround` SHALL be offered for the same selections as the TRY variants, and SHALL be enabled and disabled as they are. "Surround with FOR" and "Surround with WHILE" SHALL also be disabled, with the reason "BREAK and CONTINUE would act on the new loop.", for a selection with `BREAK` or `CONTINUE`.

#### Scenario: Offered with the TRY variants
- **WHEN** refactorings are requested for a selection of the step `Log    x`, on Robot Framework 7.2 or newer
- **THEN** "Surround with IF", "Surround with FOR", "Surround with WHILE" and "Surround with GROUP" are offered and enabled, besides the TRY variants

#### Scenario: GROUP before Robot Framework 7.2
- **WHEN** refactorings are requested for a selection of the step `Log    x`, on Robot Framework 7.1 or older
- **THEN** "Surround with GROUP" is not offered, and the other three are

#### Scenario: BREAK in the selection
- **WHEN** refactorings are requested for a selection of `Log    ${i}` and `BREAK` in the body of a FOR loop
- **THEN** "Surround with FOR" and "Surround with WHILE" are disabled with the reason "BREAK and CONTINUE would act on the new loop."

### Requirement: The blocks that Surround with IF, FOR, WHILE and GROUP writes

Resolving one of these actions SHALL replace the whole lines of the selected statements, as the TRY variants do, by a header, the statements indented by four more spaces, and `END`, at the indentation of the first selected line. The headers SHALL be `IF    condition`, `FOR    ${item}    IN    @{items}`, `WHILE    condition` and `GROUP    name`. Afterwards the placeholder of the header SHALL be selected: `condition`, `@{items}` or `name`.

#### Scenario: IF
- **WHEN** "Surround with IF" is resolved for the step `    Log    x`
- **THEN** the line becomes `    IF    condition`, `        Log    x` and `    END`, and exactly `condition` is selected

#### Scenario: FOR
- **WHEN** "Surround with FOR" is resolved for the step `    Log    x`
- **THEN** the line becomes `    FOR    ${item}    IN    @{items}`, `        Log    x` and `    END`, and exactly `@{items}` is selected

#### Scenario: WHILE
- **WHEN** "Surround with WHILE" is resolved for the step `    Log    x`
- **THEN** the line becomes `    WHILE    condition`, `        Log    x` and `    END`, and exactly `condition` is selected

#### Scenario: GROUP
- **WHEN** "Surround with GROUP" is resolved for the step `    Log    x`, on Robot Framework 7.2 or newer
- **THEN** the line becomes `    GROUP    name`, `        Log    x` and `    END`, and exactly `name` is selected
