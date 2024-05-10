*** Test Cases ***
simple var
    VAR    ${a}    1
    VAR    ${b}    2
    VAR    ${RESULT}    3
    Should Be Equal    ${{$a+$b}}    ${RESULT}

var with scope
    VAR    ${a}    1    scope=GLOBAL
    VAR    ${b}    2    scope=SUITE
    VAR    ${RESULT}    3
    Should Be Equal    ${{$a+$b}}    ${RESULT}


var with invalid scope
    VAR    ${a}    1    scope=
    VAR    ${b}    2    scope=asldkfj
    VAR    ${RESULT}    3    scope
    Should Be Equal    ${{$a+$b}}    ${RESULT}

dict var
    VAR    &{a}    b=1    c=2    d=3    SCOPe=LOCAL
    Log Many    ${a}

list var
    VAR    @{a}    1    2    3    scope=LOCAL
    Log Many    ${a}

*** Keywords ***
a keyword with variables in doc, timeout and tags
    VAR    ${an_arg}    1
    [Documentation]    a keyword with parameters ${a var} and ${an_arg}
#                                                  ^^^^^ a global var in doc
#                                                               ^^^^^^ an argument in doc
    [Timeout]    ${an_arg}
#                  ^ an argument in timeout
    [Tags]    ${an_arg}   ${a var}    1234
#               ^^^^^^ an argument in tags
#                           ^^^^^ an argument in tags
    [Arguments]    ${an_arg}    ${a_second_arg}=${a}
    Log    ${an_arg}
    Log    ${a_second_arg}

a keyword with variables in doc, timeout and tags with args first
    VAR    ${an_arg}    1
    [Arguments]    ${an_arg}    ${a_second_arg}=${a}
    [Documentation]    a keyword with parameters ${a var} and ${an_arg}
#                                                  ^^^^^ a global var in doc
#                                                               ^^^^^^ an argument in doc
    [Timeout]    ${an_arg}
#                  ^ an argument in timeout
    [Tags]    ${an_arg}   ${a var}    1234
#               ^^^^^^ an argument in tags
#                           ^^^^^ an argument in tags
    Log    ${an_arg}
    Log    ${a_second_arg}
