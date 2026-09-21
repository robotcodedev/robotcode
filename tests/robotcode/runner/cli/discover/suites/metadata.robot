*** Settings ***
Documentation    Tests with `[Metadata]` (Robot Framework 7.5+) for the
...              `discover` metadata tests.

*** Test Cases ***
Single Line
    [Metadata]    Issue    4409
    Log    single

Spaced Key
    [Metadata]    Owner Team    core
    [Metadata]    Issue    4410
    Log    spaced

Multi Line
    [Metadata]    Description    first line
    ...    second line
    Log    multi

No Metadata
    [Tags]    plain
    Log    none

Empty Setting
    [Metadata]
    Log    empty
