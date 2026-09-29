*** Settings ***
Documentation    A test whose `[Metadata]` (Robot Framework 7.5+) value is a
...              variable, which Robot replaces when the test runs.

*** Variables ***
${BUILD}    42

*** Test Cases ***
Build
    [Metadata]    Build    ${BUILD}
    Log    build

No Metadata
    Log    none
