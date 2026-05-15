*** Settings ***
Documentation     Basic suite used by the `robotcode results` acceptance tests.
...               Produces a deterministic mix of PASS / FAIL / SKIP outcomes.
Suite Setup       Log    Suite-level setup
Suite Teardown    Log    Suite-level teardown


*** Test Cases ***
Passing Test One
    [Tags]    smoke
    Log    Hello from passing test one

Passing Test Two
    Should Be Equal    foo    foo

Passing Test Three
    [Tags]    smoke    regression
    Log    Another passing test

Failing Test
    [Tags]    regression
    Fail    Boom: deliberate failure

Skipped Test
    Skip    Not implemented yet
