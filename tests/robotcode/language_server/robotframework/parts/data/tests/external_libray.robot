*** Settings ***
Library    alibrary.py
Resource    firstresource.resource

*** Test Cases ***
first
    alibrary.A Library Keyword
    firstresource.do something in a resource