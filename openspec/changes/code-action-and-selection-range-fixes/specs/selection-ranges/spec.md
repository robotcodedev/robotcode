# Spec Delta

## ADDED Requirements

### Requirement: One result per position

The selection ranges SHALL contain one result for each requested position, in the order of the positions, as the language server protocol requires. A position without any statement or block, such as one behind the end of the file, SHALL get a result whose range is the empty range at that position, and the positions after it SHALL get their results as usual.

#### Scenario: Position behind the end of the file
- **WHEN** selection ranges are requested for a position in a test, a position behind the end of the file and another position in the test
- **THEN** there are three results, the second is the empty range at its position, and the first and third are the steps of their positions
