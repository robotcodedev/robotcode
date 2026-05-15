*** Settings ***
Documentation    FOR / IF body items that exist on every supported RF
...              version (5.0+). Used to exercise the basic control-flow
...              dispatch in `_collect_test_body`.


*** Variables ***
@{ITEMS}    apple    banana    cherry


*** Test Cases ***
For In Test
    FOR    ${item}    IN    @{ITEMS}
        Log    Got ${item}
    END

For In Range Test
    FOR    ${i}    IN RANGE    3
        Log    Counter ${i}
    END

If Else Test
    ${value}=    Set Variable    cherry
    IF    "${value}" == "apple"
        Log    First branch
    ELSE IF    "${value}" == "banana"
        Log    Second branch
    ELSE
        Log    Default branch
    END
