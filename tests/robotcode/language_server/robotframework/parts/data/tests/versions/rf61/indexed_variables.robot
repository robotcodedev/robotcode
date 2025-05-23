*** Variables ***
@{A_LIST}    1    2    3
${index}    1
${A_LIST ${index}}    2

*** Test Cases ***
first
    ${A_LIST}[0]    Evaluate  2
    ${A_LIST}[${index}]    Evaluate  2
    %{aaa}    Evalute  1
