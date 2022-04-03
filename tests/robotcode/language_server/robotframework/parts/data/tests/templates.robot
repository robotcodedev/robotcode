*** Settings ***
Test Template       suite template keyword

Test Template       check that 1 plus ${b} is ${expected}

*** Variables ***
${A VAR}    4
@{LIST VAR}    1    2    3

*** Test Cases ***
first
    [Tags]    robot:continue-on-failure
    [Template]    template keyword
    1    ${A VAR}    3
    @{LIST VAR}
    1    ${UNKNOWN VAR}    3
    @{LIST VAR}    2
    3    5    ${A VAR}    2
    a=1    ${UNKNOWN VAR}    4

second
    [Tags]    robot:continue-on-failure
    1    2    3
    3    5    6    2
    a=1    2    4

third
    [Template]    NONE
    Log    hello

templated
    [Template]    templated kw
    1    2    3
    3    4    7

templated with embedded
    2    3
    3    4    7

templated with embedded2
    [Template]    check that 1 plus ${b} is ${expected}
    2    3
    3    4    7

templated with embedded1
    [Template]    check that 1 plus ${b} is ${expected}
    a    3
    1    7

templated with embedded3
    [Template]    check that 1 plus a is ${expected}
    2
    4

templated with embedded not defined
    [Template]    verify that ${a} plus ${b} is ${expected}
    1    2    3
    3    a    7

*** Keywords ***
suite template keyword
    [Arguments]    ${a}    ${b}    ${c}
    Log    Test Template
    Log    ${a}
    Log    ${b}
    Log    ${c}

template keyword
    [Arguments]    ${a}    ${b}    ${c}
    Log    Template
    Log    ${a}
    Log    ${b}
    Log    ${c}

do something
    Log    hello from do something
    [Teardown]    Run Keywords    Log    ${KEYWORD STATUS}    AND    Log    ${KEYWORD MESSAGE}

a keyword with loop
    [Arguments]    ${aaa}

    FOR    ${i}    IN RANGE    100
        Log    ${i} ${aaa}
    END

check that ${a} plus ${b:[a-c]+} is ${expected}
    log    ${a} ${b} ${expected}

templated kw
    [Arguments]    ${a}    ${b}    ${expected}
    log    ${a} ${b} ${expected}
