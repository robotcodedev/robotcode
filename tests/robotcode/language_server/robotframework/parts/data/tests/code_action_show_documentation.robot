*** Settings ***
Library         Collections
#               ^^^^^^^^^^^ built-in library
Library         myvariables
#               ^^^^^^^^^^^ user library
Library         ${CURDIR}/../lib/myvariables.py
#               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ user library by path with variable
Variables       ${CURDIR}/../lib/myvariables.py
Resource        firstresource.resource
#               ^^^^^^^^^^^^^^^^^^^^^^ resource
Resource        ${CURDIR}/../resources/firstresource.resource
#               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ resource by path with variable
Library         alibrary    a_param=from hello    WITH NAME    lib_hello
#               ^^^^^^^^ user library with arguments
Library         alibrary    a_param=${LIB_ARG}    WITH NAME    lib_var
#               ^^^^^^^^ user library with arguments and variable
Suite Setup    BuiltIn.Log To Console    hi from suite setup
#              ^^^^^^^^^^^^^^^^^^^^^^ keyword call from built-in library with namespace in Test Setup
Test Setup    Log To Console    hi from test setup
#             ^^^^^^^^^^^^^^ keyword call from built-in library in Test Setup

*** Variables ***
${a var}    hello
${LIB_ARG}    from lib
${bananas}    apples

*** Test Cases ***
first
    [Setup]    Log To Console    hi ${a var}
#              ^^^^^^^^^^^^^^ keyword call from built-in library in setup
    [Teardown]    BuiltIn.Log To Console    hi ${a var}
#                 ^^^^^^^^^^^^^^^^^^^^^^ keyword call from built-in library in teardown
    Log    Hi ${a var}
#   ^^^ keyword from built-in library
    Log To Console    hi ${a var}
    BuiltIn.Log To Console    hi ${a var}
#   ^^^^^^^^^^^^^^^^^^^^^^ keyword call from built-in library with namespace
    Log    ${A_VAR_FROM_RESOURE}

second
    [Template]    Log To Console
#                 ^^^^^^^^^^^^^^ keyword call from built-in library in template
    Hi
    There

third
    [Template]    BuiltIn.Log To Console
#                 ^^^^^^^^^^^^^^^^^^^^^^ keyword call from built-in library with namespace in template
    Hi
    There

forth
    ${result}    lib_hello.A Library Keyword
#                ^^^^^^^^^^^^^^^^^^^^^^^^^^^ keyword call from user library with namespace in assignment
    Should Be Equal    ${result}   from hello
    ${result}=    lib_var.A Library Keyword
#                 ^^^^^^^^^^^^^^^^^^^^^^^^^ keyword call from user library with namespace in assignment from different library
    Should Be Equal    ${result}   ${LIB_ARG}


fifth
    [Setup]    do something test setup inner
#              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ keyword call with embedded arguments in setup
    [Teardown]    do something test teardown inner
#                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ keyword call with embedded arguments in teardown
    do something    cool
#   ^^^^^^^^^^^^ keyword call normal arguments in test case
    do something cool from keyword
#   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ keyword call embedded arguments in test case

    add 2 coins to pocket
#   ^^^^^^^^^^^^^^^^^^^^^ keyword call with embedded arguments

    add 22134 coins to pocket
    add milk and coins to my bag

    do add ${bananas} and to my bag
#   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ keyword call with embedded arguments and variable

    add bananas to pocket
#   ^^^^^^^^^^^^^^^^^^^^^ error multiple keywords
    add bananas to pocket    # robotcode: ignore
#   ^^^^^^^^^^^^^^^^^^^^^ error multiple keywords ignored
    add bananas and apples to pocket
    add bananas and apples to pocket

*** Keywords ***
do something ${type}
#^^^^^^^^^^^^^^^^^^^ keyword definition with embedded arguments
    do something     ${type}

do something
#^^^^^^^^^^^ keyword definition
    [Arguments]    ${type}
    Log    done ${type}
#   ^^^ keyword call in keyword definition

add ${number:[0-9]+} coins to ${thing}
#^^^^^^^^^^^^^^^^^^^ keyword definition with embedded arguments and regex
     Log    added ${number} coins to ${thing}

add ${what:[a-zA-Z]+} to ${thing}
    Log    this is duplicated
    Log    added ${what} to ${thing}

add ${what:[a-zA-Z]+} to ${thing}
    Log    added ${what} coins to ${thing}

add ${what:[a-zA-Z ]+} to ${thing}
    Log    added ${what} coins to ${thing}

do add ${bananas} and to my bag
    Log    ${bananas}

a keyword with params
    [Arguments]    ${A VAR}=${A VAR}
    Log    ${tt}
    Log    ${A VAR}

another keyword with params
    [Arguments]    ${tt}    ${A VAR}=${A VAR}
    Log    ${tt}
    Log    ${A VAR}

again a keyword with params
    [Arguments]    ${a}    ${b}=${a}
    Log    ${a}
    Log    ${b}
