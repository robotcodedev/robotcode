*** Settings ***
Library     Collections

*** Variables ***
${A VAR}        i'm a var
&{A DICT}       a=1    b=2    c=3

*** Test Cases ***
first
    Log    Hello ${A VAR}
    Collections.Log Dictionary    ${A DICT}
    FOR    ${key}    ${value}    IN    &{A DICT}
        Log    ${key}=${value}
    END
    Log    ${CMD_VAR}
