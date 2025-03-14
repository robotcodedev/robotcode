*** Settings ***
#^^^^^^^^^^^^^^^ settings section
Library    Collections

*** Variables ***
#^^^^^^^^^^^^^^^ variables section
${A_VAR}    1
#^^^^^^^  variable in variables section

*** Test Cases ***
#^^^^^^^^^^^^^^^^^ test cases
first
#^^^^ testcase
    ${kw_result}    Evaluate    1+2
#     ^^^^^^^^^    keyword assignment

    ${kw_result}    ${kw_result1}    Evaluate    (1+2, 2+3)
#     ^^^^^^^^^    keyword assignment allready defined
#                     ^^^^^^^^^^    multiple keyword assigns
    VAR  ${local_var}    1
#          ^^^^^^^^^    local var RF 7
    FOR  ${loop_var}  IN  1    2    3
#          ^^^^^^^^    loop var
        Log    ${loop_var} ${kw_result}
    END

    TRY
        Fail    message
    EXCEPT  message    AS    ${exc}
#                              ^^^  exception variable
        Log    do nothing ${exc}
    END
    another keyword

*** Comments ***
#^^^^^^^^^^^^^^^ comments section

*** Keywords ***
#^^^^^^^^^^^^^^^ keywords section
a keywords
#^^^^^^^^^ keyword
    [Arguments]    ${first}    ${second}
#                    ^^^^^ first argument
#                                ^^^^^^ second argument
*** Keywords ***
#^^^^^^^^^^^^^^^ another keywords section
another keyword
#^^^^^^^^^^^^^^ another keyword
    [Documentation]    *DEPRECATED!!* - this keyword is deprecated
    No Operation

*** Test Cases ***
    # test case with no name
#^^^ unreachable test
    Unreachable

*** Keywords ***
    # keyword with no name
#^^^ unreachable keyword

    Unreachable

*** Test Cases ***
vars with equal sign
    VAR  ${var 1}=    1
#          ^^^^^  variable with space and equal sign
    VAR  ${var 2} =    1
#          ^^^^^ variable with space and equal sign
    ${var 1}=  Evaluate    1+2
#     ^^^^^ variable with space and equal sign
