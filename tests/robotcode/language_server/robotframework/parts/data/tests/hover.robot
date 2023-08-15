*** Settings ***
Library           Collections
#                 ^^^^^^^^^^^ library import by module name
Library           alibrary    a_param=from hello    WITH NAME    lib_hello
#                                                                ^^^^^^^^^  lib with alias
Library           alibrary    a_param=${LIB_ARG}    WITH NAME    lib_var
#                                       ^^^^^^^  Variable in library params
Library           ${CURDIR}/../lib/myvariables.py
#                                  ^^^^^^^^^^^^^^ library import by path name
#                   ^^^^^^  variable in library import
Variables         ${CURDIR}/../lib/myvariables.py
#                   ^^^^^^  variable in variables import
#                                  ^^^^^^^^^^^^^^ variable import by path name
Resource          ${CURDIR}/../resources/firstresource.resource
#                                       ^^^^^^^^^^^^^^ resource import by path name
#                   ^^^^^^  variable in resource import
Resource          ../resources/folder_a/duplicated.resource
Resource          ../resources/folder_b/duplicated.resource

Library        UnknownLibrary    WITH NAME    unknown
#              ^^^^^^^^^^^^^^  unknown lib
#                                             ^^^^^^^^  unknown lib namespace
Library        LibraryWithErrors    True    WITH NAME    errorlib
#              ^^^^^^^^^^^^^^^^^  lib with errors
#                                                        ^^^^^^^^  lib with errors alias
Library        LibraryWithErrors    False    WITH NAME    noerrorlib
#              ^^^^^^^^^^^^^^^^^  lib with no errors
#                                                         ^^^^^^^^^^  lib with no errors alias

*** Variables ***
${A VAR}=          i'm a var
# ^^^^^  variable declaration
#       ^ not the equal sign
&{A DICT}         a=1    b=2    c=3
# ^^^^^^  variable declarations

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
#                            ^  outer var
#                                   ^  extra var

${D}    3
${E}    SEPARATOR=\n    asd    def    hij
${F}    ${1+2}
# ^  number variable
#         ^^^  number expression
*** Test Cases ***
first
    [Tags]
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
#           ^^^^ FOR loop variable declaration
        Log    ${key}=${value}
#       ^^^ Keyword in FOR loop
    END
    Log    ${CMD_VAR}
#            ^^^^^^^    Command line variable
#   ^^^ BuiltIn Keyword
    Log    ${CURDIR}
#            ^^^^^^    BuiltIn variable
#^^^    Spaces
    Log    ${A_VAR_FROM_LIB}
#            ^^^^^^^^^^^^^^    variable from lib

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
#     ^^^^^^    Keyword assignement
    Should Be Equal    ${result}   from hello
    ${result}=    lib_var.A Library Keyword
    ${result}=    lib_var.A Library Keyword
#     ^^^^^^    Keyword assignment with equals sign
    Should Be Equal    first=${result}   second=${LIB_ARG}

forth
    Run Keyword If    ${True}
    ...    Log    ${Invalid var        # robotcode: ignore
    ...  ELSE
    ...    Unknown keyword  No  # robotcode: ignore

sixth
    IF  ${A}
#         ^    variable in if
        Log    Yeah
    ELSE IF    ${B}
#                ^    variable in else if
        Log    No
    END

    IF  $a
#        ^    variable in if expression
        Log    Yeah
    ELSE IF    $b
#               ^    variable in else if expression
        Log    No
    END

    IF  ${A}    log    hi    ELSE IF    ${b}    log  ho    ELSE    log  ro
#         ^    variable in inline if expression
#                                         ^    variable in inline else if expression

    IF  $a    log    hi    ELSE IF    $b    log  ho    ELSE    log  ro
#        ^    variable in inline if expression
#                                      ^    variable in inline else if expression

seventh
    [Setup]    Given log    setup
#              ^^^^^ BDD Given in setup
#                    ^^^ BDD Keyword in setup
    [Teardown]    Then BuiltIn.log    teardown
#                 ^^^^ BDD Then in Teardown
#                      ^^^^^^^ BDD Namespace in Teardown
#                              ^^^ BDD Keyword in Teardown
    Given log    hi
#   ^^^^^ BDD Given
#         ^^^  BDD Given keyword
    When log  hi
#   ^^^^ BDD When
#        ^^^  BDD When keyword
    And log  hi
#   ^^^ BDD And
#       ^^^  BDD And keyword
    Then log  ho
#   ^^^^ BDD Then
#       ^^^  BDD Then keyword
    But log  ho
#   ^^^ BDD But
#       ^^^  BDD But keyword
    given builtin.log    1
#   ^^^^^  BDD given with namespace
#         ^^^^^^^  BDD namespace with namespace
#                 ^^^  BDD keyword with namespace

    Given Run Keyword if  1    given log   hello  ELSE IF  2  log  haha  ELSE  log  huhu
#                                    ^^^  BDD Given in run keyword
#                                                             ^^^  BDD Given in run keyword
#                                                                              ^^^  BDD Given in run keyword

    Given BuiltIn.Run Keyword if  ${True}    given BuiltIn.log   hello
#                                                  ^^^^^^^  BDD Given namespace in run keyword with namespace
#                                                          ^^^  BDD Given keyword in run keyword with namespace

seventh1
    [Template]    given log
    1
    2

eight
    do.sell fish
#   ^^^^^^^^^^^^  keyword with dot
    firstresource.do.sell fish
#                 ^^^^^^^^^^^^  keyword with dot after namespace
#   ^^^^^^^^^^^^^  namespace in keyword with dot

nineth
    a resource keyword A
#   ^^^^^^^^^^^^^^^^^^^^  duplicated keyword a
    a resource keyword B
#   ^^^^^^^^^^^^^^^^^^^^  duplicated keyword b
    duplicated keyword
#   ^^^^^^^^^^^^^^^^^^  duplicated keyword
    duplicated.a resource keyword A
#   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  duplicated keyword a with namespace
    duplicated.a resource keyword B
#   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  duplicated keyword b with namespace
    duplicated.duplicated keyword
#   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  duplicated keyword with namespace

tenth
    🤖🤖    🥴🥶
#   ^^ a keyword with emoji

eleventh
    unknown.this is an error
#   ^^^^^^^  namespace of unknown lib
#           ^^^^^^^^^^^^^^^^  keyword of unknown lib
    unknown.this is another error
#   ^^^^^^^  namespace of unknown lib
#           ^^^^^^^^^^^^^^^^^^^^^  keyword of unknown lib
    errorlib.A Library Keyword
#   ^^^^^^^^  namespace of lib with error
#            ^^^^^^^^^^^^^^^^^  keyword of lib with error
    noerrorlib.A Library Keyword
#   ^^^^^^^^^^  namespace of lib with no error
#              ^^^^^^^^^^^^^^^^^  keyword of lib with no error
    n o e r r o r l i b.A Library Keyword
#   ^^^^^^^^^^^^^^^^^^^  namespace of lib with no error with spaces
#                       ^^^^^^^^^^^^^^^^^  keyword of lib with no error with spaces

twelfth
    firstresource.a keyword with args    a=2    a long name=99    a_short_name=342
#                                        ^  short keyword argument
#                                               ^^^^^^^^^^^  keyword argument with spaces
#

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
    Pass Execution    passed

sleep a while
    S l e e p    1s
#   ^^^^^^^^^  simple keyword with extra spaces and parameter

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

a keyword with try except
    TRY
        Fail    Does not work
    EXCEPT  AS  ${e}
        Log    ${e}
    END