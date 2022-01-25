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