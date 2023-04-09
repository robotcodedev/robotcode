*** Settings ***
#^ Settings Start
Documentation       Hallo Welt
...                 was geht

*** Test Cases ***
#^ Settings End
#^ Test Cases Start
First
#^ Testcase Start
    Log    Hello from testcase
    a keyword
    FOR    ${i}    IN    1    2    3
#^ For Start
        IF    ${i}==1
#^ If Start
            Log    "one"
        ELSE IF    ${i}==2
#^ If Start
            Log    "two"
        ELSE
#^ If Start
            Log    "more then two"
        END
#^ If End

        Log    ${i}

    END
#^ For End

🚐🚓🛺🚙
#^ Testcase Start
#^ Testcase End
    Log    🥴

*** Keywords ***
#^ Test Cases End
#^ Testcase End
a keyword
#^ Keyword Start
    Log    Hello from keyword

*** Comments ***
#^ Keyword End
#^ Comment Start
this is a long long
long long long
long long comment section

#^ Comment End
