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
#                 ^^^^^^ var in Libary import path
#                                                        ^^^^^^^  var in library parameters

*** Variables ***
${A VAR}          i'm a var
&{A DICT}         a=1    b=2    c=3
${LIB_ARG}    from lib
${DOT}    .


*** Test Cases ***
first
    Log    Hello ${A VAR}
#                 ^^^^^^^  Variable
#   ^^^  BuiltIn Keyword

    Collections.Log Dictionary    ${A DICT}
#                                 ^^^^^^^^^  Variable
#               ^^^^^^^^^^^^^^  Robot Library Keyword
#   ^^^^^^^^^^^ Robot Namespace from Library

    BuiltIn.Log    Hello ${A VAR}
#           ^^^  BuiltIn Keyword with Namespace
#   ^^^^^^^ Robot BuilIn Namespace

    FOR    ${key}    ${value}    IN    &{A DICT}
        Log    ${key}=${value}
#              ^^^^^^  For Variable
#                     ^^^^^^^^  For Variable
    END
    Log    ${A_VAR_FROM_LIB}
#          ^^^^^^^^^^^^^^^^^  Imported Variable

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


*** Keywords ***
a simple keyword
#^^^^^^^^^^^^^^^ a simple keyword
    Log    hello