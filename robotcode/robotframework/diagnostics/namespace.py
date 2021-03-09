from __future__ import annotations

import ast
import asyncio
import weakref
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    cast,
)

from ...language_server.types import (
    Diagnostic,
    DiagnosticRelatedInformation,
    DiagnosticSeverity,
    Location,
    Position,
    Range,
)
from ...utils.async_itertools import async_chain
from ...utils.logging import LoggingDescriptor
from ...utils.uri import Uri
from ..utils.ast import Token as AstToken
from ..utils.ast import is_non_variable_token, range_from_token_or_node
from ..utils.async_ast import AsyncVisitor
from .imports_manager import (
    DEFAULT_LIBRARIES,
    ImportsManager,
    LibraryChangedParams,
    ResourceChangedParams,
)
from .library_doc import KeywordDoc, LibraryDoc, is_embedded_keyword

DIAGNOSTICS_SOURCE_NAME = "RobotCode"


class DiagnosticsException(Exception):
    pass


class DiagnosticsWarning(DiagnosticsException):
    pass


class ImportError(DiagnosticsException):
    pass


class KeywordError(DiagnosticsException):
    pass


@dataclass
class Token:
    line_no: int
    col_offset: int
    end_col_offset: int


@dataclass
class Import:
    name: Optional[str]
    name_token: Optional[Token]
    line_no: int
    col_offset: int
    end_line_no: int
    end_col_offset: int

    def range(self) -> Range:
        return Range(
            start=Position(
                line=self.name_token.line_no - 1 if self.name_token is not None else self.line_no - 1,
                character=self.name_token.col_offset if self.name_token is not None else self.col_offset,
            ),
            end=Position(
                line=self.name_token.line_no - 1 if self.name_token is not None else self.end_line_no - 1,
                character=self.name_token.end_col_offset if self.name_token is not None else self.end_col_offset,
            ),
        )


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


