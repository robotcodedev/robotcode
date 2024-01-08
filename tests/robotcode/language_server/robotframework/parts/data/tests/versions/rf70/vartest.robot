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
