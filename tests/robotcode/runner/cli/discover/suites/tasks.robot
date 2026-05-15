*** Settings ***
Documentation    Pure RPA task suite for the `discover tasks` tests.

*** Tasks ***
Process Invoices
    [Tags]    rpa    nightly
    Log    invoices

Sync Inventory
    [Tags]    rpa
    Log    inventory

Notify Stakeholders
    [Tags]    notification
    Log    notify
