*** Settings ***
Documentation    Distinct tag set for `discover tags` tests, including
...              variants that exercise Robot's tag normalisation.

*** Test Cases ***
Smoke Login
    [Tags]    smoke    bug-1
    Log    s1

Smoke Logout
    [Tags]    smoke    WIP
    Log    s2

Regression Login
    [Tags]    regression    bug_1
    Log    r1

Slow Path
    [Tags]    slow
    Log    sp

Bug Variant A
    [Tags]    BUG1
    Log    a

Bug Variant B
    [Tags]    bug 1
    Log    b
