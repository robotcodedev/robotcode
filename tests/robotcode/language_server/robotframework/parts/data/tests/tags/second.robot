*** Settings ***
Default Tags    blah-tag    bluf-tag


*** Test Cases ***
first
    [Tags]    unknown
    No Operation

second
    [Tags]    unknown    no-ci_1
    No Operation
