*** Settings ***
Library         Collections
#               ^^^^^^^^^^^ a builtin library
Library         ${CURDIR}/../lib/myvariables.py
#                 ^^^^^^  Variable in library import path
#                             ^^^^^^^^^^^^^^ a custom library with path
Variables       ${CURDIR}/../lib/myvariables.py
#                 ^^^^^^  Variable in variables import path
#                                ^^^^^^^^^^^^^^ a variable import
Resource        ${CURDIR}/../resources/firstresource.resource
#                 ^^^^^^  Variable in resource import path
Library         alibrary    a_param=from hello    WITH NAME    lib_hello
#               ^^^^^^^^ a custom library
Library         alibrary    a_param=${LIB_ARG}    WITH NAME    lib_var
#                                     ^^^^^^^  Variable in library params
#               ^^^^^^^^ a same custom library
Suite Setup    BuiltIn.Log To Console    hi from suite setup
#                      ^^^^^^^^^^^^^^  suite fixture keyword call with namespace
Test Setup    Log To Console    hi from test setup
#             ^^^^^^^^^^^^^^  test fixture keyword call with namespace

*** Variables ***
${a var}    hello
# ^^^^^ simple variable
${LIB_ARG}    from lib
# ^^^^^^^ another simple var
${bananas}    apples
${🧨🧨}    🎉🎉
# ^^^^^ a var with emoji

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
#    ^^^^^^^    Keyword reassignment with equals sign
    Should Be Equal    ${result}   ${LIB_ARG}
#                        ^^^^^^    Keyword variable reference


fifth
    [Setup]    do something test setup inner
#              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  Embedded keyword in setup
    [Teardown]    do something test teardown inner
#                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  Embedded keyword in teardown
    do something    cool
    do something cool from keyword
#   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  Embedded keyword

    add 2 coins to pocket
#   ^^^^^^^^^^^^^^^^^^^^^  Embedded keyword with regex only numbers

    add 22134 coins to pocket
#   ^^^^^^^^^^^^^^^^^^^^^^^^^  Embedded keyword with regex only numbers
    add milk and coins to my bag
#   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^  Embedded keyword with regex a to z an space

    do add ${bananas} and to my bag
#   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  Embedded keyword with variable

    do add ${🧨🧨} and to my bag
#   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  Embedded keyword with emojii variable

    add bananas to pocket
#   ^^^^^^^^^^^^^^^^^^^^^  Ambiguous Embedded keyword with regex a to z
    add bananas to pocket    # robotcode: ignore
#   ^^^^^^^^^^^^^^^^^^^^^  Invalid Embedded keyword with regex a to z ignored
    add bananas and apples to pocket
#   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  Embedded keyword with regex a to z and space

    add bananas and apples to 🦼🛹🛼
#   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  Embedded keyword with emoji


sixth
    🤖🤖  🐓=🥴🥶
#   ^^^^ a keyword with emoji
    firstresource.🤖🤖  🐓=${🧨🧨}    🧟‍♂️🛃🫅🏿👸🏿=${🧨🧨}+${🧨🧨}  #  test
#   ^^^^^^^^^^^^^^^^^^  a keyword with namespace and emoji
#                           ^^^^^^  a variable with emoji


*** Keywords ***
do something ${type}
    do something     ${type}

do something
    [Arguments]    ${type}
    Log    done ${type}

add ${number:[0-9]+} coins to ${thing}
#^^  Embedded keyword
#     ^^^^^^  Embedded keyword
    Log    added ${number} coins to ${thing}
#                  ^^^^^^ embedded argument usage
#                                     ^^^^^ embedded argument usage

add ${what:[a-zA-Z]+} to ${thing}
#^^  Embedded keyword
    Log    this is duplicated
    Log    added ${what} to ${thing}

add ${what:[a-zA-Z]+} to ${thing}
#^^  Embedded keyword
    Log    added ${what} coins to ${thing}

add ${what:[a-zA-Z ]+} to ${thing}
#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  Embedded keyword
    Log    added ${what} coins to ${thing}

do add ${bananas} and to my bag
#^^  Embedded keyword
    Log    ${bananas}

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
    [Arguments]    ${a}    ${b}=${a}
#                    ^ an argument
#                            ^ another argument
#                                 ^ argument usage in argument
    Log    ${a}
#            ^ argument usage
    Log    ${b}
#            ^ argument usage
