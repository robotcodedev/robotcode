*** Settings ***
Library           Collections
#                 ^^^^^^^^^^^  Robot Library Import
#      ^^^^^^^^^^^  Separator
Library           ${CURDIR}/../lib/myvariables.py
#                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  library import by path
Variables         ${CURDIR}/../lib/myvariables.py
#                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  Variables Import
Resource          ${CURDIR}/../resources/firstresource.resource
#                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  built in var in Resource Import

Library           ${DOT}/../lib/alibrary.py    a_param=${LIB_ARG}    WITH NAME    lib_var
#                   ^^^ var in Libary import path
#                                                        ^^^^^^^  var in library parameters

*** Variables ***
${A VAR}          i'm a var
&{A DICT}         a=1    b=2    c=3
${LIB_ARG}    from lib
# ^^^^^^^  Var declaration
${DOT}    .
# ^^^  Var declaration
@{list_var}    1    2    3
# ^^^^^^^^  List Var declaration
&{dict_var}    first=1    second=3
# ^^^^^^^^  Dict Var declaration

${all together}    ${A VAR} @{list var} ${dictvar}
#                    ^^^^^ var usage
#                             ^^^^^^^^ var usage
#                                         ^^^^^^^ var usage
${A}=    1
${B}     2

*** Test Cases ***
first
    Log    Hello ${A VAR}
#                  ^^^^^  Variable
#   ^^^  BuiltIn Keyword

    Log    @{list_var}
#            ^^^^^^^^  List Var
    Log    ${list_var}
#            ^^^^^^^^  List Var as normal var

    Log    @{dict_var}
#            ^^^^^^^^  Dict Var
    Log    ${dict_var}
#            ^^^^^^^^  Dict Var as normal var

    Log    ${all together}

    Collections.Log Dictionary    ${A DICT}
#                                   ^^^^^^  Variable
#               ^^^^^^^^^^^^^^  Robot Library Keyword
#   ^^^^^^^^^^^ Robot Namespace from Library

    BuiltIn.Log    Hello ${A VAR}
#           ^^^  BuiltIn Keyword with Namespace
#   ^^^^^^^ Robot BuilIn Namespace

    FOR    ${key}    ${value}    IN    &{A DICT}
#            ^^^  For Variable
#                      ^^^^^  For Variable
        Log    ${key}=${value}
#                ^^^  For Variable
#                       ^^^^^  For Variable
    END
    Log    ${A_VAR_FROM_LIB}
#            ^^^^^^^^^^^^^^  Imported Variable

    do something in a resource
#   ^^^^^^^^^^^^^^^^^^^^^^^^^^  Keyword from resource

    firstresource.do something in a resource
#                 ^^^^^^^^^^^^^^^^^^^^^^^^^^  Keyword from resource
#   ^^^^^^^^^^^^^  Namespace from resource
    a simple keyword
#   ^^^^^^^^^^^^^^^^  call a simple keyword
    an unknown keyword
#   ^^^^^^^^^^^^^^^^^^  unknown keyword

second
    [Setup]    Log  hello setup
#              ^^^ a keyword in setup
    [Teardown]    BuiltIn.Log  hello teardown
#                         ^^^ a keyword in teardown
#                 ^^^^^^^ a namespace in teardown

a templated Test
    [Template]    BuiltIn.Log
#                         ^^^ a keyword in template
#                 ^^^^^^^ a namespace in template
    hello
    world

third
    just another keyword with params

forth
    🤖🤖    🥴🥶
#   ^^ a keyword with emoji

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

*** Keywords ***
a simple keyword
#^^^^^^^^^^^^^^^ a simple keyword
    Log    hello


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

just another keyword with params
    [Arguments]    ${tt}    ${A VAR1}=${tt}    ${tt}=${A VAR1}
#                    ^^ an argument
#                             ^^^^^^ another argument
#                                      ^^ a default value
#                                               ^^ an overridden argument
#                                                     ^^^^^ a default value from overriden argument
    Log    ${tt}
#            ^^ argument usage
    Log    ${A VAR1}
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
