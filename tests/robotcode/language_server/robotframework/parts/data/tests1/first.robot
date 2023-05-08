*** Settings ***
Resource    firstresource.resource
Suite Setup     NONE

*** Test Cases ***
wip1
    TRY
        Some failing Keyword
    EXCEPT    hello1    AS    ${ex}
        Log    error: ${ex}
    # Fail    error: ${ex}
    EXCEPT    hello
        Log    hi
    END

wop
    [Tags]    duplicate
    No Operation

wup
    [Tags]    duplicate
    No Operation

*** Keywords ***
some keyword
    RunkeywordAnd Expect Error    asd    some failing keyword

some failing keyword1
    Fail    asd


abc ${def} hih
    [Arguments]    ${b}
    Log    hello ${def} ${b}
