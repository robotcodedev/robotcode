*** Settings ***
Documentation    VAR statement. Requires Robot Framework 7.0+.


*** Test Cases ***
Var Statement Test
    VAR    ${local}    local-value
    VAR    ${suite_var}    suite-value    scope=SUITE
    Log    ${local} and ${suite_var}
