*** Variables ***
${2}    ${0x112.3432}
${a}    ${2}


*** Test Cases ***
first
    Log    ${{$a+$b}}

    Log    %{APPDATA}
    Log    ${2}
    first kw    1    2    3
    Log    ${a+@{c}+${d}}
    Log    ${{$a+$b+$c}}
    Log    ${c}
    ${v}    IF    1    Evaluate    2    ELSE    Evaluate    4
    Log    ${v}



*** Keywords ***
first kw
    [Arguments]    ${a}    ${b}  ${a}
    Log    ${a}
    Log    ${1asda + ${c} + 2}

