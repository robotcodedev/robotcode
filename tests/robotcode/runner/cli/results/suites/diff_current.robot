*** Settings ***
Documentation    Current half of the diff-test pair. Compared to the
...              baseline one test flips status, one disappears, one is new.


*** Test Cases ***
Test Alpha
    [Tags]    smoke
    Log    alpha

Test Beta
    [Tags]    smoke
    Fail    Beta broke in current

Test Delta
    [Tags]    smoke
    Log    delta is new in current
