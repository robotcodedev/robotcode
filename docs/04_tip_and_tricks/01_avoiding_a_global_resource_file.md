# Avoiding a Global Resource File

## Introduction

In many Robot Framework projects, there is a temptation to simplify setup by consolidating all resources and libraries into one global file—often named something like `Keywords.resource`—which is then usually the only resource imported into suites and other resource files.

**Executive Summary**: While global resource files might seem convenient initially, they lead to circular dependencies, keyword ambiguities, performance issues, and maintenance challenges. This guide explains the problems of this approach and offers a modular alternative that improves code organization, maintainability, and performance.

## Why This Approach is Problematic

- **Circular Dependencies:**
  Using one global file in multiple keyword resource files can create circular dependencies. While Robot Framework does not display warnings during execution, RobotCode flags these issues with warnings about already imported files or circular references. These warnings highlight poor design practices that complicate dependency management, hinder refactoring, and reduce modularity. Tightly coupled components can lead to cascading errors when changes are made.

- **Ambiguities in Keyword Resolution and Variable Precedence:**
  In Robot Framework, keywords are not silently overwritten. Instead, if multiple keywords with the same name are present, test execution fails due to ambiguous matches. This forces test writers to explicitly decide which resource's keyword to use, thereby increasing the effort during test case creation. Additionally, variables behave differently: the first variable declaration takes precedence, and all subsequent declarations in other variable sections from different resource files are ignored. Consequently, when using a global resource file, you must carefully manage the order in which resources are imported to ensure the intended variable values are used—further adding to the overall complexity.

- **Performance Issues:**
  For every keyword call, Robot Framework iterates through the entire list of known keywords—and code analysis tools like RobotCode must do the same. The performance impact significantly depends on whether the system checks 50, 500, or even 5000 keywords; indeed, 500 to 5000 keywords is a realistic number in an average project. This process is especially time-consuming with embedded arguments that require regular expressions rather than simple string comparisons. A large global file filled with rarely used elements can significantly slow down keyword resolution, particularly in larger projects.

  *Heuristic:* If a global resource file contains more than ~200 keywords or imports more than ~20 resource files, consider modularizing to improve performance and maintainability.

- **Decreased Maintainability:**
  While the number of resource files may be relatively small—perhaps 50 to 100—the combined global resource file can easily contain 500 or more keywords. This consolidation makes it difficult for test writers to quickly locate the relevant keyword or variable among hundreds of entries. The dense aggregation reduces clarity and increases the maintenance burden, as even a small change might affect multiple areas of the project. Refactoring becomes more challenging when the entire functionality is bundled into a single file, since updates or corrections must be made with care to avoid unintended side effects across the project.

- **Creation of Unnecessary References:**
  Relying on a centralized file forces all suites and resource files to reference the same global file, even if they only need a subset of its contents. This means that every suite is indirectly coupled to every keyword and variable in that file, regardless of whether they are used. Such an arrangement makes it difficult to determine which keywords are actually needed for a given suite. When updates or refactoring are required, developers may unintentionally modify or remove elements that other parts of the project still depend on. This extra layer of indirection complicates resource tracking, increases the likelihood of errors during maintenance, and can create confusion in larger teams where multiple developers modify the global file simultaneously.

### Example of Problematic Global Resource File

Consider this example of a typical global resource file that causes issues:

```robot
*** Settings ***
# Global.resource - tries to do everything
Library    SeleniumLibrary
Library    RequestsLibrary
Library    DatabaseLibrary
Library    OperatingSystem
Resource   LoginKeywords.resource
Resource   CustomerKeywords.resource
Resource   OrderKeywords.resource
Resource   ApiKeywords.resource
Resource   ReportingKeywords.resource
# ...and 20+ more imports

*** Variables ***
${GLOBAL_URL}    https://example.com
${DB_CONNECTION}    connection_string
# ...hundreds of variables for different modules

*** Keywords ***
# 500+ keywords covering every aspect of the system
```

Note: importing the same library or resource with different parameters in different places can lead to earlier instances being reused or overwritten, causing surprising behavior. Avoid parameterized duplicates and prefer small, purpose-specific imports.

When this file gets imported into multiple other resources and suite files, it creates a tangled web of dependencies.

## Documenting with Suite Settings

Suite settings do more than just configure your test environment—they serve as essential documentation for your project. When you explicitly declare libraries, resources and also variables in your settings section, you're creating a clear record of which technical or functional areas of the application are being used in this file. This transparency helps team members, stakeholders, and testers quickly understand the suite's purpose.

For example:

```robot
*** Settings ***
Library   LoginProcess
Resource  CustomerManagement.resource
Resource  DatabaseValidation.resource
```

