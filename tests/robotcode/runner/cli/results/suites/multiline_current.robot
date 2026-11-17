*** Settings ***
Documentation    Current half of the multi-line message pair: the test fails
...              with a message of three lines of 30 characters each.


*** Test Cases ***
Order Total
    Fail    The order total does not match\nExpected 42.00, but got 41.90.\nCheck how the tax gets rounded
