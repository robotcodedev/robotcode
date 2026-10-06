*** Settings ***
Documentation    Triggers an import error, which Robot Framework reports only in the
...              `<errors>` section, and logs a runtime warning, which it reports at its
...              keyword and copies into `<errors>`.
Library          NonexistentLibraryName


*** Test Cases ***
Working Test
    Log    a test that does not depend on the missing library

Warning Test
    Log    a runtime warning    WARN
