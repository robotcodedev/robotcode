# ruff: noqa: RUF009
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from robotcode.robot.config.model import BaseOptions, field


class CacheSaveLocation(Enum):
    WORKSPACE_FOLDER = "workspaceFolder"
    WORKSPACE_STORAGE = "workspaceStorage"


@dataclass
class AnalyzerConfig(BaseOptions):
    select: Optional[List[str]] = field(description="Selects which rules are run.")
    extend_select: Optional[List[str]] = field(description="Extends the rules which are run.")
    ignore: Optional[List[str]] = field(description="Defines which rules are ignored.")
    extend_ignore: Optional[List[str]] = field(description="Extends the rules which are ignored.")
    exclude_patterns: List[str] = field(default_factory=list)

    cache_dir: Optional[str] = field(description="Path to the cache directory.")

    ignored_libraries: List[str] = field(
        default_factory=list,
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
    ignored_variables: List[str] = field(
        default_factory=list,
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

    global_library_search_order: List[str] = field(
        default_factory=list,
        description="""\
            TODO
        """,
    )
