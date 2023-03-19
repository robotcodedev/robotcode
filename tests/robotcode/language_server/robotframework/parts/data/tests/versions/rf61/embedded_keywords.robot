*** Test Cases ***
Test 1
    do something with thing
    do something with thing and this data    data1

*** Keywords ***
do ${something} with ${thing}
    Log    done ${something} with ${thing}

do ${something} with ${thing} and this data
    [Arguments]    ${data}
    Log    done ${something} with ${thing} and this data ${data}
