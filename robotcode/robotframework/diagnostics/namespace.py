import asyncio
import ast
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple, cast
from pathlib import Path
import threading
from ...language_server.types import Diagnostic, DiagnosticSeverity, Range, Position

from ...utils.async_itertools import async_chain
from ..utils.async_visitor import AsyncVisitor

from .library_manager import DEFAULT_LIBRARIES, KeywordDoc, LibraryDoc, LibraryManager

RESOURCE_EXTENSIONS = (".resource", ".robot", ".txt", ".tsv", ".rst", ".rest")


class RobotImportError(Exception):
    pass


@dataclass
class Import:
    name: str
    line_no: int
    col_offset: int
    end_lineno: int
    end_col_offset: int


@dataclass
class LibraryImport(Import):
    args: Tuple[str, ...] = ()
    alias: Optional[str] = None


@dataclass
class ResourceImport(Import):
    pass


@dataclass
class VariablesImport(Import):
    args: Tuple[str, ...] = ()


class ImportVisitor(AsyncVisitor):
    async def get(self, model: ast.AST) -> List[Import]:
        self._results: List[Import] = []
        await self.visit(model)
        return self._results

    async def visit_Section(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.model.blocks import SettingSection

        if isinstance(node, SettingSection):
            await self.generic_visit(node)

    async def visit_LibraryImport(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.model.statements import LibraryImport as RobotLibraryImport

        n = cast(RobotLibraryImport, node)
        self._results.append(
            LibraryImport(
                name=str(n.name),
                args=n.args,
                alias=n.alias,
                line_no=node.lineno,
                col_offset=node.col_offset,
                end_lineno=node.end_lineno if node.end_lineno is not None else -1,
                end_col_offset=node.end_col_offset if node.end_col_offset is not None else -1,
            )
        )

    async def visit_ResourceImport(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.model.statements import ResourceImport as RobotResourceImport

        n = cast(RobotResourceImport, node)
        self._results.append(
            ResourceImport(
                name=str(n.name),
                line_no=node.lineno,
                col_offset=node.col_offset,
                end_lineno=node.end_lineno if node.end_lineno is not None else -1,
                end_col_offset=node.end_col_offset if node.end_col_offset is not None else -1,
            )
        )

    async def visit_VariablesImport(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.model.statements import VariablesImport as RobotVariablesImport

        n = cast(RobotVariablesImport, node)
        self._results.append(
            VariablesImport(
                name=str(n.name),
                args=n.args,
                line_no=node.lineno,
                col_offset=node.col_offset,
                end_lineno=node.end_lineno if node.end_lineno is not None else -1,
                end_col_offset=node.end_col_offset if node.end_col_offset is not None else -1,
            )
        )


@dataclass
class LibraryEntry:
    name: str
    library_doc: LibraryDoc
    args: Tuple[Any, ...] = ()
    alias: Optional[str] = None


class Namespace:
    def __init__(self, library_manager: LibraryManager, model: ast.AST, source: str) -> None:
        super().__init__()
        self.library_manager = library_manager
        self.model = model
        self.source = source
        self._libraries_lock = threading.RLock()
        self._libraries: OrderedDict[str, LibraryEntry] = OrderedDict()
        self._initialzed = False
        self._model_library_doc: Optional[LibraryDoc] = None

        self._diagnostics_lock = threading.RLock()
        self._diagnostics: List[Diagnostic] = []

        self._keywords: Optional[List[KeywordDoc]] = None

    async def get_diagnostisc(self) -> List[Diagnostic]:
        await self._ensure_initialized()

        with self._diagnostics_lock:
            return self._diagnostics

    async def get_libraries(self) -> OrderedDict[str, LibraryEntry]:
        with self._libraries_lock:
            return self._libraries

    async def _ensure_initialized(self) -> None:
        if not self._initialzed:
            self._initialzed = True

            self._model_library_doc = await self._import_self(self.model, self.source, add_diagnostics=True)

    async def _import_imports(self, model: ast.AST, base_dir: str, *, add_diagnostics: bool = False) -> None:
        for value in await ImportVisitor().get(model):
            try:
                if isinstance(value, LibraryImport):
                    await self._import_library(value.name, value.args, value.alias, base_dir)
                elif isinstance(value, ResourceImport):
                    await self._import_resource(value.name, base_dir)
                elif isinstance(value, VariablesImport):
                    await self._import_variables(value.name, value.args, base_dir)
            except asyncio.CancelledError:
                raise
            except (SystemExit, KeyboardInterrupt):
                raise
            except BaseException as e:
                if add_diagnostics:
                    with self._diagnostics_lock:
                        self._diagnostics.append(
                            Diagnostic(
                                range=Range(
                                    start=Position(line=value.line_no - 1, character=value.col_offset),
                                    end=Position(line=value.end_lineno - 1, character=value.end_col_offset),
                                ),
                                message=str(e),
                                severity=DiagnosticSeverity.ERROR,
                                source="Robot",
                            )
                        )

    async def _import_default_libraries(self) -> None:
        for library in DEFAULT_LIBRARIES:
            await self._import_library(library, (), None, str(Path(self.source).parent))

    async def _import_library(
        self, name: str, args: Tuple[Any, ...], alias: Optional[str], base_dir: str
    ) -> Optional[LibraryDoc]:
        library = await self.library_manager.get_doc_from_library(name, args, base_dir=str(Path(self.source).parent))
        with self._libraries_lock:
            self._libraries[alias or library.name or name] = LibraryEntry(
                name=library.name, library_doc=library, args=args, alias=alias
            )

        return library

    async def _import_resource(self, name: str, base_dir: str) -> LibraryDoc:
        from robot.utils.robotpath import find_file
        from robot.api import get_resource_model

        source = find_file(name, base_dir or ".", "Resource")

        extension = Path(source).suffix
        if Path(source).suffix.lower() not in RESOURCE_EXTENSIONS:
            raise RobotImportError(
                f"Invalid resource file extension '{extension}'. "
                f"Supported extensions are {', '.join(repr(s) for s in RESOURCE_EXTENSIONS)}."
            )

        model = get_resource_model(source)

        library = await self._import_self(model, source)

        with self._libraries_lock:
            self._libraries[library.name or name] = LibraryEntry(
                name=library.name, library_doc=library, args=(), alias=None
            )

        return library

    async def _import_variables(self, name: str, args: Tuple[Any, ...], base_dir: str) -> LibraryDoc:
        raise NotImplementedError()

    async def _import_self(self, model: ast.AST, source: str, *, add_diagnostics: bool = False) -> LibraryDoc:
        await self._import_default_libraries()
        await self._import_imports(model, str(Path(source).parent), add_diagnostics=add_diagnostics)

        library_doc = await self.library_manager.get_doc_from_model(model, source)

        return library_doc

    async def get_keywords(self) -> List[KeywordDoc]:
        await self._ensure_initialized()
        if self._keywords is None:

            with self._libraries_lock:
                self._keywords = [
                    e
                    async for e in async_chain(
                        *(e.library_doc.keywords for e in self._libraries.values()),
                        self._model_library_doc.keywords if self._model_library_doc is not None else [],
                    )
                ]

        return self._keywords

    async def find_keyword(self, name: str) -> List[KeywordDoc]:
        name = name.upper()
        return [kw for kw in await self.get_keywords() if kw.name.upper() == name]
