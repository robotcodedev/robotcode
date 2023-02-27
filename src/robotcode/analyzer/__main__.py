import asyncio
import contextlib
import traceback
from pathlib import Path
from typing import Any, Iterator, List, Set, Tuple

from robot.api import get_model
from robot.api.parsing import Keyword, LibraryImport, ResourceImport, TestCase, VariablesImport

from robotcode.language_server.robotframework.diagnostics.library_doc import (
    RESOURCE_FILE_EXTENSION,
    ROBOT_FILE_EXTENSION,
)
from robotcode.language_server.robotframework.utils.ast_utils import iter_nodes
from robotcode.language_server.robotframework.utils.async_ast import AsyncVisitor
from robotcode.utils.glob_path import iter_files

exclude_patterns: List[str] = [
    "**/.git/**",
    "**/node_modules/**",
    "**/.pytest_cache/**",
    "**/__pycache__/**",
    "**/.mypy_cache/**",
]


@contextlib.contextmanager
def timed(name: str) -> Iterator[None]:
    import time

    start = time.time()
    yield
    print(f"{name} took {time.time() - start} seconds")


class CounterVisitor(AsyncVisitor):
    def __init__(self) -> None:
        self.testcases = 0
        self.keywords = 0
        self.library_imports: Set[Tuple[Any, ...]] = set()
        self.resources_imports: Set[Tuple[Any, ...]] = set()
        self.variables_imports: Set[Tuple[Any, ...]] = set()

    async def visit_TestCase(self, node: TestCase) -> None:  # noqa: N802
        self.testcases += 1
        await super().generic_visit(node)

    async def visit_Keyword(self, node: TestCase) -> None:  # noqa: N802
        self.keywords += 1
        await super().generic_visit(node)

    async def visit_LibraryImport(self, node: TestCase) -> None:  # noqa: N802
        self.library_imports.add((node.name, node.args, node.alias))
        await super().generic_visit(node)

    async def visit_ResourceImport(self, node: TestCase) -> None:  # noqa: N802
        self.resources_imports.add((node.name))
        await super().generic_visit(node)

    async def visit_VariablesImport(self, node: TestCase) -> None:  # noqa: N802
        self.variables_imports.add((node.name, node.args))
        await super().generic_visit(node)


async def main() -> None:
    testcases = 0
    keywords = 0
    library_imports = set()
    resources_imports = set()
    variables_imports = set()
    with timed("get_model"):
        for f in iter_files(
            Path("c:/develop/robot/robotframework"),
            f"**/*.{{{ROBOT_FILE_EXTENSION[1:]},{RESOURCE_FILE_EXTENSION[1:]}}}",
            ignore_patterns=exclude_patterns,
            absolute=True,
        ):
            try:
                model = get_model(f, curdir=str(f.parent))
                for node in iter_nodes(model):
                    if isinstance(node, TestCase):
                        testcases += 1
                    if isinstance(node, Keyword):
                        keywords += 1
                    if isinstance(node, LibraryImport):
                        library_imports.add((node.name, node.args, node.alias))
                    if isinstance(node, ResourceImport):
                        resources_imports.add((node.name))
                    if isinstance(node, VariablesImport):
                        variables_imports.add((node.name, node.args))
            except (KeyboardInterrupt, SystemExit):
                raise
            except BaseException as e:
                print(f"Error: {e} ({f})")
                print(traceback.format_exc())

    print(f"Found {testcases} testcases")
    print(f"Found {keywords} keywords")
    print(f"Found {len(library_imports)} library imports")
    print(f"Found {len(resources_imports)} resource imports")
    print(f"Found {len(variables_imports)} variables imports")

    visitor = CounterVisitor()
    with timed("get_model"):
        for f in iter_files(
            Path("c:/develop/robot/robotframework"),
            f"**/*.{{{ROBOT_FILE_EXTENSION[1:]},{RESOURCE_FILE_EXTENSION[1:]}}}",
            ignore_patterns=exclude_patterns,
            absolute=True,
        ):
            try:
                model = get_model(f, curdir=str(f.parent))
                await visitor.visit(model)
            except (KeyboardInterrupt, SystemExit):
                raise
            except BaseException as e:
                print(f"Error: {e} ({f})")
                print(traceback.format_exc())

    print(f"Found {visitor.testcases} testcases")
    print(f"Found {visitor.keywords} keywords")
    print(f"Found {len(visitor.library_imports)} library imports")
    print(f"Found {len(visitor.resources_imports)} resource imports")
    print(f"Found {len(visitor.variables_imports)} variables imports")


if __name__ == "__main__":
    asyncio.run(main())