This declaration immediately communicates that this suite deals with login processes, customer management, and database validation—improving maintainability and knowledge transfer within your team.

## Limitations in Import and Package Management

Robot Framework’s import mechanism is quite basic—it lacks namespaces or similar constructs found in other programming languages. Instead, it relies solely on a name alias for libraries or the resource file name. Although Robot Framework does not flag multiple imports as errors, this simplicity can lead to issues. For instance, importing the same library with different parameters may result in the earlier instance being overwritten, causing unpredictable behavior. This limitation is often discussed in roadmap conversations, with hopes that future versions of Robot Framework will include more robust support for modular imports and package management.

## Clean Code Considerations

Adhering to clean code principles is crucial for building maintainable, readable, and scalable projects. A modular approach offers several benefits:

- **Separation of Concerns:**
  Grouping resources into logically separated files ensures each file has a clear, focused purpose, making the codebase easier to understand and maintain.

- **Enhanced Readability:**
  Smaller, purpose-driven files improve readability, enabling developers to quickly locate and modify only the necessary parts of the code.

- **Simplified Dependency Management:**
  Reducing inter-file references decreases coupling. This separation limits the impact of changes and makes your project more resilient.

- **Ease of Refactoring:**
  When resources are organized into well-defined modules, refactoring becomes more straightforward. Developers can update or replace specific components without unintended side effects on unrelated parts.

## The Better Approach: Modularization

The recommended solution is to **modularize your resources**:

- **Keep the Global File Minimal:**
  Restrict the global resource file to only those libraries and resources that are truly needed across all test cases and keyword files.

- **Import Only What’s Needed:**
  Instead of centralizing everything, selectively import only the necessary resources into each test case or keyword file.

- **Organize Resources by Function:**
  Structure your project by grouping resources into files based on their function. For example, separate business-specific keywords from technical ones (such as those for database or API interactions).

This modular approach not only eliminates issues like circular dependencies and performance bottlenecks but also enhances maintainability and clarity. It ensures that suite settings clearly document which components are required for each test suite.

### Example

A well-organized Robot Framework project might have a structure like this:

```
project/
├── lib/
│   └── UserData.py
├── resources/
│   ├── api/
│   │   ├── authentication.resource    # API auth keywords
│   │   ├── customers.resource         # Customer API endpoints
│   │   └── orders.resource            # Order API endpoints
│   ├── functional/
│   │   ├── users.resource             # User domain keywords
│   │   ├── customers.resource         # Customer domain keywords
│   ├── ui/
│   │   ├── login.resource             # Login page interactions
│   │   ├── customers.resource         # Customer page interactions
│   │   └── common_elements.resource   # Shared UI elements
│   └── common/
│       ├── test_data.resource         # Test data generation
│       └── utilities.resource         # General helper keywords
└── tests/
    ├── api/
    │   └── customer_api_tests.robot   # Imports only api/customers.resource
    ├── business/
    │   └── contracts.robot            # Imports only ui/login.resource
    └── ui_tests/
        └── login_tests.robot          # Imports only ui/login.resource
```

In this structure, each test file imports only the specific resources it needs, avoiding a global import file. Note: Robot Framework resolves Resource imports relative to the importing file (or via absolute paths). PYTHONPATH applies to Python libraries, not resource files. RobotCode can configure analysis and discovery paths via robot.toml.

Your suite settings can look like this:

::: code-group

```robot [login.robot]
*** Settings ***
Resource          ui/login.resource
Resource          ui/customers.resource
Resource          common/test_data.resource

```

:::

and if you have a suite for functional tests, it can look like this:

::: code-group

```robot [contracts.robot]
*** Settings ***
Resource          functional/users.resource
Resource          functional/customers.resource
Resource          common/test_data.resource

```

:::

### Migration Guide: From Global to Modular Structure

If you have an existing project with a large global resource file, consider this incremental approach:

1. **Analyze usage patterns**:
   - Identify which keywords/variables are actually used in each test suite
   - Look for natural functional groupings (UI, API, data generation, etc.)
   - Measure counts (keywords, variables, and resource imports) per file to prioritize refactoring; use a threshold (for example ~200 keywords) as a guide.

2. **Create specialized resource files**:
   - Start with one functional area (e.g., login functionality)
   - Extract relevant keywords into a new `login.resource` file
   - Maintain the original global file temporarily

3. **Gradual transition**:
   - Update one test suite at a time to use the specific resource
   - Keep the global import during transition for backward compatibility
   - Run tests after each change to verify functionality

4. **Progressive cleanup**:
   - Once all suites using specific functionality import the correct resource file
   - Remove those keywords from the global file
   - Eventually phase out the global file completely

