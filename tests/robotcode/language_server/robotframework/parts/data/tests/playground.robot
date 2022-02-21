*** Settings ***
Variables       testvars.yml
Resource    firstresource.resource
Test Setup    kw    1

*** Variables ***
${A}    ${1}
${B}    ${2}
${C}    1
${A VAR}    123
&{A DICT VAR}  first=hei  second=no
@{A LISTVAR}    1    2    3    4    5
${CMD_VAR_LONG}    1

*** Test Cases ***
first *1*
    Log    ${{$a+$b}}
    Log    ${CMD_VAR_LONG}
    Log    ${A}[1]

first ?11?
    log    hi
    Log    ${A VAR}
    Log    ${A VAR}[${A}]
    Log    ${{$a+1}}
    Log    @${{[1,2,3]}}
    Log    ${A VAR}[\[]
    Log    ${A VAR}[${{$c+["\["][0]}}]

first *11*
    Log    hi
    ${A}    Evaluate    2
    # Evaluate    $a==1
    # Run Keyword If    $A    a    ELSE IF    $a==34
    # Run Keyword And Return If    $a==2    a
    # Run Keyword Unless    $a==2    a

    do something in a resource

    IF  $A_Var=='123'
        Log    Hello
    END
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

