*** Variables ***
${A_VAR_FROM_RESOURE}       hello from resource

*** Keywords ***
do something in a resource
    Log    done something

do.sell fish
    Log    message


some failing keyword
    Log    hello from failing
    Fail    ho
    Log    end failing


a keyword with args
    [Arguments]    ${a}    ${a long name}=    ${a_short_name}=default
    No Operation
