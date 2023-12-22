*** Settings ***
Library    alibrary.py
Resource    firstresource.resource

*** Test Cases ***
first
    A Library Keyword
    firstresource.do something in a resource