*** Settings ***
Library           Collections
#                 ^^^^^^^^^^^ library import by module name
Library           alibrary    a_param=from hello    WITH NAME    lib_hello
Library           alibrary    a_param=${LIB_ARG}    WITH NAME    lib_var
#                                      ^^^^^^^^  Variable in library params
Library           ${CURDIR}/../lib/myvariables.py
#                                  ^^^^^^^^^^^^^^ library import by path name
#                   ^^^^^^  variable in library import
Variables         ${CURDIR}/../lib/myvariables.py
#                   ^^^^^^  variable in variables import
#                                  ^^^^^^^^^^^^^^ variable import by path name
Resource          ${CURDIR}/../resources/firstresource.resource
#                                       ^^^^^^^^^^^^^^ resource import by path name
#                   ^^^^^^^  variable in resource import

*** Variables ***
${A VAR}=          i'm a var
# ^^^^^  variable declaration
#       ^ not the equal sign
&{A DICT}         a=1    b=2    c=3
# ^^^^^^  variable declaration

${LIB_ARG}    from lib

${INVALID VAR ${}}    2
# ^^^^^^^^^^^^^^^  no hover for invalid variable

${A}=    1
${B}    2
${C}    ${A + '${B+"${D}"}'}
#         ^  complex var expression
#                ^  inner var
#                     ^  inner inner var

${K}    ${A+'${B+"${F}"}'+'${D}'} ${C}
#         ^  complex var expression
#             ^  inner var
#                 ^  inner var
#                     ^  inner inner var
#                             ^  outer var

${D}    3
${E}    SEPARATOR=\n    asd    def    hij
${F}    ${1+2}
# ^  number variable
#         ^^^  number expression
*** Test Cases ***
first
    [Setup]  Log    Hello ${A VAR}
#            ^^^ Keyword in Setup
    [Teardown]  BuiltIn.Log    Hello ${A VAR}
#                       ^^^ Keyword in Teardown
#               ^^^^^^^ Namespace in Teardown
    Log    ${E}
    Log    ${EMPTY}
    Log    ${EMPTY+'1'}
    Log    ${INVALID VAR ${}}
#           ^^^^^^^^^^^^^^^^  no hover for invalid variable reference

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

second
#^^^^^ Test Case
    [Template]    BuiltIn.Log
#                         ^^^ Keyword in Template
#                 ^^^^^^^ Namespace in Template
    hello
    world

third
    ${result}    lib_hello.A Library Keyword
#   ^^^^^^^^^    Keyword assignement
    Should Be Equal    ${result}   from hello
    ${result}=    lib_var.A Library Keyword
#   ^^^^^^^^^    Keyword assignment with equals sign
    Should Be Equal    ${result}   ${LIB_ARG}

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
