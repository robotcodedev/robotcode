## Dialogs

|  |  |
| :--- | :--- |
| ***Library Version:*** | 4.0.1 |
| ***Library Scope:*** | GLOBAL |


### Introduction

A test library providing dialogs for interacting with users.


`Dialogs` is Robot Framework's standard library that provides means for pausing the test execution and getting input from users. The dialogs are slightly different depending on whether tests are run on Python, IronPython or Jython but they provide the same functionality.


Long lines in the provided messages are wrapped automatically. If you want to wrap lines manually, you can add newlines using the `\n` character sequence.


The library has a known limitation that it cannot be used with timeouts on Python.


---
### Keywords

#### Execute Manual Step

##### Arguments:

```text
message
default_error=
```

##### Documentation:

Pauses test execution until user sets the keyword status.


User can press either `PASS` or `FAIL` button. In the latter case execution fails and an additional dialog is opened for defining the error message.


`message` is the instruction shown in the initial dialog and `default_error` is the default value shown in the possible error message dialog.


---
#### Get Selection From User

##### Arguments:

```text
message
*values
```

##### Documentation:

Pauses test execution and asks user to select a value.


The selected value is returned. Pressing `Cancel` fails the keyword.


`message` is the instruction shown in the dialog and `values` are the options given to the user.


Example:


|  |  |  |  |  |  |
| :--- | :--- | :--- | :--- | :--- | :--- |
| ${user} = | Get Selection From User | Select user | user1 | user2 | admin |


---
#### Get Selections From User

##### Arguments:

```text
message
*values
```

##### Documentation:

Pauses test execution and asks user to select multiple values.


The selected values are returned as a list. Selecting no values is OK and in that case the returned list is empty. Pressing `Cancel` fails the keyword.


`message` is the instruction shown in the dialog and `values` are the options given to the user.


Example:


|  |  |  |  |  |  |
| :--- | :--- | :--- | :--- | :--- | :--- |
| ${users} = | Get Selections From User | Select users | user1 | user2 | admin |


New in Robot Framework 3.1.


---
#### Get Value From User

##### Arguments:

```text
message
default_value=
hidden=False
```

##### Documentation:

Pauses test execution and asks user to input a value.


Value typed by the user, or the possible default value, is returned. Returning an empty value is fine, but pressing `Cancel` fails the keyword.


`message` is the instruction shown in the dialog and `default_value` is the possible default value shown in the input field.


If `hidden` is given a true value, the value typed by the user is hidden. `hidden` is considered true if it is a non-empty string not equal to `false`, `none` or `no`, case-insensitively. If it is not a string, its truth value is got directly using same [rules as in Python](http://docs.python.org/library/stdtypes.html\#truth).


Example:


|  |  |  |  |
| :--- | :--- | :--- | :--- |
| ${username} = | Get Value From User | Input user name | default |
| ${password} = | Get Value From User | Input password | hidden=yes |


---
#### Pause Execution

##### Arguments:

```text
message=Test execution paused. Press OK to continue.
```

##### Documentation:

Pauses test execution until user clicks `Ok` button.


`message` is the message shown in the dialog.


