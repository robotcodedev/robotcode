*** Settings ***
Documentation    Tests with `[Metadata]` (Robot Framework 7.5+) for the
...              stand-alone metadata pre-run modifiers.

*** Test Cases ***
Issue 4409
    [Metadata]    Issue    4409
    No Operation

Issue 4410
    [Metadata]    Issue    4410
    No Operation

No Metadata
    No Operation
