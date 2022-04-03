*** Settings ***
Test Template    Login with invalid credentials should fail

*** Variables ***
${VALID USER}    valid
${VALID PASSWORD}    pw
@{ITEMS}    1    2    3    4    5    6

*** Test Cases ***                USERNAME         PASSWORD
Invalid User Name                 invalid          ${VALID PASSWORD}
Invalid Password                  ${VALID USER}    invalid
Invalid User Name and Password    invalid          invalid
Empty User Name                   ${EMPTY}         ${VALID PASSWORD}
Empty Password                    ${VALID USER}    ${EMPTY}
Empty User Name and Password      ${EMPTY}         ${EMPTY}

*** Test Cases ***
Template with FOR loop
    [Template]    Example keyword
    FOR    ${item}    IN    @{ITEMS}
        ${item}    2nd arg
    END
    FOR    ${index}    IN RANGE    42
        1st arg    ${index}
    END

Template with FOR and IF
    [Template]    Example keyword
    FOR    ${item}    IN    @{ITEMS}
        IF  ${item} < 5
            ${item}    2nd arg
        ELSE
            ${item}    3nd arg
        END
    END

Template with FOR and IF invalid
    [Template]    Example keyword
    FOR    ${item}    IN    @{ITEMS}
        IF  ${item} < 5
            ${item}    2nd arg
            ${item}    2nd arg    2
        ELSE
            ${item}    3nd arg
        END
    END

*** Keywords ***
Login with invalid credentials should fail
    [Arguments]    ${username}    ${password}
    Log    ${username}    ${password}

Example keyword
    [Arguments]    ${a}    ${b}
    Log    ${a} ${b}