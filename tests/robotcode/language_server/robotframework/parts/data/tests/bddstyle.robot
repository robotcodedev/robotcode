*** Keywords ***
value of var <${input}> is present
    Log    ${input}
value of var input is multiplied by "${multiplier}"
    Log    ${multiplier}
value of var result should be [${result}]
    Log    ${result}


kw    [Arguments]    ${input}    ${multiplier}    ${result}
    Given value of var <${input}> is present
    When value of var input is multiplied by "${multiplier}"
    then value of var result should be [${result}]
    And value of var result should be [${{1+2}}]

*** Test Cases ***
#TESTCASE         INPUT    MULTI    RESULT
Testcase 1    kw    1        2        2
Testcase 2    kw    2        2        4
Testcase 3    kw    4        4        16
Testcase 4
    Given value of var <1234> is present
    When value of var input is multiplied by "+"
    then value of var result should be [asdfasdfsd]
    And value of var result should be [\${1}]
    And value of var result should be [@{1}]
