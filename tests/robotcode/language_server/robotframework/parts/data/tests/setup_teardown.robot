*** Settings ***
Default Tags    Hallo

Suite Setup    do something suite setup
Suite Teardown    do something suite teardown
Test Setup    do something test setup
Test Teardown    do something test teardown

*** Test Cases ***
first
    do something    hi
    Log    hello

Second
    [Setup]    do something test setup inner
    [Teardown]    do something test teardown inner
    Log    hello
    Fail  glkhj


*** Keywords ***
do something ${type}
    do something     ${type}

do something
    [Arguments]    ${type}
    Log    done ${type}