## MODIFIED Requirements

### Requirement: Full-corpus parity with documented exceptions only
With the repaired suite, the model path's encoded token data SHALL equal the legacy path's for every `.robot` file in the LSP test data (including `versions/**`), leaving out the modifier `declaration` on `variable` and `parameter` tokens, which only the model path sends. Any other deviation SHALL be a documented xfail naming the file and the reason, and is permitted only where the model output is demonstrably more correct than legacy.

#### Scenario: Corpus run
- **WHEN** the parity suite runs over the full test-data corpus
- **THEN** every file passes or is a reasoned xfail; there are no silent skips

#### Scenario: Declaration of a variable
- **WHEN** the parity suite compares a file with `${x}=    Set Variable    1`
- **THEN** the token of `x` counts as equal, although only the model path gives it the modifier `declaration`
