*** Settings ***
Documentation    GROUP block. Requires Robot Framework 7.2+.


*** Test Cases ***
Group Test
    GROUP    Setup phase
        Log    First inside group
        Log    Second inside group
    END
    Log    After group
