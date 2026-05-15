*** Settings ***
Documentation    WHILE / TRY-EXCEPT-FINALLY / RETURN / BREAK / CONTINUE.
...              Requires Robot Framework 5.2+.


*** Keywords ***
Return Early
    [Documentation]    Demonstrates the RETURN body item.
    RETURN    early-value


*** Test Cases ***
While Loop Test
    ${i}=    Set Variable    ${0}
    WHILE    ${i} < 3    limit=10
        Log    Iteration ${i}
        ${i}=    Evaluate    ${i} + 1
    END

Try Except Test
    TRY
        Fail    inner failure
    EXCEPT    inner*    type=GLOB
        Log    Caught the inner failure
    FINALLY
        Log    Cleanup ran
    END

For With Continue And Break Test
    FOR    ${i}    IN RANGE    5
        IF    ${i} == 1
            CONTINUE
        END
        IF    ${i} == 3
            BREAK
        END
        Log    Item ${i}
    END

Return Test
    ${value}=    Return Early
    Log    Got ${value}
