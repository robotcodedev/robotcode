*** Settings ***
Suite Teardown      Run Keywords    Log    ${SUITE STATUS}    AND    Log    ${SUITE MESSAGE}    AND    Log Variables

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

*** Keywords ***
do something
    Log    hello from do something
    [Teardown]    Run Keywords    Log    ${KEYWORD STATUS}    AND    Log    ${KEYWORD MESSAGE}
