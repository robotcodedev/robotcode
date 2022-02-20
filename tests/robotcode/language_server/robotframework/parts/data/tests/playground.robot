*** Settings ***
Variables       testvars.yml
Resource    firstresource.resource
Test Setup    kw    1

*** Variables ***
${A}    ${1}
${B}    ${2}

*** Test Cases ***
first *1*
    Log    ${{$a+$b}}

first ?11?
    log    hi
    Log    ${TEST_VAR3}[1]

first *11*
    Log    hi
    ${A}    Evaluate    2
    # Evaluate    $a==1
    # Run Keyword If    $A    a    ELSE IF    $a==34
    # Run Keyword And Return If    $a==2    a
    # Run Keyword Unless    $a==2    a
    do something in a resource
    IF    $a==2
        kw    55
    ELSE IF    $a==1
        Log    ho
    ELSE
        Log    huch
    END

    FOR  ${i}  IN  arg
        Log    ${i}
    END

    WHILE  $b>0
        Log    ${B}
        ${B}    Evaluate  $b-1

    END


    Log    ende

*** Keywords ***
kw
    [Arguments]    ${a}

    kw1
    IF    ${a}==1
        Log    yeah
    ELSE IF    $a==1
        Log    no yeah
    ELSE
        Log    hoho
    END


kw1
    [Arguments]    ${c}=99
    ${B}     Evaluate    1+2
    Log    hello