class NameSpaceError(Exception):
    pass


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
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import LibraryImport as RobotLibraryImport

        n = cast(RobotLibraryImport, node)
        name = cast(RobotToken, n.get_token(RobotToken.NAME))

        self._results.append(
            LibraryImport(
                name=n.name,
                name_token=Token(line_no=name.lineno, col_offset=name.col_offset, end_col_offset=name.end_col_offset)
                if name is not None
                else None,
                args=n.args,
                alias=n.alias,
                line_no=node.lineno,
                col_offset=node.col_offset,
                end_line_no=node.end_lineno if node.end_lineno is not None else -1,
                end_col_offset=node.end_col_offset if node.end_col_offset is not None else -1,
            )
        )

    async def visit_ResourceImport(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import ResourceImport as RobotResourceImport

        n = cast(RobotResourceImport, node)
        name = cast(RobotToken, n.get_token(RobotToken.NAME))

        self._results.append(
            ResourceImport(
                name=n.name,
                name_token=Token(line_no=name.lineno, col_offset=name.col_offset, end_col_offset=name.end_col_offset)
                if name is not None
                else None,
                line_no=node.lineno,
                col_offset=node.col_offset,
                end_line_no=node.end_lineno if node.end_lineno is not None else -1,
                end_col_offset=node.end_col_offset if node.end_col_offset is not None else -1,
            )
        )

    async def visit_VariablesImport(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import (
            VariablesImport as RobotVariablesImport,
        )

        n = cast(RobotVariablesImport, node)
        name = cast(RobotToken, n.get_token(RobotToken.NAME))

        self._results.append(
            VariablesImport(
                name=n.name,
                name_token=Token(line_no=name.lineno, col_offset=name.col_offset, end_col_offset=name.end_col_offset)
                if name is not None
                else None,
                args=n.args,
                line_no=node.lineno,
                col_offset=node.col_offset,
                end_line_no=node.end_lineno if node.end_lineno is not None else -1,
                end_col_offset=node.end_col_offset if node.end_col_offset is not None else -1,
            )
        )


class Analyzer(AsyncVisitor):
    async def get(self, model: ast.AST, namespace: "Namespace") -> List[Diagnostic]:
        self._results: List[Diagnostic] = []
        self._namespace = namespace
        await self.visit(model)
        return self._results

    async def _analyze_keyword_call(
        self,
        keyword: Optional[str],
        value: ast.AST,
        keyword_token: AstToken,
        argument_tokens: List[AstToken],
        analyse_run_keywords: bool = True,
    ) -> Optional[KeywordDoc]:
        result: Optional[KeywordDoc] = None
        try:
            finder = KeywordFinder(self._namespace)

            result = await finder.find_keyword(keyword)

            for e in finder.diagnostics:
                self._results.append(
                    Diagnostic(
                        range=range_from_token_or_node(value, keyword_token),
                        message=e.message,
                        severity=e.severity,
                        source=DIAGNOSTICS_SOURCE_NAME,
                        code=e.code,
                    )
                )

            if result is not None and result.errors:
                self._results.append(
                    Diagnostic(
                        range=range_from_token_or_node(value, keyword_token),
                        message="Keyword definition contains errors.",
                        severity=DiagnosticSeverity.ERROR,
                        source=DIAGNOSTICS_SOURCE_NAME,
                        related_information=[
                            DiagnosticRelatedInformation(
                                location=Location(
                                    uri=str(
                                        Uri.from_path(
                                            err.source
                                            if err.source is not None
                                            else result.source
                                            if result.source is not None
                                            else "/<unknown>"
                                        )
                                    ),
                                    range=Range(
                                        start=Position(
                                            line=err.line_no - 1
                                            if err.line_no is not None
                                            else result.line_no
                                            if result.line_no >= 0
                                            else 0,
                                            character=0,
                                        ),
                                        end=Position(
                                            line=err.line_no - 1
                                            if err.line_no is not None
                                            else result.line_no
                                            if result.line_no >= 0
                                            else 0,
                                            character=0,
                                        ),
                                    ),
                                ),
                                message=err.message,
                            )
                            for err in result.errors
                        ],
                    )
                )

        except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            self._results.append(
                Diagnostic(
                    range=range_from_token_or_node(value, keyword_token),
                    message=str(e),
                    severity=DiagnosticSeverity.ERROR,
                    source=DIAGNOSTICS_SOURCE_NAME,
                    code=type(e).__qualname__,
                )
            )

        if result is not None and analyse_run_keywords:
            await self._analyse_run_keyword(result, value, argument_tokens)

        return result

    async def _analyse_run_keyword(
        self, keyword_doc: Optional[KeywordDoc], node: ast.AST, argument_tokens: List[AstToken]
    ) -> List[AstToken]:

        if keyword_doc is None or not keyword_doc.is_any_run_keyword():
            return argument_tokens

        if keyword_doc.is_run_keyword() and len(argument_tokens) > 0 and is_non_variable_token(argument_tokens[0]):
            await self._analyze_keyword_call(argument_tokens[0].value, node, argument_tokens[0], argument_tokens[1:])

            return argument_tokens[1:]
        elif (
            keyword_doc.is_run_keyword_with_condition()
            and len(argument_tokens) > 1
            and is_non_variable_token(argument_tokens[1])
        ):
            await self._analyze_keyword_call(argument_tokens[1].value, node, argument_tokens[1], argument_tokens[2:])
            return argument_tokens[2:]
        elif keyword_doc.is_run_keywords():
            for t in argument_tokens:
                if is_non_variable_token(t):
                    await self._analyze_keyword_call(t.value, node, t, [])

            return []

        elif keyword_doc.is_run_keyword_if() and len(argument_tokens) > 1 and is_non_variable_token(argument_tokens[1]):

            def skip_args() -> None:
                nonlocal argument_tokens

                while argument_tokens:
                    if argument_tokens[0].value in ["ELSE", "ELSE IF"]:
                        break
                    argument_tokens = argument_tokens[1:]

            result = await self._analyze_keyword_call(
                argument_tokens[1].value,
                node,
                argument_tokens[1],
                argument_tokens[2:],
                analyse_run_keywords=False,
            )

            argument_tokens = argument_tokens[2:]

            if result is not None and result.is_any_run_keyword():
                argument_tokens = await self._analyse_run_keyword(result, node, argument_tokens)

            skip_args()

            while argument_tokens:
                if argument_tokens[0].value == "ELSE" and len(argument_tokens) > 1:

                    result = await self._analyze_keyword_call(
                        argument_tokens[1].value,
                        node,
                        argument_tokens[1],
                        argument_tokens[2:],
                        analyse_run_keywords=False,
                    )

                    argument_tokens = argument_tokens[2:]

                    if result is not None and result.is_any_run_keyword():
                        argument_tokens = await self._analyse_run_keyword(result, node, argument_tokens)

                    skip_args()

                    break
                elif argument_tokens[0].value == "ELSE IF" and len(argument_tokens) > 2:

                    result = await self._analyze_keyword_call(
                        argument_tokens[2].value,
                        node,
                        argument_tokens[2],
                        argument_tokens[3:],
                        analyse_run_keywords=False,
                    )

                    argument_tokens = argument_tokens[3:]

                    if result is not None and result.is_any_run_keyword():
                        argument_tokens = await self._analyse_run_keyword(result, node, argument_tokens)

                    skip_args()
                else:
                    break

        return argument_tokens

    async def visit_Fixture(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Fixture

        value = cast(Fixture, node)
        keyword_token = cast(AstToken, value.get_token(RobotToken.NAME))

        if keyword_token is not None:
            await self._analyze_keyword_call(
                value.name, value, keyword_token, [cast(AstToken, e) for e in value.get_tokens(RobotToken.ARGUMENT)]
            )

        await self.generic_visit(node)

    async def visit_TestTemplate(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import TestTemplate

        value = cast(TestTemplate, node)
        keyword_token = cast(AstToken, value.get_token(RobotToken.NAME))

        if keyword_token is not None:
            await self._analyze_keyword_call(value.value, value, keyword_token, [])

        await self.generic_visit(node)

    async def visit_Template(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Template

        value = cast(Template, node)
        keyword_token = cast(AstToken, value.get_token(RobotToken.NAME))

        if keyword_token is not None:
            await self._analyze_keyword_call(value.value, value, keyword_token, [])

        await self.generic_visit(node)

    async def visit_KeywordCall(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import KeywordCall

        value = cast(KeywordCall, node)
        keyword_token = cast(RobotToken, value.get_token(RobotToken.KEYWORD))

        await self._analyze_keyword_call(
            value.keyword, value, keyword_token, [cast(AstToken, e) for e in value.get_tokens(RobotToken.ARGUMENT)]
        )

        await self.generic_visit(node)

    async def visit_Keyword(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.blocks import Keyword
        from robot.parsing.model.statements import Arguments, KeywordName

        kw = cast(Keyword, node)
        if kw.name is not None:
            name_token = cast(KeywordName, kw.header).get_token(RobotToken.KEYWORD_NAME)
            if is_embedded_keyword(kw.name) and any(isinstance(v, Arguments) and len(v.values) > 0 for v in kw.body):
                self._results.append(
                    Diagnostic(
                        range=range_from_token_or_node(kw, name_token),
                        message="Keyword cannot have both normal and embedded arguments.",
                        severity=DiagnosticSeverity.ERROR,
                        source=DIAGNOSTICS_SOURCE_NAME,
                        code="KeywordError",
                    )
                )

        await self.generic_visit(node)


@dataclass
class LibraryEntry:
    name: str
    import_name: str
    library_doc: LibraryDoc
    args: Tuple[Any, ...] = ()
    alias: Optional[str] = None


@dataclass
class ResourceEntry(LibraryEntry):
    pass


class Namespace:
    _logger = LoggingDescriptor()

    @_logger.call
    def __init__(
        self,
        imports_manager: ImportsManager,
        model: ast.AST,
        source: str,
        sentinel: Any,
        invalidated_callback: Callable[[Namespace], None],
    ) -> None:
        super().__init__()

        self.imports_manager = imports_manager
        self.imports_manager.libraries_changed.add(self.libraries_changed)
        self.imports_manager.resources_changed.add(self.resources_changed)
        self.model = model
        self.source = source
        self._sentinel = weakref.ref(sentinel)
        self.invalidated_callback = invalidated_callback

        self._libraries: OrderedDict[str, LibraryEntry] = OrderedDict()
        self._resources: OrderedDict[str, ResourceEntry] = OrderedDict()
        self._initialzed = False
        self._analyzed = False
        self._library_doc: Optional[LibraryDoc] = None

        self._diagnostics: List[Diagnostic] = []

        self._keywords: Optional[List[KeywordDoc]] = None

        # TODO: how to get the search order from model
        self.search_order: Tuple[str, ...] = ()

    async def libraries_changed(self, sender: Any, params: List[LibraryChangedParams]) -> None:

        for p in params:
            c = (p.name, p.args)
            if any(e for e in self._libraries.values() if (e.import_name, e.args) == c):
                self.invalidated_callback(self)
                break

    async def resources_changed(self, sender: Any, params: List[ResourceChangedParams]) -> None:
        for p in params:
            if any(e for e in self._resources.values() if e.import_name == p.name):
                self.invalidated_callback(self)
                break

    async def get_diagnostisc(self) -> List[Diagnostic]:
        await self._ensure_initialized()

        await self._analyze()

        return self._diagnostics

    async def get_libraries(self) -> OrderedDict[str, LibraryEntry]:
        await self._ensure_initialized()

        return self._libraries

    async def get_resources(self) -> OrderedDict[str, ResourceEntry]:
        await self._ensure_initialized()

        return self._resources

    async def get_library_doc(self) -> LibraryDoc:
        if self._library_doc is None:
            self._library_doc = await self.imports_manager.get_libdoc_from_model(self.model, self.source)

        return self._library_doc

    async def _ensure_initialized(self) -> None:
        if not self._initialzed:
            self._initialzed = True

            await self._import_default_libraries()
            await self._import_imports(await self.get_imports(), str(Path(self.source).parent), add_diagnostics=True)

    async def _import_imports(self, imports: Iterable[Import], base_dir: str, *, add_diagnostics: bool = False) -> None:
        async def _import(value: Import) -> Optional[LibraryEntry]:
            result: Optional[LibraryEntry] = None
            try:
                if isinstance(value, LibraryImport):
                    if value.name is None:
                        raise NameSpaceError("Library setting requires value.")
                    result = await self._get_library_entry(value.name, value.args, value.alias, base_dir)
                    if add_diagnostics and result.library_doc.errors is None and len(result.library_doc.keywords) == 0:
                        self._diagnostics.append(
                            Diagnostic(
                                range=value.range(),
                                message=f"Imported library '{value.name}' contains no keywords.",
                                severity=DiagnosticSeverity.WARNING,
                                source=DIAGNOSTICS_SOURCE_NAME,
                            )
                        )
                elif isinstance(value, ResourceImport):
                    if value.name is None:
                        raise NameSpaceError("Resource setting requires value.")
                    result = await self._get_resource_entry(value.name, base_dir)
                elif isinstance(value, VariablesImport):
                    if value.name is None:
                        raise NameSpaceError("Variables setting requires value.")
                    result = await self._get_variables_entry(value.name, value.args, base_dir)
                else:
                    raise DiagnosticsException("Unknown import type.")

                if result.library_doc.errors and add_diagnostics:
                    if any(err.source for err in result.library_doc.errors):
                        self._diagnostics.append(
                            Diagnostic(
                                range=value.range(),
                                message="Import definition contains errors.",
                                severity=DiagnosticSeverity.ERROR,
                                source=DIAGNOSTICS_SOURCE_NAME,
                                related_information=[
                                    DiagnosticRelatedInformation(
                                        location=Location(
                                            uri=str(Uri.from_path(err.source)),
                                            range=Range(
                                                start=Position(
                                                    line=err.line_no - 1
                                                    if err.line_no is not None
                                                    else result.library_doc.line_no
                                                    if result.library_doc.line_no >= 0
                                                    else 0,
                                                    character=0,
                                                ),
                                                end=Position(
                                                    line=err.line_no - 1
                                                    if err.line_no is not None
                                                    else result.library_doc.line_no
                                                    if result.library_doc.line_no >= 0
                                                    else 0,
                                                    character=0,
                                                ),
                                            ),
                                        ),
                                        message=err.message,
                                    )
                                    for err in result.library_doc.errors
                                    if err.source is not None
                                ],
                            )
                        )
                    for err in filter(lambda e: e.source is None, result.library_doc.errors):
                        self._diagnostics.append(
                            Diagnostic(
                                range=value.range(),
                                message=err.message,
                                severity=DiagnosticSeverity.ERROR,
                                source=DIAGNOSTICS_SOURCE_NAME,
                                code=err.type_name,
                            )
                        )

            except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
                raise
            except BaseException as e:
                if add_diagnostics:
                    self._diagnostics.append(
                        Diagnostic(
                            range=value.range(),
                            message=str(e) or type(e).__name__,
                            severity=DiagnosticSeverity.ERROR,
                            source=DIAGNOSTICS_SOURCE_NAME,
                            code=type(e).__qualname__,
                        )
                    )
            return result

        for e in await asyncio.gather(*(_import(v) for v in imports)):
            if e is not None:
                if isinstance(e, ResourceEntry):
                    self._resources[e.alias or e.name or e.import_name] = e
                else:
                    self._libraries[e.alias or e.name or e.import_name] = e
                # TODO Variables

    async def get_imports(self) -> List[Import]:
        return await ImportVisitor().get(self.model)

    async def _import_default_libraries(self) -> None:
        async def _import_lib(library: str) -> Optional[LibraryEntry]:
            try:
                return await self._get_library_entry(
                    library, (), None, str(Path(self.source).parent), is_default_library=True
                )
            except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
                raise
            except BaseException as e:
                self._diagnostics.append(
                    Diagnostic(
                        range=Range.zero(),
                        message=f"Can't import default library '{library}': {str(e) or type(e).__name__}",
                        severity=DiagnosticSeverity.ERROR,
                        source="Robot",
                        code=type(e).__qualname__,
                    )
                )
                return None

        for e in await asyncio.gather(*(_import_lib(library) for library in DEFAULT_LIBRARIES)):
            if e is not None:
                self._libraries[e.alias or e.name or e.import_name] = e

    async def _get_library_entry(
        self, name: str, args: Tuple[Any, ...], alias: Optional[str], base_dir: str, *, is_default_library: bool = False
    ) -> LibraryEntry:
        library = await self.imports_manager.get_libdoc_for_library_import(
            name, args, base_dir=base_dir, sentinel=None if is_default_library else (self._sentinel() or self.model)
        )

        return LibraryEntry(name=library.name, import_name=name, library_doc=library, args=args, alias=alias)

    async def _get_resource_entry(self, name: str, base_dir: str) -> ResourceEntry:

        namespace = await self.imports_manager.get_namespace_for_resource_import(name, base_dir)

        await self._import_imports(
            await namespace.get_imports(), str(Path(namespace.source).parent), add_diagnostics=False
        )

        library_doc = await namespace.get_library_doc()

        return ResourceEntry(name=library_doc.name, import_name=name, library_doc=library_doc)

    async def _get_variables_entry(self, name: str, args: Tuple[Any, ...], base_dir: str) -> LibraryEntry:
        raise NotImplementedError("_import_variables")

    async def get_keywords(self) -> List[KeywordDoc]:
        await self._ensure_initialized()

        if self._keywords is None:

            self._keywords = [
                e
                async for e in async_chain(
                    *(e.library_doc.keywords.values() for e in self._libraries.values()),
                    *(e.library_doc.keywords.values() for e in self._resources.values()),
                    (await self.get_library_doc()).keywords.values()
                    if (await self.get_library_doc()) is not None
                    else [],
                )
            ]

        return self._keywords

    async def _analyze(self) -> None:
        if not self._analyzed:
            self._analyzed = True

            self._diagnostics += await Analyzer().get(self.model, self)

    async def find_keyword(self, name: Optional[str]) -> Optional[KeywordDoc]:
        await self._ensure_initialized()

        return await KeywordFinder(self).find_keyword(name)


class DiagnosticsEntry(NamedTuple):
    message: str
    severity: DiagnosticSeverity
    code: Optional[str] = None


class CancelSearch(Exception):
    pass


class KeywordFinder:
    def __init__(self, namespace: Namespace) -> None:
        super().__init__()
        self.namespace = namespace
        self.diagnostics: List[DiagnosticsEntry] = []

    async def find_keyword(self, name: Optional[str]) -> Optional[KeywordDoc]:
        try:
            result = await self._find_keyword(name)
            if result is None:
                self.diagnostics.append(
                    DiagnosticsEntry(
                        f"No keyword with name {repr(name)} found.", DiagnosticSeverity.ERROR, "KeywordError"
                    )
                )

            return result
        except CancelSearch:
            return None

    async def _find_keyword(self, name: Optional[str]) -> Optional[KeywordDoc]:
        if not name:
            self.diagnostics.append(
                DiagnosticsEntry("Keyword name cannot be empty.", DiagnosticSeverity.ERROR, "KeywordError")
            )
            raise CancelSearch()
        if not isinstance(name, str):
            self.diagnostics.append(
                DiagnosticsEntry("Keyword name must be a string.", DiagnosticSeverity.ERROR, "KeywordError")
            )
            raise CancelSearch()

        result = await self._get_keyword_from_self(name)
        if not result and "." in name:
            result = await self._get_explicit_keyword(name)

        if not result:
            result = await self._get_implicit_keyword(name)

        if not result:
            result = await self._get_bdd_style_keyword(name)

        return result

    async def _get_keyword_from_self(self, name: str) -> Optional[KeywordDoc]:

        return (await self.namespace.get_library_doc()).keywords.get(name, None)

    async def _yield_owner_and_kw_names(self, full_name: str) -> AsyncIterator[Tuple[str, ...]]:
        tokens = full_name.split(".")
        for i in range(1, len(tokens)):
            yield ".".join(tokens[:i]), ".".join(tokens[i:])

    async def _get_explicit_keyword(self, name: str) -> Optional[KeywordDoc]:
        found: List[Tuple[LibraryEntry, KeywordDoc]] = []
        async for owner_name, kw_name in self._yield_owner_and_kw_names(name):
            found.extend(await self._find_keywords(owner_name, kw_name))
        if len(found) > 1:
            self.diagnostics.append(
                DiagnosticsEntry(
                    self._create_multiple_keywords_found_message(name, found, implicit=False),
                    DiagnosticSeverity.ERROR,
                    "KeywordError",
                )
            )
            raise CancelSearch()

        return found[0][1] if found else None

    async def _find_keywords(self, owner_name: str, name: str) -> Sequence[Tuple[LibraryEntry, KeywordDoc]]:
        from robot.utils.match import eq

        return [
            (v, v.library_doc.keywords[name])
            async for k, v in async_chain(self.namespace._libraries.items(), self.namespace._resources.items())
            if eq(k, owner_name) and name in v.library_doc.keywords
        ]

    def _create_multiple_keywords_found_message(
        self, name: str, found: Sequence[Tuple[LibraryEntry, KeywordDoc]], implicit: bool = True
    ) -> str:

        error = "Multiple keywords with name '%s' found" % name
        if implicit:
            error += ". Give the full name of the keyword you want to use"
        names = sorted(f"{e[0].alias or e[0].name}.{e[1].name}" for e in found)
        return "\n    ".join([error + ":"] + names)

    async def _get_implicit_keyword(self, name: str) -> Optional[KeywordDoc]:
        result = await self._get_keyword_from_resource_files(name)
        if not result:
            result = await self._get_keyword_from_libraries(name)
        return result

    async def _get_keyword_from_resource_files(self, name: str) -> Optional[KeywordDoc]:
        found: List[Tuple[LibraryEntry, KeywordDoc]] = [
            (v, v.library_doc.keywords[name])
            async for v in async_chain(self.namespace._resources.values())
            if name in v.library_doc.keywords
        ]
        if not found:
            return None
        if len(found) > 1:
            found = await self._get_keyword_based_on_search_order(found)
        if len(found) == 1:
            return found[0][1]

        self.diagnostics.append(
            DiagnosticsEntry(
                self._create_multiple_keywords_found_message(name, found),
                DiagnosticSeverity.ERROR,
                "KeywordError",
            )
        )
        raise CancelSearch()

    async def _get_keyword_based_on_search_order(
        self, entries: List[Tuple[LibraryEntry, KeywordDoc]]
    ) -> List[Tuple[LibraryEntry, KeywordDoc]]:
        from robot.utils.match import eq

        for libname in self.namespace.search_order:
            for e in entries:
                if eq(libname, e[0].alias or e[0].name):
                    return [e]

        return entries

    async def _get_keyword_from_libraries(self, name: str) -> Optional[KeywordDoc]:
        found = [
            (v, v.library_doc.keywords[name])
            async for v in async_chain(self.namespace._libraries.values())
            if name in v.library_doc.keywords
        ]
        if not found:
            return None
        if len(found) > 1:
            found = await self._get_keyword_based_on_search_order(found)
        if len(found) == 2:
            found = await self._filter_stdlib_runner(*found)
        if len(found) == 1:
            return found[0][1]

        self.diagnostics.append(
            DiagnosticsEntry(
                self._create_multiple_keywords_found_message(name, found),
                DiagnosticSeverity.ERROR,
                "KeywordError",
            )
        )
        raise CancelSearch()

    async def _filter_stdlib_runner(
        self, entry1: Tuple[LibraryEntry, KeywordDoc], entry2: Tuple[LibraryEntry, KeywordDoc]
    ) -> List[Tuple[LibraryEntry, KeywordDoc]]:
        from robot.libraries import STDLIBS

        stdlibs_without_remote = STDLIBS - {"Remote"}
        if entry1[0].name in stdlibs_without_remote:
            standard, custom = entry1, entry2
        elif entry2[0].name in stdlibs_without_remote:
            standard, custom = entry2, entry1
        else:
            return [entry1, entry2]

        self.diagnostics.append(
            DiagnosticsEntry(
                self._create_custom_and_standard_keyword_conflict_warning_message(custom, standard),
                DiagnosticSeverity.WARNING,
                "KeywordError",
            )
        )

        return [custom]

    def _create_custom_and_standard_keyword_conflict_warning_message(
        self, custom: Tuple[LibraryEntry, KeywordDoc], standard: Tuple[LibraryEntry, KeywordDoc]
    ) -> str:
        custom_with_name = standard_with_name = ""
        if custom[0].alias is not None:
            custom_with_name = " imported as '%s'" % custom[0].alias
        if standard[0].alias is not None:
            standard_with_name = " imported as '%s'" % standard[0].alias
        return (
            f"Keyword '{standard[1].name}' found both from a custom test library "
            f"'{custom[0].name}'{custom_with_name} and a standard library '{standard[1].name}'{standard_with_name}. "
            f"The custom keyword is used. To select explicitly, and to get "
            f"rid of this warning, use either '{custom[0].alias or custom[0].name}.{custom[1].name}' "
            f"or '{standard[0].alias or standard[0].name}.{standard[1].name}'."
        )

    async def _get_bdd_style_keyword(self, name: str) -> Optional[KeywordDoc]:
        lower = name.lower()
        for prefix in ["given ", "when ", "then ", "and ", "but "]:
            if lower.startswith(prefix):
                return await self._find_keyword(name[len(prefix) :])  # noqa: E203

        return None
