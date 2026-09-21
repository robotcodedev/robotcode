*** Settings ***
Documentation    Tasks with `[Metadata]` (Robot Framework 7.5+) for the
...              `discover` metadata tests.

*** Tasks ***
Process Invoices
    [Metadata]    Issue    4409
    [Metadata]    Owner Team    core
    Log    invoices

Sync Inventory
    Log    inventory
