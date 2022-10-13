import asyncio
from pathlib import Path
from typing import List

from robotcode.language_server.robotframework.diagnostics.library_doc import (
    RESOURCE_FILE_EXTENSION,
    ROBOT_FILE_EXTENSION,
)
from robotcode.utils.glob_path import iter_files

exclude_patterns: List[str] = [
    "**/.git/**",
    "**/node_modules/**",
    "**/.pytest_cache/**",
    "**/__pycache__/**",
    "**/.mypy_cache/**",
]


async def main() -> None:
    for f in iter_files(
        Path("c:/develop/robot/robotframework"),
        f"**/*.{{{ROBOT_FILE_EXTENSION[1:]},{RESOURCE_FILE_EXTENSION[1:]}}}",
        ignore_patterns=exclude_patterns,
        absolute=True,
    ):
        print(f)


if __name__ == "__main__":
    asyncio.run(main())
