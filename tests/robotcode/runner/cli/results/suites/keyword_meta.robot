*** Settings ***
Documentation    Suite-level documentation token: SUITE_DOC_TOKEN_alpha.
...              Exercises suite/keyword metadata as search targets.
Metadata         OwnerTeam      payments-squad
Metadata         BuildBadge     green


*** Keywords ***
Helper With Metadata
    [Documentation]    Helper keyword documentation token: KW_DOC_TOKEN_beta.
    [Tags]    KWTagProbe
    [Timeout]    7 days
    Log    helper ran


*** Test Cases ***
Tagged Caller
    [Setup]    Helper With Metadata
    Log    body after setup

Plain Test
    Log    just a leaf
