# DRAFT: Why is my variable shown as "not found"?

Does this sound familiar? Your Robot Framework tests are carefully written and run smoothly - but RobotCode persistently displays `VariableNotFound` errors, even though you're certain that all variables are defined and no errors are reported during runtime. In this guide, you'll learn what causes this problem, how the different handling of variables between RobotCode and Robot Framework leads to misunderstandings, and which best practices make your tests more reliable, maintainable, and transparent.

## Variables and Variable Scopes in Robot Framework

Variables are a fundamental building block of any test automation with Robot Framework. They allow storing and reusing values, make tests more dynamic, and improve the maintainability of your code. However, to use variables effectively, understanding their scopes is crucial.

In Robot Framework, a variable's scope determines where it's available and how long it exists. Misunderstanding these scopes often leads to confusion, especially when RobotCode marks variables as "not found" even though they work at runtime.

### What scopes exist

Robot Framework distinguishes four main scopes for variables, which are hierarchically arranged ([see also Robot Framework Documentation on Variable Scopes](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#variable-scopes)):

- **Local**: The narrowest scope level. Local variables exist only within the keyword in which they were created, or within a test case if defined there. They disappear as soon as the keyword or test is completed.

- **Test/Task**: These variables are valid for the duration of a single test and are only accessible within that test. This scope only exists within keywords; within a test, this scope corresponds to the local scope.

- **Suite**: Suite variables are available within an entire test suite - that is, in all tests of a `.robot` file as well as in all keywords called in these tests.

- **Global**: The widest scope level. Global variables are available in all test suites, tests, and keywords that run during a test execution.

This hierarchical structure is important to understand as it determines how Robot Framework searches for variables and how variable overrides work.

### `*** Variables ***` Section

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

### How Robot Framework resolves variables

When resolving variables, Robot Framework follows a strictly hierarchical search strategy:

1. **Local scope** (within the current keyword or test)
2. **Test scope** (within the current test case)
3. **Suite scope** (within the current test suite)
4. **Global scope** (valid for the entire test run)

This search strategy follows a hierarchical resolution principle: Robot Framework always searches first in the narrowest available scope (local) and gradually expands the search outward. The search stops as soon as a matching variable is found - even if there are further variables with the same name in outer scopes.

In other words: A local variable named `${status}` always takes precedence over a test, suite, or global variable with the same name. This resolution order (local → test → suite → global) corresponds to the typical scope rules of many programming languages.

### What happens when setting variables?

Robot Framework offers several methods to define variables and assign them a scope:

- **Set keywords**: The classic method with `Set Global Variable`, `Set Suite Variable`, `Set Test Variable`, and `Set Local Variable`
- **VAR syntax**: The modern, more readable syntax (available from Robot Framework 7.0) with an optional scope parameter
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

## Conclusion on variables and variable scopes

Understanding the different variable scopes in Robot Framework is crucial for developing robust and maintainable tests. The hierarchical structure of local, test, suite, and global variables offers flexibility but also requires careful use. It is especially important to understand the resolution strategy: Robot Framework always searches from the narrowest to the widest scope and stops at the first match.

Pay particular attention to the fact that setting variables with identical names in different scopes can lead to unexpected overrides. The automatic deletion of variables in narrower scopes can cause hard-to-understand side effects, especially when it occurs in nested keywords.

As a best practice, you should:
- Use meaningful variable names
- Be cautious when setting variables in suite or global scopes - use these only for truly shared values
- Prefer keyword arguments and return values over setting variables in wider scopes
- Most variables should remain in the local scope
- Be aware of the impact of variables sections in resource files and their import order
- Document necessary variable overrides between keywords to avoid surprises

These principles help you avoid the most common pitfalls when working with variables and also explain why RobotCode sometimes marks variables as "not found" even though they would exist at runtime.

## Why does RobotCode now report "Variable not found"?

The core of the problem lies in two fundamentally different working methods:

### Runtime vs. Development time

**Robot Framework** is an interpreter that processes your `.robot` files **at runtime** sequentially:
- Variables are dynamically evaluated
- Scopes are created and destroyed during test execution
- Variable definitions through `Set Suite Variable`, `Set Global Variable`, or the `VAR` syntax with scope parameters only take effect when the corresponding code section is executed
- Only at this moment do the variables become known and usable in the specified scope

**RobotCode**, on the other hand, performs a **static analysis**:
- Your code is analyzed before it is executed
- RobotCode cannot "see into the future" and know which variables would exist at runtime
- The IDE must work with the information available at the time of analysis
- It cannot predict dynamic assignments or conditional execution paths

This fundamental discrepancy between **dynamic execution** and **static analysis** explains why RobotCode must mark variables as `VariableNotFound` even if they would work correctly at runtime. It's like the difference between reading a recipe (static analysis) and actually cooking (runtime) - when reading, you only see the ingredients explicitly listed, not what will later emerge during cooking.

### Reasons why RobotCode can be confused:

The following points explain why RobotCode sometimes does not recognize variables even though they would exist at runtime.

- **No call analysis:**
  RobotCode does not perform deep tracking of variable assignments across keyword or test calls during its static analysis. This means specifically:

  - If, for example, a suite or global variable is created within a keyword with `Set Suite Variable` or `Set Global Variable`, RobotCode cannot trace this assignment back to the calling code.
  - The variable may then appear as "not found" in the test case, even though it would exist correctly at runtime.

  **Example:** A keyword `Setup Environment` sets a suite variable `${CONFIG}`, which is then used in a test. RobotCode cannot automatically recognize that `${CONFIG}` would be defined by calling `Setup Environment`.

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

## The conservative strategy of RobotCode

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

## How to avoid `VariableNotFound` errors

### Definition of cross-scope variables in the `*** Variables ***` section

TODO

#### Checking default values

### Using keywords with RETURN

TODO
