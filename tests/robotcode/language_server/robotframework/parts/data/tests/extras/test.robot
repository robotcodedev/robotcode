*** Settings ***

*** Variables ***
${var}    1
${var1}    2

*** Test Cases ***
first
    a keyword

*** Keywords ***
a keyword
    [Arguments]    ${bar}    ${var1}=${var} ${var1}
    Log    ${var}
    ${var}=    Evaluate    ${var}
    Log    ${var}
    Log    ${bar}