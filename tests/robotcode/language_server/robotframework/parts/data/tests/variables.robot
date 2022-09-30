*** Settings ***
Suite Teardown      Run Keywords    Log    ${SUITE STATUS}    AND    Log    ${SUITE MESSAGE} ${TEST NAME}   AND    Log Variables
Test Setup    Log    ${TEST NAME}
Variables    myvariables.py
Variables    testvars.yml

*** Variables ***
${pre_full_name}    ${PREV TEST NAME}_${PREV TEST STATUS}
${full_name}    ${TEST NAME}_${TEST STATUS}
${ZZ}    ${}
${UU}    @{}
${DD}    ${DD+1}    # TODO recursiv variable definition
${aaa    1

*** Test Cases ***
first
    Log    ${CURDIR}
    Log    ${EXECDIR}
    Log    ${TEMPDIR}
    Log    ${/}
    Log    ${:}
    Log    ${\n}
    Log    ${SPACE}
    Log    ${True}
    Log    ${False}
    Log    ${None}
    Log    ${null}
    Log    ${TEST NAME}
    Log    ${TEST TAGS}
    Log    ${TEST DOCUMENTATION}

    Log    ${PREV TEST NAME}
    Log    ${PREV TEST STATUS}
    Log    ${PREV TEST MESSAGE}
    Log    ${SUITE NAME}
    Log    ${SUITE SOURCE}
    Log    ${SUITE DOCUMENTATION}
    Log    ${SUITE METADATA}
    Log    ${LOG LEVEL}
    Log    ${OUTPUT FILE}
    Log    ${LOG FILE}
    Log    ${REPORT FILE}
    Log    ${DEBUG FILE}
    Log    ${OUTPUT DIR}

    do something

    [Teardown]    Log    ${TEST STATUS} ${TEST MESSAGE}

second
    FOR  ${i}  IN  arg
        Log    ${i}
    END

    a keyword with loop    hello


third
    Log    ${hello there1 + 1}
    Log    ${hello there1}
    Log    ${hello there1 + ${asd}}
    Log    ${asd}
    ${asd}    Set Variable    hello

    Log    ${asd}
    Log    ${hello there1 + ${asd}}
    ${hello there1}    Set Variable    hello
    Log    ${hello there1 + ${asd}}    # TODO resolve vars?

    &{a dict}    Set Variable    hello=hi    there=12
    Log    ${a dict.hello}

fourth
    ${a}    Evaluate    1
    ${b}    Evaluate    2
    ${c}    Set Variable    ${{$a+$b+$d}}
    ${d}    Set Variable    ${{$a+$b+c}}
    ${e}    Set Variable    ${{$a+$b+$e}}
    ${f}    Set Variable    ${{$a+$b+$e}}

fifth
    ${a}    Evaluate    1+2
    ${b}    Evaluate    2+2

    IF    $a+$b+$c
        Log    Yeah
    ELSE IF    $a+$d
        Log    buuh
    END

    WHILE  $a+$b+$c
        BREAK
    END

    IF  $a<$b+$c    log    hello

sixth
    ${a}    Evaluate    1+2
    ${b}    Evaluate    123

    ${c}    Evaluate    $a+$b+$c
    Should Be True    $a+$d
    Should Be True    $a+$d
    Skip If    $dd
    Continue For Loop If    $aa
    Exit For Loop If    $aa
    Return From Keyword If    $aa+$a
    Run Keyword And Return If    $aa    Log    hello
    Pass Execution If    $asd    hello
    Run Keyword If    $a+$d    log    hello
    Run Keyword Unless    $aa    log    hello
    Run Keyword If    $a+$d    evaluate    $a+$b+$c

seventh
    [Documentation]    This is a documentation ${TEST}
    ...
    ...    Examples vars ${value} ${unknown value}

    a keyword

*** Variables ***
${VALUE}=           INFO
${INFO_DATA}=       DATA

*** Test Cases ***
tc
    Log    ${VALUE}

    Log    ${${VALUE}_DATA1}
    Log    ${${VALUE}_1}

templated
    [Template]  templated kw
    1  2  3
    3  4  7

templated with embedded
    [Template]  check that ${a} plus ${b} is ${expected}
    1  2  3
    3  4  7

templated with embedded
    [Template]  check that ${a} plus ${b} is ${expected}
    a  c  b
    ${EMPTY}  4  7
    1 2  4  7

templated with embedded not defined
    [Template]  verify that ${a} plus ${b} is ${expected}
    1  2  3
    3  4  7

environmentvars
    log  ${%{TESTENV}.server.ip}  port=${%{TESTENV}.server.port}  # TODO

named arguments
    a keyword with loop    aaa=hello


*** Keywords ***
do something
    Log    hello from do something
    [Teardown]    Run Keywords    Log    ${KEYWORD STATUS}    AND    Log    ${KEYWORD MESSAGE}

a keyword with loop
    [Arguments]    ${aaa}

    FOR  ${i}  IN RANGE  100
        Log    ${i} ${aaa}
    END

check that ${a:[0-9\ ]*} plus ${b} is ${expected}
    log  ${a} ${b} ${expected}

templated kw
    [Arguments]  ${a}  ${b}  ${expected}
    log  ${a} ${b} ${expected}

a keyword with kwonly separator
    [Arguments]    ${name}    @{}    ${version}=<unknown>    ${scope}    ${keywords}    ${listener}=False
    No Operation

dummy
    a keyword with kwonly separator  a   scope=1  keywords=1

*** Test Cases ***
