*** Settings ***
Test Template       suite template keyword


*** Test Cases ***
first
    [Tags]    robot:continue-on-failure
    [Template]    template keyword
    1    2    3
    3    5    6    2
    a=1    2    4

second
    [Tags]    robot:continue-on-failure
    1    2    3
    3    5    6    2
    a=1    2    4


*** Keywords ***
suite template keyword
    [Arguments]    ${a}    ${b}    ${c}
    Log    Test Template
    Log    ${a}
    Log    ${b}
    Log    ${c}

template keyword
    [Arguments]    ${a}    ${b}    ${c}
    Log    Template
    Log    ${a}
    Log    ${b}
    Log    ${c}