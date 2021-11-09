*** Settings ***
#^ Settings Start: any(e for e in result if e.start_line == line and (e.start_character is None or e.start_character==0) and e.kind=='section')
Documentation       Hallo Welt
...                 was geht

*** Test Cases ***
#^ Settings End: any(e for e in result if e.end_line == line - 1 and (e.end_character is None or e.end_character>0) and e.kind=='section')
#^ Test Cases Start: any(e for e in result if e.start_line == line and e.kind=='section')
First
#^ Testcase Start: any(e for e in result if e.start_line == line and e.kind=='testcase')
    Log    Hello from testcase
    a keyword
    FOR    ${i}    IN    1    2    3
#^ For Start: any(e for e in result if e.start_line == line and e.kind=='for')
        IF    ${i}==1
#^ If Start: any(e for e in result if e.start_line == line and e.kind=='if')
            Log    "one"
        ELSE IF    ${i}==2
#^ If Start: any(e for e in result if e.start_line == line and e.kind=='if')
            Log    "two"
        ELSE
#^ If Start: any(e for e in result if e.start_line == line and e.kind=='if')
            Log    "more then two"
        END
#^ If End: any(e for e in result if e.end_line == line and e.kind=='if')

        Log    ${i}

    END
#^ For End: any(e for e in result if e.end_line == line and e.kind=='for')

*** Keywords ***
#^ Test Cases End: any(e for e in result if e.end_line == line - 1 and e.kind=='section')
#^ Testcase End: any(e for e in result if e.end_line == line - 1 and e.kind=='testcase')
a keyword
#^ Keyword Start: any(e for e in result if e.start_line == line and e.kind=='keyword')
    Log    Hello from keyword

*** Comments ***
#^ Keyword End: any(e for e in result if e.end_line == line - 1 and e.kind=='keyword')
#^ Comment Start: any(e for e in result if e.start_line == line and e.kind=='comment')
this is a long long
long long long
long long comment section

#^ Comment End: any(e for e in result if e.end_line == line + 1 and e.kind=='comment')
