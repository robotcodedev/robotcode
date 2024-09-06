*** Test Cases ***
Continue when iteration limit is reached
    WHILE    True    limit=5    on_limit=pass
        Log    Loop will be executed five times
    END
    Log    This will be executed normally.

Limit as iteration count
    WHILE    True    limit=0.5s    on_limit_message=Custom While loop error message
        Log    This is run 0.5 seconds.
    END
