*** Settings ***
Documentation     A test whose message comes only from its failing teardown.


*** Test Cases ***
Cleanup Problem
    No Operation
    [Teardown]    Fail    cleanup broke

Clean Test
    No Operation
