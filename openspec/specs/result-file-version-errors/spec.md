# Spec: result-file-version-errors

## Purpose

Defines how `robotcode results` reports a result file that the installed Robot Framework cannot read, so that the user sees which Robot Framework version is needed.

## Requirements

### Requirement: JSON result files on Robot Framework older than 7.0

When the installed Robot Framework is older than 7.0 and `robotcode results` is given a JSON result file, the command SHALL fail with a message that says reading JSON result files requires Robot Framework 7.0 or newer and names the file.

#### Scenario: JSON file on Robot Framework 6.1
- **WHEN** `robotcode results show --output output.json` is run with Robot Framework 6.1.1 installed
- **THEN** the command fails with a message that names Robot Framework 7.0 as the required version and the path of `output.json`
