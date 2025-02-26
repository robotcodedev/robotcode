# Tips and Tricks

Here are some tips and tricks that you might find useful when working with RobotCode.

Here’s a refined version that keeps the structure and details while improving clarity and readability:  


## Resolving Imports from a Central `common.resource` File  

### Why is it not a good idea?  
Currently, the RobotCode extension does not support automatically resolving imports from a centralized `common.resource` file for all test cases and keyword files. Additionally, structuring a project this way is generally not considered best practice due to several issues:  

- **Circular Imports**: If `common.resource` is imported into keyword resource files, circular dependencies may arise, leading to warnings or unexpected behavior, as this file is often already included in other parts of the project.  
- **Risk of Overwriting Keywords or Variables**: A single `common.resource` file increases the likelihood of accidental overwrites of keywords or variables with the same name, making debugging difficult and causing unpredictable test execution.  
- **Performance Issues**: Robot Framework processes all known keywords and variables during execution to resolve calls and prevent conflicts. A large `common.resource` file with many unused keywords and variables significantly slows down processing, especially in big projects.  
- **Increased Complexity for Users**: When a single file contains hundreds or thousands of keywords, test writers may struggle to locate the relevant ones, reducing productivity and complicating test creation.  

### How to properly solve it?  
The recommended approach is to **modularize your resources**:  

- Keep `common.resource` minimal, only including libraries and resources that are genuinely required across all test cases and keyword files.  
- Instead of centralizing everything, **import only the necessary resources** in each test case or keyword file.  
- Organize similar resources into separate files, such as:  
  - Business-specific (functional) keywords  
  - Technical keywords (e.g., interacting with databases, APIs, or UI elements)  
- This structure **eliminates circular import issues** and ensures better maintainability.  

### What if I cannot change the structure?  
If modifying the structure is not an option, you can suppress RobotCode warnings about circular imports and already-imported resources.  

**Option 1: Disable Warnings in Specific Files**  
You can disable these warnings directly in your resource or test files using RobotCode directives:  

```robot
# robotcode: ignore[*ResourceAlreadyImported*, PossibleCircularImport]
*** Settings ***
Variables  variables

Resource  already_imported.resource  # robotcode: ignore[ResourceAlreadyImported]
Resource  circular_import.resource  # robotcode: ignore[PossibleCircularImport]
```
- The first line disables all relevant warnings for the entire file.  
- Alternatively, you can place `# robotcode: ignore[...]` next to individual imports.  

**Option 2: Disable Warnings Globally in VS Code**  
If you want to suppress these warnings for the entire project, modify the RobotCode settings in VS Code:  
- Go to **Settings**  
- Search for `robotcode.analysis.diagnosticModifiers.ignore`  
- Add the following warning codes: `ResourceAlreadyImported`, `PossibleCircularImport`  

### Conclusion  
A **modular resource structure** is the best approach to avoid performance, maintainability, and debugging issues. However, if a centralized `common.resource` file is unavoidable, you can mitigate problems by disabling RobotCode warnings as needed.  

For a more in-depth explanation, check out this video:  
📺 **[YouTube Video Link](https://www.youtube.com/watch?v=a1b2c3d4e5f)**  

For further discussion on this topic, visit:  
🗨️ **[GitHub Discussion](https://github.com/robotcodedev/robotcode/discussions/355)**  


## Why is my non local variable "not found"?

Global, Suite, and Test scope variables in Robot Framework may raise a "Variable not found" error in RobotCode, even though they work fine during runtime. This occurs because the scope of these variables is determined dynamically at runtime, and their existence can be unpredictable. RobotCode relies on static analysis of the test data, while the actual test execution is handled dynamically, making it difficult to anticipate variable availability in certain contexts.

A best practice to prevent this error is to define variables in the `*** Variables ***` section, even for Test scope variables, and assign them default values. This approach helps RobotCode recognize the variables early in the analysis, which also improves autocompletion. For instance, defining a variable like `${MY_GLOBAL_VAR}` in the `*** Variables ***` section will ensure that RobotCode recognizes the variable, making it available for the editor and runtime. 

```robot
*** Variables ***
${GLOBAL}    Default Value

*** Settings ***
Test Setup    My Test Keyword

*** Keywords ***
My Test Keyword
    VAR    ${GLOBAL}    scope=GLOBAL

*** Test Cases ***
Example Test Case
    Log    ${GLOBAL}
``` 

This approach allows for more predictable behavior, making it easier to identify issues before runtime. By establishing variables with clear default values, you improve both the debugging process and the overall reliability of your tests.

## Customization

### Editor Style

You can change some stylings for RobotFramework files in VSCode editor, independently of the current theme. (see [Customizing a Color Theme](https://code.visualstudio.com/docs/getstarted/themes#_customizing-a-color-theme))

See the difference:

| Before                                                            | After                                                       |
| ----------------------------------------------------------------- | ----------------------------------------------------------- |
| ![Without customization](./images/without_customization.gif) | ![With customization](./images/with_customization.gif) |


As a template you can put the following code to your user settings of VSCode.

Open the user `settings.json` like this:

<kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>P</kbd> or <kbd>F1</kbd> or <kbd>CMD</kbd> + <kbd>Shift</kbd> + <kbd>P</kbd>

and then type:

`Preferences: Open Settings (JSON)`

put this to the `settings.json`

```jsonc
"editor.tokenColorCustomizations": {
    "textMateRules": [
        {
            "scope": "variable.function.keyword-call.inner.robotframework",
            "settings": {
                "fontStyle": "italic"
            }
        },
        {
            "scope": "variable.function.keyword-call.robotframework",
            "settings": {
                //"fontStyle": "bold"
            }
        },
        {
            "scope": "string.unquoted.embeddedArgument.robotframework",
            "settings": {
                "fontStyle": "italic"
            }
        },
        {
            "scope": "entity.name.function.testcase.name.robotframework",
            "settings": {
                "fontStyle": "bold underline"
            }
        },
        {
            "scope": "entity.name.function.keyword.name.robotframework",
            "settings": {
                "fontStyle": "bold italic"
            }
        },
        {
            "scope": "variable.name.readwrite.robotframework",
            "settings": {
                //"fontStyle": "italic",
            }
        },
        {
            "scope": "keyword.control.import.robotframework",
            "settings": {
                "fontStyle": "italic"
            }
        },
        {
            "scope": "keyword.other.header.setting.robotframework",
            "settings": {
                "fontStyle": "bold underline"
            }
        },
        {
            "scope": "keyword.other.header.variable.robotframework",
            "settings": {
                "fontStyle": "bold underline"
            }
        },
        {
            "scope": "keyword.other.header.testcase.robotframework",
            "settings": {
                "fontStyle": "bold underline"
            }
        },
        {
            "scope": "keyword.other.header.keyword.robotframework",
            "settings": {
                "fontStyle": "bold underline"
            }
        },
        {
            "scope": "keyword.other.header.setting.robotframework",
            "settings": {
                "fontStyle": "bold underline"
            }
        },
        {
            "scope": "keyword.other.header.comment.robotframework",
            "settings": {
                "fontStyle": "bold italic underline"
            }
        },
        {
            "scope": "string.unquoted.escape.robotframework",
            "settings": {
                //"foreground": "#FF0000",
            }
        }
    ]
},

"editor.semanticTokenColorCustomizations": {
    "rules": {
        "*.documentation:robotframework": {
            "fontStyle": "italic",
            //"foreground": "#aaaaaa"
        }
    }
}

```
