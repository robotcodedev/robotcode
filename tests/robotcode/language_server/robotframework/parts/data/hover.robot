*** Settings ***
Library           Collections
#                 ^^^^^^^^^^^ library import by module name
Library           ${CURDIR}/libs/myvariables.py
#                               ^^^^^^^^^^^^^^ library import by path name
#                 ^^^^^^^^^  variable in library import
Variables         ${CURDIR}/libs/myvariables.py
#                 ^^^^^^^^^  variable in variables import
#                                ^^^^^^^^^^^^^^ variable import by path name
Resource          ${CURDIR}/resources/firstresource.resource
#                                     ^^^^^^^^^^^^^^ resource import by path name
#                 ^^^^^^^^^  variable in resource import

*** Variables ***
${A VAR}          i'm a var
#^^^^^^^          variable declaration
&{A DICT}         a=1    b=2    c=3
#^^^^^^^          variable declaration

*** Test Cases ***
first
    [Setup]  Log    Hello ${A VAR}
#            ^^^ Keyword in Setup
    [Teardown]  Log    Hello ${A VAR}
#               ^^^ Keyword in Teardown

    Log    Hello ${A VAR}
#   ^^^ Keyword from Library

    Collections.Log Dictionary    ${A DICT}
#               ^^^^^^^^^^^^^^ Keyword with namespace
#   ^^^^^^^^^^^ namespace before keyword
    FOR    ${key}    ${value}    IN    &{A DICT}
#          ^^^^^^ FOR loop variable declaration
        Log    ${key}=${value}
#       ^^^ Keyword in FOR loop
    END
    Log    ${CMD_VAR}
#          ^^^^^^^^^^    BuiltIn variable
#   ^^^ BuiltIn Keyword
    Log    ${CURDIR}
#          ^^^^^^^^^    BuiltIn variable
#^^^    Spaces
    Log    ${A_VAR_FROM_LIB}
#          ^^^^^^^^^^^^^^^^^    variable from lib

    do something in a resource
#   ^^^^^^^^^^^^^^^^^^^^^^^^^^  Keyword from resource

    firstresource.do something in a resource
#                 ^^^^^^^^^^^^^^^^^^^^^^^^^^  KeywordCall from resource with Namespace
#   ^^^^^^^^^^^^^  Namespace from resource


*** Keywords ***
a keyword
    Run Keyword    log    hi
#   ^^^^^^^^^^^  run keyword
#                  ^^^  run keyword argument

    Run Keywords    a simple keyword    s l e e p a w h i le
#   ^^^^^^^^^^^^  run keywords
#                   ^^^^^^^^^^^^^^^^  run keywords simple keyword
#                                       ^^^^^^^^^^^^^^^^^^^^  run keywords second parameter with spaces

    Run Keywords    log  hi  AND  a simple keyword  AND  s l e e p a w h i le
#   ^^^^^^^^^^^^  run keywords
#                   ^^^  run keywords simple keyword, parameter and AND
#                                 ^^^^^^^^^^^^^^^^  run keywords simple keyword and AND
#                                                        ^^^^^^^^^^^^^^^^^^^^  run keywords second parameter with spaces and no AND
#                            ^^^    AND

a simple keyword
#^^^^^^^^^^^^^^^  simple keyword with extra spaces and parameter
    Pass Execution

sleep a while
    S l e e p    1s
#   ^^^^^^^^^  simple keyword with extra spaces and parameter
