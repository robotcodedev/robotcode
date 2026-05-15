*** Settings ***
Documentation    Suite with a varied tag mix — used to exercise --include,
...              --exclude and stats grouping by tag.


*** Test Cases ***
Tagged Smoke Pass
    [Tags]    smoke
    Log    pass 1

Tagged Smoke Regression Pass
    [Tags]    smoke    regression
    Log    pass 2

Tagged Regression Slow Pass
    [Tags]    regression    slow
    Log    pass 3

Tagged Regression Fail
    [Tags]    regression
    Fail    deliberate failure

Untagged Pass
    Log    pass without tags

Tagged Slow Skip
    [Tags]    slow
    Skip    not now

Tagged Bug Fail
    [Tags]    bug-123
    Fail    deliberate failure 2

Tagged Bug Smoke Pass
    [Tags]    bug-123    smoke
    Log    pass 5

Tag Norm Variant A
    [Tags]    norm tag
    Log    same tag, with space

Tag Norm Variant B
    [Tags]    norm_tag
    Log    same tag, with underscore

Tag Norm Variant C
    [Tags]    NormTag
    Log    same tag, different case
