*** Settings ***
Library    Collections

Library     Signatures    [1,2]  #
#                         ^^^^^ library signature

Suite Setup    Do Something    1    2
#                              ^ Suite Setup first param
#                                   ^ Suite Setup second param

*** Test Cases ***
first
    do something from resource    hello     INFO    False                    #
#                               ^^^^^^^ first param resource
#                                        ^^^^^^^^^  second param resource
#                                                   ^^^^^^^  second param resource
#                                                          ^^^^^^^  no param resource
    Do Something        #
#                   ^ without params
    ${a}    ${b}    Do Something    1    2
#                                   ^ with params
#                                        ^ second param
#                                             ^ no param


*** Keywords ***
do something from resource
    [Arguments]    ${message}    ${level}=INFO    ${html}=${False}
    No Operation     #
#                 ^  BuiltIn no params
