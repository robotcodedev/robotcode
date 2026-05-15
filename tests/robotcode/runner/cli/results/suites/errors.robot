*** Settings ***
Documentation    Triggers a parser/discovery error so `--execution-messages`
...              and `messages_count` have something to surface.
Library          NonexistentLibraryName


*** Test Cases ***
Working Test
    Log    a test that does not depend on the missing library
