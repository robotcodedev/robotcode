*** Test Cases ***
first
    ${a}    fibonaci    ${15}
    Log To Console    ${a}

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