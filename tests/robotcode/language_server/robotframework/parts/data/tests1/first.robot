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

# wip
#     Wait Until Keyword Succeeds    5s    100ms    some failing keyword


# first
#     Log    blah
#     some keyword
#     Sleep    1s

# second
#     Fail

# third
#     some failing keyword

*** Keywords ***
some keyword
    RunkeywordAnd Expect Error    asd    some failing keyword

some failing keyword1
    Fail    asd