*** Settings ***
Library           alibrary    a_param=brumm    WITH NAME    res_lib_var

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
    res_lib_var.A Library Keyword
    res_lib_var.A Library Keywords With Args


a keyword with args
    [Arguments]    ${a}    ${a long name}=    ${a_short_name}=default
    No Operation

🤖🤖
    [Documentation]    this is a keyword with emoji in the name
    ...
    ...    and some more documentation with 🚎🚐🚓🛺🚙🛻🚖🛴🚲🛼🛹🦼🦽
    [Arguments]    ${🐓}    ${😎😋😙😙}=    ${🧟‍♂️🛃🫅🏿👸🏿}=🧨✨🎉👔
    Log    hello from 🤖🤖 ${🐓} ${😎😋😙😙} ${🧟‍♂️🛃🫅🏿👸🏿}
