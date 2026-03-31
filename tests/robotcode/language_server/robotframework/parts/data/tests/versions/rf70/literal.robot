*** Settings ***
Library    literal_tester

*** Test Cases ***
first
    A Keyword With Literal    q    v

second
    Test Literal    b

*** Keywords ***
A Keyword With Literal
    [Arguments]    ${a: Literal["q", "b"]}    ${b: Literal["x", "y"] | int}
    do something  ${a}
    do something  ${b}