*** Settings ***
Library           Collections
#                 ^^^^^^^^^^^  Robot Library Import: len(result) == 1 and result[0].target_uri.endswith("robot/libraries/Collections.py")
#      ^^^^^^^^^^^  Separator: result is None or len(result) == 0
Library           ${CURDIR}/libs/myvariables.py
#                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  Library Import by Path: len(result) == 1 and result[0].target_uri.endswith("/libs/myvariables.py")
Variables         ${CURDIR}/libs/myvariables.py
#                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  Variables Import: len(result) == 1 and result[0].target_uri.endswith("libs/myvariables.py")
Resource          ${CURDIR}/resources/firstresource.resource
#                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  Resource Import: len(result) == 1 and result[0].target_uri.endswith("/resources/firstresource.resource")

*** Variables ***
${A VAR}          i'm a var
&{A DICT}         a=1    b=2    c=3

*** Test Cases ***
first
    Log    Hello ${A VAR}
#                 ^^^^^^^  Variable: len(result) == 1 and result[0].target_uri.endswith("/data/goto.robot")
#   ^^^  BuiltIn Keyword: len(result) == 1 and result[0].target_uri.endswith("robot/libraries/BuiltIn.py")
    Collections.Log Dictionary    ${A DICT}
#                                 ^^^^^^^^^  Variable: len(result) == 1 and result[0].target_uri.endswith("/data/goto.robot")
#               ^^^^^^^^^^^^^^  Robot Library Keyword: len(result) == 1 and result[0].target_uri.endswith("robot/libraries/Collections.py")
    FOR    ${key}    ${value}    IN    &{A DICT}
        Log    ${key}=${value}
#              ^^^^^^  For Variable: len(result) == 1 and result[0].target_uri.endswith("/data/goto.robot")
#                     ^^^^^^^^  For Variable: len(result) == 1 and result[0].target_uri.endswith("/data/goto.robot")
    END
    Log    ${A_VAR_FROM_LIB}
#          ^^^^^^^^^^^^^^^^^  Imported Variable: len(result) == 1 and result[0].target_uri.endswith("libs/myvariables.py")
