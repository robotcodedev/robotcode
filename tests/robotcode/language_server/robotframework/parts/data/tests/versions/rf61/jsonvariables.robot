*** Settings ***
Variables    ./vars.json

*** Test Cases ***
first
    Log    ${var from json}
    Log    ${var_from_json}