*** Settings ***
Documentation    A flat suite with mixed names and tags for search tests.
Metadata         OwnerProbe    SUITE_META_TOKEN_qrs

*** Test Cases ***
Login Smoke
    [Tags]    smoke    bug 1
    Log    smoke

Login Regression
    [Tags]    regression    bug_1
    Log    regression

Reporting Summary
    [Tags]    smoke    BUG1
    Log    summary

Plain Other
    [Tags]    slow
    Log    other

Body Probe
    [Tags]    body-probe
    Set Test Variable    ${probe_var}    UNIQUE_BODY_TOKEN_xyz
    FOR    ${i}    IN    fizz    buzz
        Log    ${i}
    END

Documented Probe
    [Documentation]    Verifies the DOC_PROBE_TOKEN handling.
    [Tags]    doc-probe
    Log    documented
