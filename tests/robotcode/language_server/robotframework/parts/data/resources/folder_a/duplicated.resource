*** Keywords ***
duplicated keyword
    [Documentation]    keyword from folder a
    Log    hello

A Resource Keyword A
    Log    hello

a dummy keyword
    duplicated keyword
    A Resource Keyword A
