from __future__ import annotations

import ast
import asyncio
from typing import TYPE_CHECKING, Any, List, Optional

from robotcode.core.async_tools import check_canceled, create_sub_task, threaded
from robotcode.core.logging import LoggingDescriptor
from robotcode.core.lsp.types import Diagnostic, DiagnosticSeverity, DiagnosticTag, Position, Range
from robotcode.core.uri import Uri

from ...common.decorators import language_id
from ...common.parts.diagnostics import DiagnosticsResult
from ...common.text_document import TextDocument
from ..configuration import AnalysisConfig
from ..diagnostics.entities import ArgumentDefinition
from ..diagnostics.namespace import Namespace
from ..utils.ast_utils import (
    HeaderAndBodyBlock,
    Token,
    range_from_node,
    range_from_token,
)

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .protocol_part import RobotLanguageServerProtocolPart


class RobotDiagnosticsProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        self.source_name = "robotcode.diagnostics"

        parent.diagnostics.collect.add(self.collect_token_errors)
        parent.diagnostics.collect.add(self.collect_model_errors)

        parent.diagnostics.collect.add(self.collect_namespace_diagnostics)

        parent.diagnostics.collect.add(self.collect_unused_keyword_references)
        parent.diagnostics.collect.add(self.collect_unused_variable_references)

        parent.documents_cache.namespace_invalidated.add(self.namespace_invalidated)

    async def namespace_invalidated_task(self, namespace: Namespace) -> None:
        if namespace.document is not None:
            refresh = namespace.document.opened_in_editor

            await self.parent.diagnostics.force_refresh_document(namespace.document, False)

            if await namespace.is_initialized():
                resources = (await namespace.get_resources()).values()
                for r in resources:
                    if r.library_doc.source:
                        doc = await self.parent.documents.get(Uri.from_path(r.library_doc.source).normalized())
                        if doc is not None:
                            refresh |= doc.opened_in_editor
                            await self.parent.diagnostics.force_refresh_document(doc, False)

            if refresh:
                await self.parent.diagnostics.refresh()

    @language_id("robotframework")
    @_logger.call
    async def namespace_invalidated(self, sender: Any, namespace: Namespace) -> None:
        create_sub_task(self.namespace_invalidated_task(namespace), loop=self.parent.diagnostics.diagnostics_loop)

    @language_id("robotframework")
    @threaded()
    @_logger.call
    async def collect_namespace_diagnostics(self, sender: Any, document: TextDocument) -> DiagnosticsResult:
        return await document.get_cache(self._collect_namespace_diagnostics)

    async def _collect_namespace_diagnostics(self, document: TextDocument) -> DiagnosticsResult:
        try:
            namespace = await self.parent.documents_cache.get_namespace(document)

            return DiagnosticsResult(self.collect_namespace_diagnostics, await namespace.get_diagnostisc())
        except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            self._logger.exception(e)
            return DiagnosticsResult(
                self.collect_namespace_diagnostics,
                [
                    Diagnostic(
                        range=Range(
                            start=Position(
                                line=0,
                                character=0,
                            ),
                            end=Position(
                                line=len(document.get_lines()),
                                character=len((document.get_lines())[-1] or ""),
                            ),
                        ),
                        message=f"Fatal: can't get namespace diagnostics '{e}' ({type(e).__qualname__})",
                        severity=DiagnosticSeverity.ERROR,
                        source=self.source_name,
                        code=type(e).__qualname__,
                    )
                ],
            )

    def _create_error_from_node(
        self, node: ast.AST, msg: str, source: Optional[str] = None, only_start: bool = True
    ) -> Diagnostic:
        from robot.parsing.model.statements import Statement

        if isinstance(node, HeaderAndBodyBlock):
            if node.header is not None:
                node = node.header
            elif node.body:
                stmt = next((n for n in node.body if isinstance(n, Statement)), None)
                if stmt is not None:
                    node = stmt

        return Diagnostic(
            range=range_from_node(node, True, only_start),
            message=msg,
            severity=DiagnosticSeverity.ERROR,
            source=source if source is not None else self.source_name,
            code="ModelError",
        )

    def _create_error_from_token(self, token: Token, source: Optional[str] = None) -> Diagnostic:
        return Diagnostic(
            range=range_from_token(token),
            message=token.error if token.error is not None else "(No Message).",
            severity=DiagnosticSeverity.ERROR,
            source=source if source is not None else self.source_name,
            code="TokenError",
        )

    @language_id("robotframework")
    @threaded()
    @_logger.call
    async def collect_token_errors(self, sender: Any, document: TextDocument) -> DiagnosticsResult:
        return await document.get_cache(self._collect_token_errors)

    async def _collect_token_errors(self, document: TextDocument) -> DiagnosticsResult:
        from robot.errors import VariableError
        from robot.parsing.lexer.tokens import Token

        result: List[Diagnostic] = []
        try:
            for token in await self.parent.documents_cache.get_tokens(document):
                await check_canceled()

                if token.type in [Token.ERROR, Token.FATAL_ERROR] and not Namespace.should_ignore(
                    document, range_from_token(token)
                ):
                    result.append(self._create_error_from_token(token))

                try:
                    for variable_token in token.tokenize_variables():
                        await check_canceled()
                        if variable_token == token:
                            break

                        if variable_token.type in [
                            Token.ERROR,
                            Token.FATAL_ERROR,
                        ] and not Namespace.should_ignore(document, range_from_token(variable_token)):
                            result.append(self._create_error_from_token(variable_token))

                except VariableError as e:
                    if not Namespace.should_ignore(document, range_from_token(token)):
                        result.append(
                            Diagnostic(
                                range=range_from_token(token),
                                message=str(e),
                                severity=DiagnosticSeverity.ERROR,
                                source=self.source_name,
                                code=type(e).__qualname__,
                            )
                        )
        except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            return DiagnosticsResult(
                self.collect_token_errors,
                [
                    Diagnostic(
                        range=Range(
                            start=Position(
                                line=0,
                                character=0,
                            ),
                            end=Position(
                                line=len(document.get_lines()),
                                character=len((document.get_lines())[-1] or ""),
                            ),
                        ),
                        message=f"Fatal: can't get token diagnostics '{e}' ({type(e).__qualname__})",
                        severity=DiagnosticSeverity.ERROR,
                        source=self.source_name,
                        code=type(e).__qualname__,
                    )
                ],
            )

        return DiagnosticsResult(self.collect_token_errors, result)

    @language_id("robotframework")
    @threaded()
    @_logger.call
    async def collect_model_errors(self, sender: Any, document: TextDocument) -> DiagnosticsResult:
        return await document.get_cache(self._collect_model_errors)

    async def _collect_model_errors(self, document: TextDocument) -> DiagnosticsResult:
        from robotcode.language_server.robotframework.utils.ast_utils import HasError, HasErrors
        from robotcode.language_server.robotframework.utils.async_ast import iter_nodes

        try:
            model = await self.parent.documents_cache.get_model(document, True)

            result: List[Diagnostic] = []
            async for node in iter_nodes(model):
                error = node.error if isinstance(node, HasError) else None
                if error is not None and not Namespace.should_ignore(document, range_from_node(node)):
                    result.append(self._create_error_from_node(node, error))
                errors = node.errors if isinstance(node, HasErrors) else None
                if errors is not None:
                    for e in errors:
                        if not Namespace.should_ignore(document, range_from_node(node)):
                            result.append(self._create_error_from_node(node, e))

            return DiagnosticsResult(self.collect_model_errors, result)

        except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            return DiagnosticsResult(
                self.collect_model_errors,
                [
                    Diagnostic(
                        range=Range(
                            start=Position(
                                line=0,
                                character=0,
                            ),
                            end=Position(
                                line=len(document.get_lines()),
                                character=len((document.get_lines())[-1] or ""),
                            ),
                        ),
                        message=f"Fatal: can't get model diagnostics '{e}' ({type(e).__qualname__})",
                        severity=DiagnosticSeverity.ERROR,
                        source=self.source_name,
                        code=type(e).__qualname__,
                    )
                ],
            )

    @language_id("robotframework")
    @threaded()
    @_logger.call
    async def collect_unused_keyword_references(self, sender: Any, document: TextDocument) -> DiagnosticsResult:
        if not self.parent.diagnostics.workspace_loaded_event.is_set():
            return DiagnosticsResult(self.collect_unused_keyword_references, None)

        config = await self.parent.workspace.get_configuration(AnalysisConfig, document.uri)

        if not config.find_unused_references:
            return DiagnosticsResult(self.collect_unused_keyword_references, [])

        return await self._collect_unused_keyword_references(document)

    async def _collect_unused_keyword_references(self, document: TextDocument) -> DiagnosticsResult:
        try:
            namespace = await self.parent.documents_cache.get_namespace(document)

            result: List[Diagnostic] = []
            for kw in (await namespace.get_library_doc()).keywords.values():
                references = await self.parent.robot_references.find_keyword_references(document, kw, False, True)
                if not references and not Namespace.should_ignore(document, kw.name_range):
                    result.append(
                        Diagnostic(
                            range=kw.name_range,
                            message=f"Keyword '{kw.name}' is not used.",
                            severity=DiagnosticSeverity.WARNING,
                            source=self.source_name,
                            code="KeywordNotUsed",
                            tags=[DiagnosticTag.UNNECESSARY],
                        )
                    )

            return DiagnosticsResult(self.collect_unused_keyword_references, result)
        except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            return DiagnosticsResult(
                self.collect_unused_keyword_references,
                [
                    Diagnostic(
                        range=Range(
                            start=Position(
                                line=0,
                                character=0,
                            ),
                            end=Position(
                                line=len(document.get_lines()),
                                character=len((document.get_lines())[-1] or ""),
                            ),
                        ),
                        message=f"Fatal: can't collect unused keyword references '{e}' ({type(e).__qualname__})",
                        severity=DiagnosticSeverity.ERROR,
                        source=self.source_name,
                        code=type(e).__qualname__,
                    )
                ],
            )

    @language_id("robotframework")
    @threaded()
    @_logger.call
    async def collect_unused_variable_references(self, sender: Any, document: TextDocument) -> DiagnosticsResult:
        if not self.parent.diagnostics.workspace_loaded_event.is_set():
            return DiagnosticsResult(self.collect_unused_variable_references, None)

        config = await self.parent.workspace.get_configuration(AnalysisConfig, document.uri)

        if not config.find_unused_references:
            return DiagnosticsResult(self.collect_unused_variable_references, [])

        return await self._collect_unused_variable_references(document)

    async def _collect_unused_variable_references(self, document: TextDocument) -> DiagnosticsResult:
        try:
            namespace = await self.parent.documents_cache.get_namespace(document)

            result: List[Diagnostic] = []

            for var in (await namespace.get_variable_references()).keys():
                references = await self.parent.robot_references.find_variable_references(document, var, False, True)
                if not references and not Namespace.should_ignore(document, var.name_range):
                    result.append(
                        Diagnostic(
                            range=var.name_range,
                            message=f"{'Argument' if isinstance(var, ArgumentDefinition) else 'Variable'}"
                            f" '{var.name}' is not used.",
                            severity=DiagnosticSeverity.WARNING,
                            source=self.source_name,
                            code="VariableNotUsed",
                            tags=[DiagnosticTag.UNNECESSARY],
                        )
                    )

            return DiagnosticsResult(self.collect_unused_variable_references, result)
        except (asyncio.CancelledError, SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            return DiagnosticsResult(
                self.collect_unused_variable_references,
                [
                    Diagnostic(
                        range=Range(
                            start=Position(
                                line=0,
                                character=0,
                            ),
                            end=Position(
                                line=len(document.get_lines()),
                                character=len((document.get_lines())[-1] or ""),
                            ),
                        ),
                        message=f"Fatal: can't collect unused variable references '{e}' ({type(e).__qualname__})",
                        severity=DiagnosticSeverity.ERROR,
                        source=self.source_name,
                        code=type(e).__qualname__,
                    )
                ],
            )
