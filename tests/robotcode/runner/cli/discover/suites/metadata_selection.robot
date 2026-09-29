*** Settings ***
Documentation    Tests with `[Metadata]` (Robot Framework 7.5+) for selecting
...              tests by their metadata.
Metadata         Owner    core

*** Test Cases ***
Issue 4409 Smoke
    [Tags]    smoke
    [Metadata]    Issue    4409
    [Metadata]    Author    Hans Müller
    [Metadata]    Reviewer    Eva Schmidt
    Log    smoke

Issue 4409
    [Metadata]    Issue    4409
    [Metadata]    Author    Hans Müller
    Log    unreviewed

Issue 4410
    [Metadata]    Issue    4410
    Log    other issue

Requirement 4409
    [Metadata]    Requirement    4409
    Log    requirement

Core Issue
    [Metadata]    Issue    CORE-123
    Log    upper case

Norbert
    [Metadata]    Author    NORBERT
    Log    upper case

Rock And Roll
    [Metadata]    Title    Rock AND Roll
    Log    operator word

Two Lines
    [Metadata]    Issue    5769
    ...    5770
    Log    two lines

Two Cells
    [Metadata]    Issue    5771    5772
    Log    two cells

Owner Without Value
    [Metadata]    Owner
    Log    no value

Build
    [Metadata]    Build    ${BUILD}
    Log    variable

Lower Case Name
    [Metadata]    issue    4411
    Log    other spelling

No Metadata
    Log    none
