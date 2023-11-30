*** Settings ***
#^ Settings start
Documentation       Hallo Welt
...                 was geht

*** Test Cases ***
#^ Settings end
#^ Test Cases start
First
#^ Testcase start
    Log    Hello from testcase
    a keyword
    FOR    ${i}    IN    1    2    3
#^ For start
        IF    ${i}==1
#^ If start
            Log    "one"
        ELSE IF    ${i}==2
#^ If start
            Log    "two"
        ELSE
#^ If start
            Log    "more then two"
        END
#^ If end

        Log    ${i}

    END
#^ For end

🚐🚓🛺🚙
#^ Testcase start
#^ Testcase end
    Log    🥴

*** Keywords ***
#^ Test Cases end
#^ Testcase end
a keyword
#^ Keyword start
    Log    Hello from keyword

*** Comments ***
#^ Keyword end
#^ Comment start
this is a long long
long long long
long long comment section

*** Test Cases ***
#^ Comment end
IF statements
    ${a}    Set Variable    2
    IF    $a==1
#^ simple if start
        Log    hello
    END
#^ simple if end

    IF  $a==1
#^ complex if start
        Log    hello
    ELSE IF    $a>2 and $a<10
#^ complex else if start
        Log    greater 2
        IF  $a==3
            Log    blo
        ELSE
            Log    no
        END
    ELSE IF    $a==100
#^ complex second else if start
        Log  aaahhhh
    ELSE
#^ else start
        Log    to much
    END
#^ else end
