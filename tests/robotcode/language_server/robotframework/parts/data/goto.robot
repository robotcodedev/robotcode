*** Settings ***
Library           Collections
#                 ^^^^^^^^^^^  Robot Library Import
#      ^^^^^^^^^^^  Separator
Library           ${CURDIR}/libs/myvariables.py
#                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  Library Import by Path
Variables         ${CURDIR}/libs/myvariables.py
#                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  Variables Import
Resource          ${CURDIR}/resources/firstresource.resource
#                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  Resource Import

*** Variables ***
${A VAR}          i'm a var
&{A DICT}         a=1    b=2    c=3

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