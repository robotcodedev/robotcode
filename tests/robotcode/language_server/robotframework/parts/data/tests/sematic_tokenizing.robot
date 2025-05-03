*** Settings ***
Resource    embedded_args.resource

*** Test Cases ***
Continue when iteration limit is reached
    WHILE    True    limit=5    on_limit=pass
        do something    Loop will be executed five times
    END
    do something    This will be executed normally.

Limit as iteration count
    WHILE    True    limit=0.5s    on_limit_message=Custom While loop error message
        do something    This is run 0.5 seconds.
    END

some templated
    [Template]    template
    1    2    3
    3    ${{1+2+${1}}}    7

some embedded args keywords
    do task with thing
    embedded_args.do task with thing   

*** Keywords ***
do something
    [Arguments]    ${type}
    ok


template
    [Arguments]    ${a}    ${b}    ${c}
    # TODO: implement keyword "template".
    ok  ${a} ${b} ${c}
