*** Settings ***
# Library    Remote    uri=http://127.0.0.1:8270


*** Test Cases ***
first
    Remote.Strings Should Be Equal