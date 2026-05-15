*** Settings ***
Documentation    Exercises every body-item type the `log` JSON dispatch
...              touches. Requires Robot Framework 7.0+ (uses GROUP and the
...              RF 7 attribute names).


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

Var Statement Test
    VAR    ${local}    local-value
    VAR    ${suite_var}    suite-value    scope=SUITE
    Log    ${local} and ${suite_var}

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

Group Test
    GROUP    Setup phase
        Log    First inside group
        Log    Second inside group
    END
    Log    After group
