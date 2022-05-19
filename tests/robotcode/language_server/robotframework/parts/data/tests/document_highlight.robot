*** Settings ***
Library         Collections
Library         ${CURDIR}/../lib/myvariables.py
#                 ^^^^^^  Variable in library import path
Variables       ${CURDIR}/../lib/myvariables.py
#                 ^^^^^^  Variable in variables import path
Resource        ${CURDIR}/../resources/firstresource.resource
#                 ^^^^^^  Variable in resource import path
Library         alibrary    a_param=from hello    WITH NAME    lib_hello
Library         alibrary    a_param=${LIB_ARG}    WITH NAME    lib_var
#                                   ^^^^^^^^^^  Variable in library params

Suite Setup    BuiltIn.Log To Console    hi from suite setup
#                      ^^^^^^^^^^^^^^  suite fixture keyword call with namespace
Test Setup    Log To Console    hi from test setup
#             ^^^^^^^^^^^^^^  test fixture keyword call with namespace

*** Variables ***
${a var}    hello
# ^^^^^ simple variable
${LIB_ARG}    from lib
# ^^^^^^ another simple var


*** Test Cases ***
first
    [Setup]    Log To Console    hi ${a var}
#              ^^^^^^^^^^^^^^  fixture keyword call
    [Teardown]    BuiltIn.Log To Console    hi ${a var}
#                         ^^^^^^^^^^^^^^  fixture keyword call with namespace
    Log    Hi ${a var}
#   ^^^  simple keyword call
    Log To Console    hi ${a var}
#   ^^^^^^^^^^^^^^  multiple references
    BuiltIn.Log To Console    hi ${a var}
#           ^^^^^^^^^^^^^^  multiple references with namespace
#                                  ^^^^^  multiple variables
    Log    ${A_VAR_FROM_RESOURE}
#            ^^^^^^^^^^^^^^^^^^ a var from resource

second
    [Template]    Log To Console
#                 ^^^^^^^^^^^^^^  template keyword
    Hi
    There

third
    [Template]    BuiltIn.Log To Console
#                         ^^^^^^^^^^^^^^  template keyword with namespace
    Hi
    There

forth
    ${result}    lib_hello.A Library Keyword
#     ^^^^^^    Keyword assignement
    Should Be Equal    ${result}   from hello
    ${result}=    lib_var.A Library Keyword
#     ^^^^^^    Keyword assignment with equals sign
    Should Be Equal    ${result}   ${LIB_ARG}


fifth
    a keyword with params
    another keyword with params    1
    again a keyword with params    1
    a keyword with args    a=2    a long name=99    a_short_name=342

*** Keywords ***
a keyword with params
    [Arguments]    ${A VAR}=${A VAR}
#                    ^^^^^ another argument
#                             ^^^^^ a default value
    Log    ${tt}
#            ^^ argument usage
    Log    ${A VAR}
#            ^^^^^ argument usage

another keyword with params
    [Arguments]    ${tt}    ${A VAR}=${A VAR}
#                    ^^ an argument
#                             ^^^^^ another argument
#                                      ^^^^^ a default value
    Log    ${tt}
#            ^^ argument usage
    Log    ${A VAR}
#            ^^^^^ argument usage

again a keyword with params
    [Arguments]    ${a}    ${b}=${a}    ${c}=${b}
#                    ^ an argument
#                            ^ another argument
#                                 ^ argument usage in argument
    Log    ${a}
#            ^ argument usage
    Log    ${b}
#            ^ argument usage
    Log    ${c}
#            ^ argument usage

    Run Keyword If    ${a}    Should Be Equal    ${b}    ${c}
    Run Keyword If    $a    Should Be Equal    ${{$c}}    ${c}
    Run Keyword If    ${a}    run keyword    ${b}    ${{$c}}


add ${number:[0-9]+} coins to ${thing}
#     ^^^^^^  Embedded keyword
    Log    added ${number} coins to ${thing}
#                  ^^^^^^ embedded argument usage
#                                     ^^^^^ embedded argument usage
