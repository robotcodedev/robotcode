*** Settings ***
Documentation    A test that fails with a message of ten lines of 50 characters each.


*** Test Cases ***
Order Total
    Fail    Line 01: the order total check failed at this step\nLine 02: the order total check failed at this step\nLine 03: the order total check failed at this step\nLine 04: the order total check failed at this step\nLine 05: the order total check failed at this step\nLine 06: the order total check failed at this step\nLine 07: the order total check failed at this step\nLine 08: the order total check failed at this step\nLine 09: the order total check failed at this step\nLine 10: the order total check failed at this step
