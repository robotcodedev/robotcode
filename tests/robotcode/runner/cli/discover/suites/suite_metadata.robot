*** Settings ***
Documentation    A suite with `Metadata` and a test without metadata, for
...              `discover metadata` on every Robot Framework version.
Metadata         Version    1.0

*** Test Cases ***
Plain
    Log    plain
