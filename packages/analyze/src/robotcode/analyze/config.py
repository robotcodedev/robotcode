# ruff: noqa: RUF009
from dataclasses import dataclass
from typing import List, Optional

from robotcode.robot.config.model import BaseOptions, field


@dataclass
class ModifiersConfig(BaseOptions):
    """Modifiers configuration."""

    ignore: Optional[List[str]] = field(
        description="""\
            Specifies the error codes to ignore.

            Examples:

            ```toml
            [tool.robotcode-analyze.modifiers]
            ignore = ["VariableNotFound", "multiple-keywords"]
            ```
        """
    )
    extend_ignore: Optional[List[str]] = field(
        description="""
            Extend the error codes to ignore.

            Examples:

            ```toml
            [tool.robotcode-analyze.modifiers]
            extend_ignore = ["VariableNotFound", "multiple-keywords"]
            ```
        """
    )
    error: Optional[List[str]] = field(
        description="""
            Specifies the error codes to treat as errors.

            Examples:

            ```toml
            [tool.robotcode-analyze.modifiers]
            error = ["VariableNotFound", "multiple-keywords"]
            ```
        """
    )
    extend_error: Optional[List[str]] = field(
        description="""
            Extend the error codes to treat as errors.

            Examples:

            ```toml
            [tool.robotcode-analyze.modifiers]
            extend_error = ["VariableNotFound", "multiple-keywords"]
            ```
        """
    )
    warning: Optional[List[str]] = field(
        description="""
            Specifies the error codes to treat as warning.

            Examples:

            ```toml
            [tool.robotcode-analyze.modifiers]
            warning = ["VariableNotFound", "multiple-keywords"]
            ```
        """
    )
    extend_warning: Optional[List[str]] = field(
        description="""
            Extend the error codes to treat as warnings.

            Examples:

            ```toml
            [tool.robotcode-analyze.modifiers]
            extend_warning = ["VariableNotFound", "multiple-keywords"]
            ```
        """
    )
    information: Optional[List[str]] = field(
        description="""
            Specifies the error codes to treat as information.

            Examples:

            ```toml
            [tool.robotcode-analyze.modifiers]
            information = ["VariableNotFound", "multiple-keywords"]
            ```
        """
    )
    extend_information: Optional[List[str]] = field(
        description="""
            Extend the error codes to treat as information.

            Examples:

            ```toml
            [tool.robotcode-analyze.modifiers]
            extend_information = ["VariableNotFound", "multiple-keywords"]
            ```
        """
    )
    hint: Optional[List[str]] = field(
        description="""
            Specifies the error codes to treat as hint.

            Examples:

            ```toml
            [tool.robotcode-analyze.modifiers]
            hint = ["VariableNotFound", "multiple-keywords"]
            ```
        """
    )
    extend_hint: Optional[List[str]] = field(
        description="""
            Extend the error codes to treat as hint.

            Examples:

            ```toml
            [tool.robotcode-analyze.modifiers]
            extend_hint = ["VariableNotFound", "multiple-keywords"]
            ```
        """
    )


@dataclass
class CacheConfig(BaseOptions):
    """Cache configuration."""

    cache_dir: Optional[str] = field(description="Path to the cache directory.")

    ignored_libraries: Optional[List[str]] = field(
        description="""\
            Specifies the library names that should not be cached.
            This is useful if you have a dynamic or hybrid library that has different keywords depending on
            the arguments. You can specify a glob pattern that matches the library name or the source file.

            Examples:
            - `**/mylibfolder/mylib.py`
            - `MyLib`\n- `mylib.subpackage.subpackage`

            For robot framework internal libraries, you have to specify the full module name like
            `robot.libraries.Remote`.
            """,
    )
    extend_ignored_libraries: Optional[List[str]] = field(description="Extend the ignored libraries setting.")

    ignored_variables: Optional[List[str]] = field(
        description="""\
            Specifies the variable files that should not be cached.
            This is useful if you have a dynamic or hybrid variable files that has different variables
            depending on the arguments. You can specify a glob pattern that matches the variable module
            name or the source file.

            Examples:
            - `**/variables/myvars.py`
            - `MyVariables`
            - `myvars.subpackage.subpackage`
            """,
    )
    extend_ignored_variables: Optional[List[str]] = field(description="Extend the ignored variables setting.")

    ignore_arguments_for_library: Optional[List[str]] = field(
        description="""\
            Specifies a list of libraries for which arguments will be ignored during analysis.
            This is usefull if you have library that gets variables from a python file as arguments that contains
            complex data like big dictionaries or complex objects that **RobotCode** can't handle.
            You can specify a glob pattern that matches the library name or the source file.

            Examples:
            - `**/mylibfolder/mylib.py`
            - `MyLib`\n- `mylib.subpackage.subpackage`

            If you change this setting, you may need to run the command
            `RobotCode: Clear Cache and Restart Language Servers`.

            _Ensure your library functions correctly without arguments e.g. by defining default
            values for all arguments._
        """
    )
    extend_ignore_arguments_for_library: Optional[List[str]] = field(
        description="Extend the ignore arguments for library settings."
    )


@dataclass
class AnalyzeConfig(BaseOptions):
    """robotcode-analyze configuration."""

    modifiers: Optional[ModifiersConfig] = field(
        description="""\
            Defines the modifiers for the analysis.

            Examples:

            ```toml
            [tool.robotcode-analyze.modifiers]
            ignore = ["VariableNotFound"]
            hint = ["KeywordNotFound"]
            information = ["MultipleKeywords"]
            ```
        """
    )
    extend_modifiers: Optional[ModifiersConfig] = field(
        description="""\
            Extends the modifiers for the analysis.

            Examples:

            ```toml
            [tool.robotcode-analyze.extend_modifiers]
            ignore = ["VariableNotFound"]
            extend-hint = ["KeywordNotFound"]
            extend-information = ["MultipleKeywords"]
            ```
        """
    )

    cache: Optional[CacheConfig] = field(description="Defines the cache configuration.")
    extend_cache: Optional[CacheConfig] = field(description="Extend the cache configuration.")

    exclude_patterns: Optional[List[str]] = field(
        description="Specifies glob patterns for excluding files and folders from analysing by the language server.",
    )
    extend_exclude_patterns: Optional[List[str]] = field(description="Extend the exclude patterns.")

    global_library_search_order: Optional[List[str]] = field(
        description="""\
            Specifies a global [search order](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#specifying-explicit-priority-between-libraries-and-resources)
            for libraries and resources.
            This is usefull when you have libraries containing keywords with the same name. **RobotCode** is unable to
            analyze the library search order in a file specified with
                [`Set Library Search Order`](https://robotframework.org/robotframework/latest/libraries/BuiltIn.html#Set%20Library%20Search%20Order),
            so you can define a global order here. Just make sure to call the `Set Library Search Order`
            keyword somewhere in your robot file or internally in your library.
        """,
    )
    extend_global_library_search_order: Optional[List[str]] = field(
        description="Extend the global library search order setting."
    )
