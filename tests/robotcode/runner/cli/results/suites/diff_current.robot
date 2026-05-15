*** Settings ***
Documentation    Current half of the diff-test pair. Compared to the
...              baseline: Beta now fails, Gamma is gone, Delta is new.


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
