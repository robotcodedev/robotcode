*** Settings ***
Documentation    Baseline half of the multi-line message pair. Both halves are
...              run with `robot --name Multiline` so their tests share full names.


*** Test Cases ***
Order Total
    Log    the total matches
