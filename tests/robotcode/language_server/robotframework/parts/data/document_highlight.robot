*** Settings ***
Library         Collections
Library         ${CURDIR}/libs/myvariables.py
Variables       ${CURDIR}/libs/myvariables.py
Resource        ${CURDIR}/resources/firstresource.resource

*** Variables ***
${a var}    hello

*** Test Cases ***
first
    [Setup]    Log To Console    hi ${a var}
    [Teardown]    BuiltIn.Log To Console    hi ${a var}

    Log    Hi ${a var}
#   ^^^  simple keyword call
    Log To Console    hi ${a var}
#   ^^^^^^^^^^^^^^  multiple references
    BuiltIn.Log To Console    hi ${a var}
#           ^^^^^^^^^^^^^^  multiple references with namespace
#                                  ^^^^^  multiple variables