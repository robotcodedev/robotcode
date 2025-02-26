# Avoiding a Global Resource File

In many Robot Framework projects, there is a temptation to simplify setup by consolidating all resources and libraries into one global file—often named something like `Keywords.resource`—which is then usually the only resource imported into suites and other resource files. At first glance, this strategy appears to streamline the project structure by reducing the number of explicit imports and centralizing common functionality. However, while this approach may save time during initial configuration, it masks underlying design issues and introduces several long-term challenges. These challenges range from complex circular dependencies and naming collisions to performance slowdowns and decreased maintainability, which ultimately hinder the scalability and robustness of the test suite.

## Why This Approach is Problematic

- **Circular Dependencies:**
  Using one global file in multiple keyword resource files can create circular dependencies. While Robot Framework does not display warnings during execution, RobotCode flags these issues with warnings about already imported files or circular references. These warnings highlight poor design practices that complicate dependency management, hinder refactoring, and reduce modularity. Tightly coupled components can lead to cascading errors when changes are made.

- **Ambiguities in Keyword Resolution and Variable Precedence:**
  In Robot Framework, keywords are not silently overwritten. Instead, if multiple keywords with the same name are present, test execution fails due to ambiguous matches. This forces test writers to explicitly decide which resource's keyword to use, thereby increasing the effort during test case creation. Additionally, variables behave differently: the first variable declaration takes precedence, and all subsequent declarations in other variable sections from different resource files are ignored. Consequently, when using a global resource file, you must carefully manage the order in which resources are imported to ensure the intended variable values are used—further adding to the overall complexity.

- **Performance Issues:**
  For every keyword call, Robot Framework iterates through the entire list of known keywords—and code analysis tools like RobotCode must do the same. The performance impact significantly depends on whether the system checks 50, 500, or even 5000 keywords; indeed, 500 to 5000 keywords is a realistic number in an average project. This process is especially time-consuming with embedded arguments that require regular expressions rather than simple string comparisons. A large global file filled with rarely used elements can significantly slow down keyword resolution, particularly in larger projects.

- **Decreased Maintainability:**
  While the number of resource files may be relatively small—perhaps 50 to 100—the combined global resource file can easily contain 500 or more keywords. This consolidation makes it difficult for test writers to quickly locate the relevant keyword or variable among hundreds of entries. The dense aggregation reduces clarity and increases the maintenance burden, as even a small change might affect multiple areas of the project. Refactoring becomes more challenging when the entire functionality is bundled into a single file, since updates or corrections must be made with care to avoid unintended side effects across the project.

- **Creation of Unnecessary References:**
  Relying on a centralized file forces all suites and resource files to reference the same global file, even if they only need a subset of its contents. This means that every suite is indirectly coupled to every keyword and variable in that file, regardless of whether they are used. Such an arrangement makes it difficult to determine which keywords are actually needed for a given suite. When updates or refactoring are required, developers may unintentionally modify or remove elements that other parts of the project still depend on. This extra layer of indirection complicates resource tracking, increases the likelihood of errors during maintenance, and can create confusion in larger teams where multiple developers modify the global file simultaneously.

## Documenting with Suite Settings

Declaring libraries and resources in the suite settings is not only a configuration step—it also serves as essential documentation. Test suites and test cases are more than just executable code; they document which functional areas of the application are under test. By explicitly declaring the required libraries and resources (e.g., for login processes, customer management, or database validations), you provide clear insight into the suite’s focus.

For example:

```robot
*** Settings ***
Library   LoginProcess
Resource  CustomerManagement.resource
Resource  DatabaseValidation.resource
```

This explicit declaration improves maintainability and helps new team members, stakeholders, and automated systems quickly understand the application areas being validated.

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
│   └───UserData.py
├── resources/
│   ├── api/
│   │   ├── authentication.resource    # API auth keywords
│   │   ├── customers.resource         # Customer API endpoints
│   │   └── orders.resource           # Order API endpoints
│   ├── functional/
│   │   ├── users.resource       # Login page interactions
│   │   ├── customers.resource    # Customer page interactions
│   ├── ui/
│   │   ├── login.resource       # Login page interactions
│   │   ├── customers.resource    # Customer page interactions
│   │   └── common_elements.resource  # Shared UI elements
│   └── common/
│       ├── test_data.resource        # Test data generation
│       └── utilities.resource        # General helper keywords
└── tests/
    ├── api/
    │   └── customer_api_tests.robot  # Imports only api/customers.resource
    ├── api/
    └── business/
        └── contracts.robot         # Imports only ui/login_page.resource
    └── ui_tests/
        └── login_tests.robot         # Imports only ui/login_page.resource
```

In this structure, each test file imports only the specific resources it needs, avoiding a global import file. If you put the `resources` folder to your python path (this is the default for RobotCode)

Your settings section in a resource file for functional keywords, can be look like this:

```robot
*** Settings ***
# In login_tests.robot
Resource          ui/login.resource
Resource          ui/customers.resource
Resource          common/test_data.resource

```

and if you have a suite for functional tests, like this:

```robot
*** Settings ***
# In contracts.robot
Resource          functional/users.resource
Resource          functional/customers.resource
Resource          common/test_data.resource

```

### Migration Guide: From Global to Modular Structure

If you have an existing project with a large global resource file, consider this incremental approach:

1. **Analyze usage patterns**:
   - Identify which keywords/variables are actually used in each test suite
   - Look for natural functional groupings (UI, API, data generation, etc.)

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

For keywords that are genuinely used everywhere, consider keeping a minimal `common.resource` file, but ensure it only contains truly global utilities.


## When Restructuring Isn’t Possible

If restructuring your project isn’t an option, you can mitigate potential issues by managing warnings from your development environment. For example, you can suppress warnings related to circular dependencies and redundant imports on a per-file basis or globally.

### Suppress Warnings in Specific Files

Use directives to disable warnings for circular dependencies and already-imported resources on a per-file basis.

```robot
# robotcode: ignore[*ResourceAlreadyImported*, PossibleCircularImport]
*** Settings ***
Variables  variables

Resource  already_imported.resource  # robotcode: ignore[ResourceAlreadyImported]
Resource  circular_import.resource  # robotcode: ignore[PossibleCircularImport]
```

### Suppress Warnings Globally

For global suppression in VS Code, add the following to your `settings.json`:

```json
"robotcode.analysis.diagnosticModifiers.ignore": [
    "PossibleCircularImport",
    "CircularImport",
    "ResourceAlreadyImported",
    "VariablesAlreadyImported",
    "LibraryAlreadyImported"
]
```

Alternatively, to remain IDE-independent, use a [`robot.toml`](/03_reference/config) file with these contents:

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

## Conclusion

In summary, while a single global resource file might simplify the initial setup by reducing the number of imports, it ultimately creates more problems than it solves. Issues such as circular dependencies, naming collisions, performance degradation, and decreased maintainability quickly outweigh the initial convenience. A modular resource structure adheres to clean code principles and ensures that suite settings serve as clear, documented indicators of which parts of the application are under test. If a centralized file is unavoidable, selectively suppressing warnings can help manage the associated risks.
