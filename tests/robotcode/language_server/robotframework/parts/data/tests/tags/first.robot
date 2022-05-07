*** Settings ***
Default Tags    blah-tag    bluf-tag


*** Test Cases ***
first
    [Tags]    no-ci_1
    No Operation

second
    [Tags]    unknown 1
    No Operation
