# Why is my variable shown as "not found"?

Does this sound familiar? Your Robot Framework tests are carefully written and run smoothly - but RobotCode persistently displays `VariableNotFound` errors, even though you're certain that all variables are defined and no errors are reported during runtime. In this guide, you'll learn what causes this problem, how the different handling of variables between RobotCode and Robot Framework leads to misunderstandings, and which best practices make your tests more reliable, maintainable, and transparent.

## Understanding Robot Framework Variables

Variables are a fundamental building block of any test automation with Robot Framework. They allow storing and reusing values, make tests more dynamic, and improve the maintainability of your code. However, to use variables effectively, understanding their scopes is crucial.

In Robot Framework, a variable's scope determines where it's available and how long it exists. Misunderstanding these scopes often leads to confusion, especially when RobotCode marks variables as "not found" even though they work at runtime.

### Variable Scopes

Robot Framework distinguishes four main scopes for variables, which are hierarchically arranged ([see also Robot Framework Documentation on Variable Scopes](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#variable-scopes)):

- **Local**: The narrowest scope level. Local variables exist only within the keyword in which they were created, or within a test case if defined there. They disappear as soon as the keyword or test is completed.

- **Test/Task**: These variables are valid for the duration of a single test and are accessible in all keywords called by that test. Test scope variables persist across keyword calls within the same test, unlike local variables which are limited to their defining scope.

- **Suite**: Suite variables are available within an entire test suite - that is, in all tests of a `.robot` file as well as in all keywords called in these tests.

- **Global**: The widest scope level. Global variables are available in all test suites, tests, and keywords that run during a test execution.

This hierarchical structure is important to understand as it determines how Robot Framework searches for variables and how variable overrides work.

### The `*** Variables ***` Section

The `*** Variables ***` section is a fundamental component of Robot files for defining variables:

- **Suite Scope:** All variables defined here automatically receive suite scope and are available throughout the file.

- **Import order decides:** For variables with identical names:
  - The first found definition takes precedence
  - This applies to both definitions in the current suite and in imported resource files
  - For nested resource imports (when Resource A imports Resource B), the same rule applies: The first read definition wins

- **Strategic overriding:** This property can be deliberately used, for example:
  - To control test behavior in different environments
  - To specifically adjust library settings
  This powerful technique should be used with caution.

- **Command line variables have the highest priority:** Variables defined via command line parameters (`--variable` or `-v`) always override all definitions in `*** Variables ***` sections.

**Example: Overriding browser settings**

In this test suite, we define default browser settings that can be overridden by command line parameters:

```robot
*** Settings ***
Library    Browser

*** Variables ***
${BROWSER}      chromium
${HEADLESS}     FALSE

*** Test Cases ***
Open Browser Test
    New Browser    browser=${BROWSER}    headless=${HEADLESS}
    New Page       https://example.com
    # Further test steps...
    Close Browser
```

**Execution with default values:**
```bash
robot tests/web_tests.robot
```
Uses Chromium in normal (non-headless) mode.

**Execution with Firefox in headless mode:**
```bash
robot --variable BROWSER:firefox --variable HEADLESS:True tests/web_tests.robot
```

This pattern is particularly useful for:
- CI/CD pipelines with different browser requirements
- Parallel testing on various browsers
- Local debugging (GUI mode) vs. server execution (headless)

**Tip:** RobotCode provides special hints when a variable definition might override another definition or be overridden by a global variable.

### Variable Resolution

When resolving variables, Robot Framework follows a strictly hierarchical search strategy:

1. **Local scope** (within the current keyword or test)
2. **Test scope** (within the current test case)
3. **Suite scope** (within the current test suite)
4. **Global scope** (valid for the entire test run)

The search stops as soon as a matching variable is found - even if there are further variables with the same name in outer scopes. A local variable named `${status}` always takes precedence over variables with the same name in wider scopes.

### Setting Variables

Robot Framework offers several methods to define variables and assign them a scope:

- **Set keywords**: The classic method with `Set Global Variable`, `Set Suite Variable`, `Set Test Variable`, and `Set Local Variable`
- **VAR syntax**: More readable syntax (available from Robot Framework 7.0) with an optional scope parameter
- **Return values**: Variables created by assigning a keyword return value are local by default

An important concept in Robot Framework is the **scope override mechanism**: If you define a variable with a name that already exists in a narrower scope and specify a wider scope, the variable in the narrower scope is automatically deleted. This behavior ensures that the variable has the last assigned value, regardless of the scope specified.

Consider the following example:

```robot
*** Test Cases ***
test variable scopes
    # 1. Create a local variable
    VAR  ${a_var}    a local value
    Log    ${a_var}  # Output: "a local value"

    # 2. Create a suite variable with the same name
    VAR    ${a_var}  a suite value  scope=suite
    # The local variable is automatically deleted
    Log    ${a_var}  # Output: "a suite value"

    # 3. Create a global variable with the same name
    VAR    ${a_var}  a global value  scope=global
    # The suite variable is automatically deleted
    Log    ${a_var}  # Output: "a global value"
```

To better understand this behavior, it is recommended to run the code in the debugger and observe the variables in the Variables view.

Pay special attention when variables are set in called keywords with a higher scope:

```robot
*** Test Cases ***
test variable scopes
    VAR    ${a_var}    a local value
    Log    ${a_var}  # Output: a local value
    Do Something
    Log    ${a_var}  # Output: a global value - the local variable was overridden


*** Keywords ***
Do Something
    VAR    ${a_var}    a global value    scope=global
```

Caution: By setting a variable with the same name but in a different scope in the `Do Something` keyword, the local variable in the calling test is overridden. This can lead to hard-to-understand effects if you do not explicitly account for this behavior.

## Why RobotCode Reports "Variable not found"

### Runtime vs. Static Analysis

**Robot Framework** is an interpreter that processes your `.robot` files **at runtime** sequentially:
- Variables are dynamically evaluated
- Scopes are created and destroyed during test execution
- Variable definitions through `Set Suite Variable`, `Set Global Variable`, or the `VAR` syntax with scope parameters only take effect when the corresponding code section is executed
- Only at this moment do the variables become known and usable in the specified scope

**RobotCode**, on the other hand, performs a **static analysis**:
- Your code is analyzed before execution
- Cannot predict dynamic assignments or conditional execution paths
- Must work with information available at analysis time

This fundamental discrepancy explains why RobotCode marks variables as `VariableNotFound` even when they would work at runtime.

### Technical Limitations

The following points explain why RobotCode sometimes does not recognize variables even though they would exist at runtime.

- **No call analysis:**
  RobotCode cannot track variable assignments across keyword calls. If a keyword sets a suite/global variable, RobotCode cannot trace this back to the calling code.

  **Example:** A keyword `Setup Environment` sets `${CONFIG}`, but RobotCode cannot recognize that `${CONFIG}` would be defined by calling this keyword.

  **Why can't RobotCode do this?**

  - **Technically challenging:** A complete call analysis would require simulating all possible execution paths - including conditional branches and loops.

  - **Dynamic language elements:** Robot Framework allows:

    - Conditional execution paths that are not predictable
    - Dynamically generated keyword calls (`Run Keyword  ${dynamic_name}`)
    - Imports at runtime ([`Import Library ${lib_name}`](https://robotframework.org/robotframework/latest/libraries/BuiltIn.html#Import%20Library), [`Import Resource ${resource_path}`](https://robotframework.org/robotframework/latest/libraries/BuiltIn.html#Import%20Resource))
    - Dynamically generated variable names ([`${Home ${name}}`](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#variables-inside-variables))

  - **Performance:** Analyzing complex test suites with all possible execution paths would significantly slow down the IDE.

  - **Unlimited search space:** Nested calls across multiple files and potentially recursive structures make a complete analysis impossible.

- **Unpredictable execution order:**
  The execution order in Robot Framework is not always statically predictable. RobotCode cannot know during analysis:

  - Whether tests are filtered with **tags** (`--include`/`--exclude`/`--skip`)
  - Whether the order is changed by **command line options** (`--randomize`)
  - Whether tests are skipped by **conditional execution** (`Skip If`, `Run Keyword If`)
  - Whether **dynamically generated tests** are used (test templates with variable data)
  - Whether **parallel execution** (e.g., with Pabot) is used
  - Whether **external listeners or prerunmodifiers** change the execution or execution order

  **Example:** A suite contains two tests - the first defines `${CONFIG_VALUE}` as a suite variable, the second uses it:

  ```robot
  *** Test Cases ***
  Setup Configuration
      [Tags]    setup
      Set Suite Variable    ${CONFIG_VALUE}    production

  Use Configuration
      [Tags]    functional
      Log    ${CONFIG_VALUE}    # Works only if the setup test was executed
  ```

  If the test is run with `--include functional`, the variable is missing.

- **Conditional assignments and loops:**
  If variables are only set under certain conditions (e.g., in `IF` statements or loops) or in dynamic contexts, RobotCode cannot predict the actual execution path. Examples include:

  - Variables defined only in an `IF` branch
  - Variables created only within a `FOR` loop
  - Variables whose assignment depends on dynamic conditions

  ```robot
  *** Test Cases ***
  test different environments
    IF    '${ENV}' == 'production'
        Set Suite Variable    ${API_URL}    https://api.production.example.com
    ELSE
        Set Suite Variable    ${TEST_URL}    https://api.test.example.com
    END

    Log    ${API_URL}     # [!code error] Error: VariableNotFound
    Log    ${TEST_URL}    # [!code error] Error: VariableNotFound
  ```

- **Suite order and `__init__.robot`:**
  Robot Framework uses a hierarchical execution model with folders and files as test suites. When executing a folder as a suite, Robot Framework first processes the `__init__.robot` file of that folder, if present. This file can define suite setup/teardown keywords as well as test/task setups that then apply to all tests within the entire folder structure.

  This leads to an important peculiarity: Variables defined in these `__init__.robot` files or their suite setups are available at runtime in all subordinate tests. However, this only applies if you run the entire folder. When directly executing a single `.robot` file, parent `__init__.robot` files may not be considered at all - accordingly, the variables defined in them do not exist.

  RobotCode cannot predict during its static analysis whether a single file or an entire folder will be executed.


### Summary of technical reasons:

| Problem                | At runtime                                         | During static analysis                                 |
| ---------------------- | -------------------------------------------------- | ------------------------------------------------------ |
| Call analysis          | Variable is defined by called keyword              | No complete tracking of call chains                    |
| Execution order        | Depends on CLI options and conditional executions  | Cannot predict which tests will be executed            |
| Conditional assignments| Only one path is actually executed                 | All possible paths would need to be analyzed           |
| Suite folder           | Available depending on execution context           | Cannot know the exact execution context                |

### RobotCode's Conservative Strategy

RobotCode deliberately follows a cautious approach to variable recognition, partly due to technical limitations regarding complexity and performance. It only marks a variable as valid if it is explicitly defined in one of the following ways:

- As a command line parameter
- In a `*** Variables ***` section
- In the currently analyzable scope (such as keyword arguments or local variables)

All other variables are consistently marked as `VariableNotFound` - even if they might exist at runtime. This conservative strategy is not merely a technical limitation but a deliberate design principle that offers significant advantages for test quality and maintenance:

- **Error prevention:** The variable might actually be undefined, which would only lead to errors at runtime. Such runtime errors are particularly tricky as they may only occur under certain conditions and take a lot of time to debug. Tests could fail on CI/CD systems or in specific environments even though they work fine locally. RobotCode helps you identify and fix these potential issues early during development - long before they lead to hard-to-trace errors in production-like environments.

- **Code clarity:** Developers cannot immediately tell if a variable is correctly defined when its definition is hidden in other files or nested keywords. A particular risk arises when variables with identical names are set via `Set Global Variable` in different resource files. It can easily happen that a team member uses an already used variable name (`${CONFIG}`) for a completely different purpose - while you store server settings with it, someone else uses the same name for test data. Without explicit definitions, undetected conflicts and hard-to-trace errors arise.

- **Maintainability:** Implicit variable definitions scattered across multiple resource files or occurring only under certain execution conditions create unwanted dependencies and complicate long-term maintenance. When variables "magically" appear - defined somewhere deep in keywords or rarely executed code paths - every change becomes a risk. Teams spend unnecessary time figuring out where a variable was originally set and whether changing it might have unintended side effects. As test suites grow, this problem intensifies exponentially: What was obvious to the original developer becomes an opaque web of hidden dependencies for the team. RobotCode's conservative warnings enforce cleaner design with explicit dependencies.

- **Documentation:** Explicit variable definitions serve as integrated documentation of your code. They make it immediately clear which variables are used, what type they have, and what default values are intended. This significantly eases onboarding for new team members as they don't have to search the entire code to understand where a variable comes from or what purpose it serves. Especially in larger test projects, this kind of self-documentation becomes an important factor for the long-term maintainability and extensibility of the test suite.

The `VariableNotFound` messages should therefore not be seen as annoying warnings but as valuable development tools. They encourage critical reflection on your code and promote better design decisions: "Is a suite variable really necessary here, or is there a more elegant solution?" These diagnostic messages foster an architectural understanding of the test structure, improve code quality, and ultimately support the development of explicit, self-explanatory structures. This principle applies to all diagnostic messages in RobotCode - they are not mere error indications but valuable guardrails on the path to high-quality, robust test suites.

## Solutions and Best Practices

### Explicit Variable Definitions

The most reliable way to avoid `VariableNotFound` errors is to explicitly define variables in the `*** Variables ***` section, especially when you plan to use `Set Suite Variable`, `Set Global Variable`, or the `VAR` statement with suite/global scope later in your tests.

**Key principle**: Always provide default values in `*** Variables ***` for variables that will be dynamically set with wider scopes during test execution. This ensures that RobotCode can statically recognize these variables, even before they are assigned their runtime values.

**Example: Variables that will be set dynamically**

```robot
*** Variables ***
# Define defaults for variables that will be set dynamically
${AUTH_TOKEN}           ${EMPTY}    # Will be set by login keyword
${CURRENT_USER_ID}      ${NONE}     # Will be set during user creation
${TEST_DATA_PATH}       ${EMPTY}    # Will be set based on environment

*** Keywords ***
Login User
    [Arguments]    ${username}    ${password}
    ${token}=    Get Auth Token    ${username}    ${password}
    # RobotCode recognizes ${AUTH_TOKEN} because it's pre-defined
    Set Suite Variable    ${AUTH_TOKEN}    ${token}

Create Test User
    ${user_id}=    Generate User ID
    # RobotCode recognizes ${CURRENT_USER_ID} because it's pre-defined
    VAR    ${CURRENT_USER_ID}    ${user_id}    scope=SUITE

*** Test Cases ***
User Management Test
    Login User    testuser    password123
    Create Test User
    Log    Using token: ${AUTH_TOKEN}        # ✅ No VariableNotFound
    Log    Created user: ${CURRENT_USER_ID}  # ✅ No VariableNotFound
```

**Best Practice: Use descriptive variable names with clear prefixes**

```robot
*** Variables ***
# Configuration variables - use CONFIG_ prefix
${CONFIG_BASE_URL}      https://api.example.com
${CONFIG_TIMEOUT}       30 seconds
${CONFIG_RETRY_COUNT}   3

# Test data variables - use DATA_ prefix
${DATA_USER_EMAIL}      test@example.com
${DATA_USER_PASSWORD}   SecurePassword123

# Environment-specific variables with defaults
${ENV}                  test    # Can be overridden via command line
${BROWSER}              chrome  # Default browser for web tests
```

**Pattern: Variable files for complex configurations**

For more complex scenarios, use Python variable files that RobotCode can analyze:

```python
# variables/config.py
import os

# These variables will be recognized by RobotCode
BASE_URL = os.getenv('BASE_URL', 'https://api.test.example.com')
API_KEY = os.getenv('API_KEY', 'test-api-key')

# Dictionary variables for structured data
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'name': os.getenv('DB_NAME', 'testdb')
}
```

Usage in your robot file:
```robot
*** Settings ***
Variables    variables/config.py

*** Test Cases ***
API Test
    Log    Using API at ${BASE_URL}
    Log    Database host: ${DATABASE_CONFIG}[host]
```

**Pattern: Resource files with shared variables**

Create resource files that define commonly used variables:

```robot
# resources/common_variables.resource
*** Variables ***
${WAIT_TIMEOUT}         10 seconds
${SCREENSHOT_DIR}       ${OUTPUT_DIR}/screenshots
${LOG_LEVEL}           INFO

# Complex data structures
&{DEFAULT_HEADERS}      Content-Type=application/json    Accept=application/json
@{SUPPORTED_BROWSERS}   chrome    firefox    edge
```

Then import in your test files:
```robot
*** Settings ***
Resource    resources/common_variables.resource

*** Test Cases ***
Use Shared Variables
    Log    Timeout is ${WAIT_TIMEOUT}
    Log    Supported browsers: @{SUPPORTED_BROWSERS}
```

This approach provides several benefits:
- RobotCode recognizes all variables immediately
- Variables are documented and centralized
- Easy to maintain and update
- Clear separation of concerns

### Default Value Handling

When working with variables that might not always be defined, it's crucial to implement proper default value handling. RobotCode can better understand your code when you explicitly handle potentially undefined variables.

**Pattern: Using Variable Should Exist with fallback**

```robot
*** Keywords ***
Get Configuration Value
    [Arguments]    ${key}    ${default}=${EMPTY}
    ${exists}=    Run Keyword And Return Status
    ...    Variable Should Exist    ${${key}}
    IF    ${exists}
        ${value}=    Set Variable    ${${key}}
    ELSE
        ${value}=    Set Variable    ${default}
        Log    Variable ${key} not found, using default: ${default}    WARN
    END
    RETURN    ${value}
```

**Pattern: Safe variable access with Get Variable Value**

Robot Framework 5.0+ provides `Get Variable Value` for safe variable access:

```robot
*** Test Cases ***
Safe Variable Access
    # Get variable with default if not exists
    ${url}=    Get Variable Value    ${API_URL}    https://default.example.com

    # Check nested variables safely
    ${timeout}=    Get Variable Value    ${CONFIG.timeout}    30

    # Use None as default to check existence
    ${optional_var}=    Get Variable Value    ${OPTIONAL_SETTING}    ${None}
    IF    $optional_var is not None
        Log    Optional setting is: ${optional_var}
    END
```

**Pattern: Defensive programming with variable validation**

Create a keyword that validates required variables at the start of your test suite:

```robot
*** Keywords ***
Validate Required Variables
    [Documentation]    Ensures all required variables are defined
    @{required_vars}=    Create List
    ...    BASE_URL
    ...    API_KEY
    ...    TEST_USER

    FOR    ${var}    IN    @{required_vars}
        TRY
            Variable Should Exist    ${${var}}
            Log    ✓ Variable ${var} is defined
        EXCEPT
            Fail    Required variable ${var} is not defined!
        END
    END

*** Test Cases ***
Setup Test Environment
    [Setup]    Validate Required Variables
    Log    All required variables are present
```

**RobotCode Quick Fix Integration**

When RobotCode shows a `VariableNotFound` error, you can use the built-in quick fixes:
1. **Create suite variable** - Adds the variable to `*** Variables ***` section
2. **Create local variable** - Creates a local variable with `Set Variable`
3. **Add as keyword argument** - Adds the variable as a keyword parameter

These quick fixes help maintain clean, analyzable code while resolving variable issues.

### Using RETURN Statements (RF 5.0+)

The `RETURN` statement (Robot Framework 5.0+) provide the cleanest way to pass data between keywords without relying on suite or global variables. This approach makes your code more maintainable and helps RobotCode understand the data flow.

In older Robot Framework versions there was a `[Return]` setting that allowed declaring a fixed return value for a keyword; it did not support conditional returns and was deprecated in Robot Framework 7.0. Use the more flexible `RETURN` statement (introduced in RF 5.0), which supports conditional returns and can be used inside IF/FOR constructs.

**RETURN statement**

```robot
*** Keywords ***
Calculate Total Price
    [Arguments]    ${base_price}    ${tax_rate}=0.1    ${discount}=0
    ${tax_amount}=    Evaluate    ${base_price} * ${tax_rate}
    ${discounted_price}=    Evaluate    ${base_price} - ${discount}
    ${total}=    Evaluate    ${discounted_price} + ${tax_amount}
    RETURN    ${total}

Get User Details
    [Arguments]    ${user_id}
    ${name}=    Query Database    SELECT name FROM users WHERE id=${user_id}
    ${email}=    Query Database    SELECT email FROM users WHERE id=${user_id}
    ${role}=     Query Database    SELECT role FROM users WHERE id=${user_id}
    RETURN    ${name}    ${email}    ${role}

*** Test Cases ***
Test With Return Values
    ${price}=    Calculate Total Price    100    0.2    10
    Should Be Equal As Numbers    ${price}    108

    ${name}    ${email}    ${role}=    Get User Details    123
    Log    User: ${name} (${email}) has role: ${role}
```

**Pattern: Data transformation pipelines**

Chain keywords using return values instead of setting suite variables:

```robot
*** Keywords ***
Fetch Raw Data
    [Arguments]    ${source}
    ${data}=    Get File    ${source}
    RETURN    ${data}

Parse JSON Data
    [Arguments]    ${raw_data}
    ${parsed}=    Evaluate    json.loads('''${raw_data}''')
    RETURN    ${parsed}

Transform Data
    [Arguments]    ${data}
    ${transformed}=    Create Dictionary
    FOR    ${key}    ${value}    IN    &{data}
        ${new_value}=    Convert To Upper Case    ${value}
        Set To Dictionary    ${transformed}    ${key}=${new_value}
    END
    RETURN    ${transformed}

*** Test Cases ***
Data Pipeline Test
    ${raw}=         Fetch Raw Data       data.json
    ${parsed}=      Parse JSON Data      ${raw}
    ${result}=      Transform Data       ${parsed}
    Log    Transformed data: ${result}
```

**Pattern: Configuration builders**

Build complex configurations without polluting the variable scope:

```robot
*** Keywords ***
Create Test Configuration
    [Arguments]    ${environment}=test
    ${config}=    Create Dictionary

    IF    "${environment}" == "production"
        Set To Dictionary    ${config}
        ...    url=https://api.production.example.com
        ...    timeout=60
        ...    retry=5
    ELSE IF    "${environment}" == "staging"
        Set To Dictionary    ${config}
        ...    url=https://api.staging.example.com
        ...    timeout=30
        ...    retry=3
    ELSE
        Set To Dictionary    ${config}
        ...    url=https://api.test.example.com
        ...    timeout=10
        ...    retry=1
    END

    RETURN    ${config}

Initialize API Client
    [Arguments]    ${config}
    ${client}=    Create API Client
    ...    base_url=${config}[url]
    ...    timeout=${config}[timeout]
    RETURN    ${client}

*** Test Cases ***
API Test With Configuration
    ${config}=    Create Test Configuration    staging
    ${client}=    Initialize API Client    ${config}
    ${response}=    Call API    ${client}    /health
    Should Be Equal    ${response.status}    200
```

**Pattern: Error handling with optional returns**

Handle errors gracefully while maintaining clear data flow:

```robot
*** Keywords ***
Safe Database Query
    [Arguments]    ${query}
    TRY
        ${result}=    Execute SQL Query    ${query}
        ${status}=    Set Variable    SUCCESS
    EXCEPT    AS    ${error}
        ${result}=    Set Variable    ${None}
        ${status}=    Set Variable    ERROR: ${error}
        Log    Query failed: ${error}    WARN
    END
    RETURN    ${result}    ${status}

*** Test Cases ***
Database Test With Error Handling
    ${data}    ${status}=    Safe Database Query    SELECT * FROM users
    IF    "${status}" == "SUCCESS"
        Log    Retrieved ${data.rowcount} users
    ELSE
        Log    Query failed: ${status}    ERROR
    END
```

**Benefits for RobotCode analysis:**
- Clear data flow that RobotCode can trace
- No hidden variable dependencies
- Explicit input/output contracts
- Better IntelliSense and autocomplete support
- Easier refactoring and testing

**Migration tip:** When refactoring old tests that use `Set Suite Variable`, replace them with keywords that RETURN values:

```robot
# Old approach - RobotCode can't trace this
*** Keywords ***
Setup Test Data
    ${user}=    Create Test User
    Set Suite Variable    ${TEST_USER}    ${user}
    ${token}=    Get Auth Token    ${user}
    Set Suite Variable    ${AUTH_TOKEN}    ${token}

# New approach - Clear data flow
*** Keywords ***
Setup Test Data
    ${user}=    Create Test User
    ${token}=    Get Auth Token    ${user}
    RETURN    ${user}    ${token}

*** Test Cases ***
Test With Clear Data Flow
    ${user}    ${token}=    Setup Test Data
    # Variables are explicit and traceable
```

### Quick Reference Guide

#### Checklist

✅ **DO:**
- Define shared variables in `*** Variables ***` sections
- Use RETURN statements for passing data between keywords
- Leverage variable files for complex configurations
- Use descriptive variable names with consistent prefixes
- Validate required variables at test setup
- Use `Get Variable Value` for optional variables
- Apply RobotCode's quick fixes when appropriate

❌ **DON'T:**
- Rely on `Set Suite/Global Variable` for data passing
- Create variables in deeply nested keywords
- Use dynamic variable names unnecessarily
- Ignore RobotCode's VariableNotFound warnings
- Mix variable definition patterns within the same suite

#### RobotCode Features

1. **Quick Fixes (Ctrl+.):**
   - Create suite variable
   - Create local variable
   - Add as keyword argument
   - Disable warning for line

2. **IntelliSense Support:**
   - Autocomplete for defined variables
   - Hover documentation for variables
   - Go to definition (F12)

3. **Refactoring Support:**
   - Rename variable (F2)
   - Extract variable
   - Inline variable

#### Common Patterns Reference

| Scenario | Recommended Approach | Avoid |
|----------|---------------------|-------|
| Configuration values | `*** Variables ***` section or variable files | Set Suite Variable in setup |
| Test data | Keyword arguments and RETURN | Global variables |
| Temporary values | Local variables with VAR | Suite-level variables |
| Cross-file sharing | Resource files with variables | Dynamic imports |
| Environment-specific | Command-line variables | Hardcoded conditionals |

## Conclusion

Understanding how RobotCode analyzes variables and following the best practices outlined in this guide will help you write more maintainable and reliable Robot Framework tests. While the `VariableNotFound` warnings might seem frustrating at first, they are valuable indicators that guide you toward better code structure and clearer variable management.

Remember that RobotCode's conservative approach to variable recognition is designed to help you catch potential issues early in development rather than during test execution. By embracing explicit variable definitions and clear data flow patterns, you'll create test suites that are not only free from variable warnings but also easier to understand, maintain, and scale.

The key takeaway: Make your variables visible to both RobotCode and your team members through explicit definitions and clear scoping. Your future self and your colleagues will thank you for it.
