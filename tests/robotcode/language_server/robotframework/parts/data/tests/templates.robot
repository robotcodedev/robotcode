*** Settings ***
Test Template    template keyword


*** Test Cases ***
first
    [Tags]    ROBOT:CONTINUE-ON-FAILURE
    [Template]    template keyword
    1    2    3
    3    5    6    2
    a=1    2    4

second
    [Tags]    ROBOT:CONTINUE-ON-FAILURE
    1    2    3
    3    5    6    2
    a=1    2    4


*** Keywords ***
template keyword
    [Arguments]    ${a}    ${b}    ${c}
    Log    ${a}
    Log    ${b}
    Log    ${c}