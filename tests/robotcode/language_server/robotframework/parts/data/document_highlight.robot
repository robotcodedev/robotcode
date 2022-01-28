*** Settings ***
Library         Collections
Library         ${CURDIR}/libs/myvariables.py
Variables       ${CURDIR}/libs/myvariables.py
Resource        ${CURDIR}/resources/firstresource.resource
Suite Setup    BuiltIn.Log To Console    hi from suite setup
#                      ^^^^^^^^^^^^^^  suite fixture keyword call with namespace
Test Setup    Log To Console    hi from test setup
#                      ^^^^^^^^^^^^^^  test fixture keyword call with namespace

*** Variables ***
${a var}    hello

*** Test Cases ***
first
    [Setup]    Log To Console    hi ${a var}
#              ^^^^^^^^^^^^^^  fixture keyword call 
    [Teardown]    BuiltIn.Log To Console    hi ${a var}
#              ^^^^^^^^^^^^^^  fixture keyword call with namespace
    Log    Hi ${a var}
#   ^^^  simple keyword call
    Log To Console    hi ${a var}
#   ^^^^^^^^^^^^^^  multiple references
    BuiltIn.Log To Console    hi ${a var}
#           ^^^^^^^^^^^^^^  multiple references with namespace
#                                  ^^^^^  multiple variables

second
    [Template]    Log To Console
#                 ^^^^^^^^^^^^^^  template keyword
    Hi
    There

third
    [Template]    BuiltIn.Log To Console
#                         ^^^^^^^^^^^^^^  template keyword with namespace
    Hi
    There
