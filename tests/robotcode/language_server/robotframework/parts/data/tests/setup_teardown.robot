*** Settings ***
Suite Setup         do something suite setup
Suite Teardown      do something suite teardown
Test Setup          do something test setup
Test Teardown       do something test teardown

Default Tags        hallo

*** Test Cases ***
first
    do something    hi
    Log    hello

Second
    [Setup]    do something test setup inner
    Log    hello
    [Teardown]    do something test teardown inner

*** Keywords ***
do something ${type}
    do something    ${type}

do something
    [Arguments]    ${type}
    Log    done ${type}
