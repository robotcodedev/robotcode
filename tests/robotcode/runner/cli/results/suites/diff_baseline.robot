*** Settings ***
Documentation    Baseline half of the diff-test pair. Both halves are run
...              with `robot --name Diff` so their tests share full names.


*** Test Cases ***
Test Alpha
    [Tags]    smoke
    Log    alpha

Test Beta
    [Tags]    smoke
    Log    beta passed in baseline

Test Gamma
    [Tags]    regression
    Log    gamma exists in baseline only
