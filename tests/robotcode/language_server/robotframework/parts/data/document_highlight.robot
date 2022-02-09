*** Settings ***
Library         Collections
Library         ${CURDIR}/lib/myvariables.py
#               ^^^^^^^^^  Variable in library import path
Variables       ${CURDIR}/lib/myvariables.py
#               ^^^^^^^^^  Variable in variables import path
Resource        ${CURDIR}/resources/firstresource.resource
#               ^^^^^^^^^  Variable in resource import path
Library         alibrary    a_param=from hello    WITH NAME    lib_hello
Library         alibrary    a_param=${LIB_ARG}    WITH NAME    lib_var
#                                   ^^^^^^^^^^  Variable in library params

Suite Setup    BuiltIn.Log To Console    hi from suite setup
#                      ^^^^^^^^^^^^^^  suite fixture keyword call with namespace
Test Setup    Log To Console    hi from test setup
#             ^^^^^^^^^^^^^^  test fixture keyword call with namespace

*** Variables ***
${a var}    hello
${LIB_ARG}    from lib


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
#   ^^^^^^^^^    Keyword assignement
    Should Be Equal    ${result}   from hello
    ${result}=    lib_var.A Library Keyword
#   ^^^^^^^^^    Keyword assignment with equals sign
    Should Be Equal    ${result}   ${LIB_ARG}