Here's a concrete example of refactoring from a global approach to a modular one:

**Before (Global.resource):**

::: code-group

```robot [/tests/login_test.robot]
*** Settings ***
# Anti-pattern: single global import
Resource    resources/Global.resource

*** Test Cases ***
Valid Login
    Login To Application    valid_user    valid_password
    Get Customer Details    123
```

```robot [/resources/Global.resource]
*** Settings ***
Library    SeleniumLibrary
Library    RequestsLibrary
Library    Collections
Resource   common/test_data.resource
Resource   common/utility.resource

*** Keywords ***
Login To Application
    [Arguments]    ${username}    ${password}
    Open Browser    ${URL}    ${BROWSER}
    Input Text    id=username    ${username}
    Input Password    id=password    ${password}
    Click Button    id=login-button

Get Customer Details
    [Arguments]    ${customer_id}
    ${response}=    GET    ${API_URL}/customers/${customer_id}
    RETURN    ${response.json()}
```

:::

**After:**

::: code-group

```robot [/tests/login_test.robot]
*** Settings ***
# Only importing what is needed
Resource    ui/login.resource
Resource    api/customers.resource

*** Test Cases ***
Valid Login
    Login To Application    valid_user    valid_password
    Get Customer Details    123
```

```robot [/resources/ui/login.resource]
*** Settings ***
Library    SeleniumLibrary
Resource   common/utility.resource

*** Keywords ***
Login To Application
    [Arguments]    ${username}    ${password}
    Open Browser    ${URL}    ${BROWSER}
    Input Text    id=username    ${username}
    Input Password    id=password    ${password}
    Click Button    id=login-button
```

```robot [/resources/api/customers.resource]
*** Settings ***
Library    RequestsLibrary

*** Keywords ***
Get Customer Details
    [Arguments]    ${customer_id}
    ${response}=    GET    ${API_URL}/customers/${customer_id}
    [Return]    ${response.json()}
```

:::

## When Restructuring Isn't Possible

If restructuring your project isn't an option, you can mitigate potential issues by managing warnings from your development environment. For example, you can suppress warnings related to circular dependencies and redundant imports on a per-file basis or globally.

It's important to understand that suppressing warnings doesn't fix the underlying issues—it merely acknowledges them. When you choose to ignore specific diagnostics, you're making a conscious decision that these particular issues are acceptable in your codebase. This explicit acknowledgment is different from simply ignoring random warnings in your IDE. By documenting suppressions in your code or configuration files, you're communicating to your team that you understand the potential problem but have determined that it's an acceptable compromise given your project's constraints.

This approach is particularly useful during transitional periods or when working with legacy codebases where perfect architectural solutions aren't immediately feasible. However, these suppressions should ideally be revisited periodically to determine if the underlying issues can eventually be resolved through refactoring.

### Suppress Warnings in Specific Files

Use directives to disable warnings for circular dependencies and already-imported resources on a per-file basis.

```robot
# example for disabling of specific messages for the whole file
# robotcode: ignore[ResourceAlreadyImported, PossibleCircularImport]
*** Settings ***
Variables  variables

# example for disabling of specific messages for a statement
Resource  already_imported.resource  # robotcode: ignore[ResourceAlreadyImported]
Resource  circular_import.resource  # robotcode: ignore[PossibleCircularImport]
```

### Suppress Warnings Globally

The preferred approach to suppress warnings globally is using a `robot.toml` configuration file. This method is IDE-independent and can be checked into version control to share with your team. Create a [`robot.toml`](/03_reference/config) file in your project root with these contents:

```toml
[tool.robotcode-analyze.modifiers]
ignore = [
    "PossibleCircularImport",
    "CircularImport",
    "ResourceAlreadyImported",
    "VariablesAlreadyImported",
    "LibraryAlreadyImported"
]
```

Alternatively, if you're working exclusively in VS Code, you can add the following to your `settings.json`, though this approach is not recommended for team environments as it only affects your local setup:

```json
"robotcode.analysis.diagnosticModifiers.ignore": [
    "PossibleCircularImport",
    "CircularImport",
    "ResourceAlreadyImported",
    "VariablesAlreadyImported",
    "LibraryAlreadyImported"
]
```

## Conclusion

In summary, while a single global resource file might simplify the initial setup by reducing the number of imports, it ultimately creates more problems than it solves. Issues such as circular dependencies, naming collisions, performance degradation, and decreased maintainability quickly outweigh the initial convenience. A modular resource structure adheres to clean code principles and ensures that suite settings serve as clear, documented indicators of which parts of the application are under test. If a centralized file is unavoidable, selectively suppressing warnings can help manage the associated risks.
