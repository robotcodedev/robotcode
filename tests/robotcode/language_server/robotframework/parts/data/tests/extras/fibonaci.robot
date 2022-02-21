*** Test Cases ***
calc fibonaci
    ${a}    fibonaci    ${14}
    Log    ${a}

calc fibonaci data
    [Template]    calc fibonaci kw
    1
    2
    3
    4
    5
    6
    7
    20
    9
    10
    11
    12
    13
    14


*** Keywords ***
fibonaci
    [Arguments]    ${n}

    IF    $n<=1
        ${r}    Set Variable    ${n}
    ELSE
        ${n1}    fibonaci    ${{$n-1}}
        ${n2}    fibonaci    ${{$n-2}}
        ${r}    Set Variable    ${{$n1 + $n2}}
    END

    [Return]    ${r}

calc fibonaci kw
    [Arguments]    ${n}
    ${a}    fibonaci    ${{${n}}}
    Log    ${a}
