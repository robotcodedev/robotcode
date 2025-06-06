*** Test Cases ***
first
    :FOR    ${animal}    IN    cat    dog
        \    Log ${animal}
        \    Log    2nd keyword

second
    IF    True    FOR    ${x}    IN    @{stuff}

third
    FOR    ${i}    IN RANGE    1    22
        Pass Execution    ${i}
    END
