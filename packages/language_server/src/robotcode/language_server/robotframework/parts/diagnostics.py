import ast
import threading
from concurrent.futures import CancelledError
from typing import TYPE_CHECKING, Any, List, Optional

from robot.parsing.lexer.tokens import Token

from robotcode.core.concurrent import check_current_task_canceled
from robotcode.core.language import language_id
from robotcode.core.lsp.types import (
    Diagnostic,
    DiagnosticSeverity,
    DiagnosticTag,
    Position,
    Range,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.language_server.robotframework.configuration import AnalysisConfig
from robotcode.robot.diagnostics.entities import (
    ArgumentDefinition,
    EnvironmentVariableDefinition,
    GlobalVariableDefinition,
    LibraryArgumentDefinition,
)
from robotcode.robot.diagnostics.namespace import Namespace
from robotcode.robot.utils.ast import (
    iter_nodes,
    range_from_node,
    range_from_token,
)
from robotcode.robot.utils.stubs import HasError, HasErrors, HeaderAndBodyBlock

from ...common.parts.diagnostics import DiagnosticsResult

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .protocol_part import RobotLanguageServerProtocolPart


class RobotDiagnosticsProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

        self.source_name = "robotcode.diagnostics"

        self.parent.on_initialized.add(self._on_initialized)

        self.parent.diagnostics.collect.add(self.collect_token_errors)
        self.parent.diagnostics.collect.add(self.collect_model_errors)

        self.parent.diagnostics.collect.add(self.collect_namespace_diagnostics)

        self.parent.diagnostics.collect.add(self.collect_unused_keyword_references)
        self.parent.diagnostics.collect.add(self.collect_unused_variable_references)

        self._collect_unused_references_event = threading.Event()

        self.parent.diagnostics.on_workspace_diagnostics_analyze.add(self._on_workspace_diagnostics_analyze)
        self.parent.diagnostics.on_workspace_diagnostics_collect.add(self._on_workspace_diagnostics_collect)

    def _on_initialized(self, sender: Any) -> None:
        self.parent.diagnostics.analyze.add(self.analyze)

        self.parent.documents_cache.namespace_invalidated.add(self.namespace_invalidated)

    def _on_workspace_diagnostics_analyze(self, sender: Any) -> None:
        self._collect_unused_references_event.clear()

    def _on_workspace_diagnostics_collect(self, sender: Any) -> None:
        self._collect_unused_references_event.set()

    @language_id("robotframework")
    def analyze(self, sender: Any, document: TextDocument) -> None:
        self.parent.documents_cache.get_namespace(document).analyze()

    @language_id("robotframework")
    def namespace_invalidated(self, sender: Any, namespace: Namespace) -> None:
        self._collect_unused_references_event.clear()

        self._namespace_invalidated(namespace)

        self.parent.diagnostics.break_workspace_diagnostics_loop()

    def _namespace_invalidated(self, namespace: Namespace) -> None:
        if namespace.document is not None:
            refresh = namespace.document.opened_in_editor

            self.parent.diagnostics.force_refresh_document(namespace.document, False)

            if namespace.is_initialized():
                resources = namespace.get_resources().values()
                for r in resources:
                    if r.library_doc.source:
                        doc = self.parent.documents.get(Uri.from_path(r.library_doc.source).normalized())
                        if doc is not None:
                            refresh |= doc.opened_in_editor
                            self.parent.diagnostics.force_refresh_document(doc, False)

            if refresh:
                self.parent.diagnostics.refresh()

    @language_id("robotframework")
    def collect_namespace_diagnostics(self, sender: Any, document: TextDocument) -> DiagnosticsResult:
        return document.get_cache(self._collect_namespace_diagnostics)

    def _collect_namespace_diagnostics(self, document: TextDocument) -> DiagnosticsResult:
        try:
            namespace = self.parent.documents_cache.get_namespace(document)

            return DiagnosticsResult(self.collect_namespace_diagnostics, namespace.get_diagnostics())
        except (CancelledError, SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            self._logger.exception(e)
            return DiagnosticsResult(
                self.collect_namespace_diagnostics,
                [
                    Diagnostic(
                        range=Range(
                            start=Position(line=0, character=0),
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
        self,
        node: ast.AST,
        msg: str,
        source: Optional[str] = None,
        only_start: bool = True,
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
    @_logger.call
    def collect_token_errors(self, sender: Any, document: TextDocument) -> DiagnosticsResult:
        return document.get_cache(self._collect_token_errors)

    def _collect_token_errors(self, document: TextDocument) -> DiagnosticsResult:
        from robot.errors import VariableError
        from robot.parsing.lexer.tokens import Token

        result: List[Diagnostic] = []
        try:
            for token in self.parent.documents_cache.get_tokens(document):
                check_current_task_canceled()

                if token.type in [
                    Token.ERROR,
                    Token.FATAL_ERROR,
                ] and not Namespace.should_ignore(document, range_from_token(token)):
                    result.append(self._create_error_from_token(token))

                try:
                    for variable_token in token.tokenize_variables():
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
        except (CancelledError, SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            return DiagnosticsResult(
                self.collect_token_errors,
                [
                    Diagnostic(
                        range=Range(
                            start=Position(line=0, character=0),
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
    @_logger.call
    def collect_model_errors(self, sender: Any, document: TextDocument) -> DiagnosticsResult:
        return document.get_cache(self._collect_model_errors)

    def _collect_model_errors(self, document: TextDocument) -> DiagnosticsResult:
        try:
            model = self.parent.documents_cache.get_model(document, True)

            result: List[Diagnostic] = []
            for node in iter_nodes(model):
                check_current_task_canceled()

                error = node.error if isinstance(node, HasError) else None
                if error is not None and not Namespace.should_ignore(document, range_from_node(node)):
                    result.append(self._create_error_from_node(node, error))
                errors = node.errors if isinstance(node, HasErrors) else None
                if errors is not None:
                    for e in errors:
                        if not Namespace.should_ignore(document, range_from_node(node)):
                            result.append(self._create_error_from_node(node, e))

            return DiagnosticsResult(self.collect_model_errors, result)

        except (CancelledError, SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            return DiagnosticsResult(
                self.collect_model_errors,
                [
                    Diagnostic(
                        range=Range(
                            start=Position(line=0, character=0),
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
    @_logger.call
    def collect_unused_keyword_references(self, sender: Any, document: TextDocument) -> DiagnosticsResult:
        config = self.parent.workspace.get_configuration(AnalysisConfig, document.uri)

        if not config.find_unused_references:
            return DiagnosticsResult(self.collect_unused_keyword_references, [])

        if not self._collect_unused_references_event.is_set():
            return DiagnosticsResult(self.collect_unused_keyword_references, None, True)

        return self._collect_unused_keyword_references(document)

    def _collect_unused_keyword_references(self, document: TextDocument) -> DiagnosticsResult:
        try:
            namespace = self.parent.documents_cache.get_namespace(document)

            result: List[Diagnostic] = []
            for kw in (namespace.get_library_doc()).keywords.values():
                check_current_task_canceled()

                references = self.parent.robot_references.find_keyword_references(document, kw, False, True)
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
        except (CancelledError, SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            return DiagnosticsResult(
                self.collect_unused_keyword_references,
                [
                    Diagnostic(
                        range=Range(
                            start=Position(line=0, character=0),
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
    @_logger.call
    def collect_unused_variable_references(self, sender: Any, document: TextDocument) -> DiagnosticsResult:
        config = self.parent.workspace.get_configuration(AnalysisConfig, document.uri)

        if not config.find_unused_references:
            return DiagnosticsResult(self.collect_unused_variable_references, [])

        if not self._collect_unused_references_event.is_set():
            return DiagnosticsResult(self.collect_unused_variable_references, None, True)

        return self._collect_unused_variable_references(document)

    def _collect_unused_variable_references(self, document: TextDocument) -> DiagnosticsResult:
        try:
            namespace = self.parent.documents_cache.get_namespace(document)

            result: List[Diagnostic] = []

            for var in (namespace.get_variable_references()).keys():
                check_current_task_canceled()

                if isinstance(
                    var, (LibraryArgumentDefinition, EnvironmentVariableDefinition, GlobalVariableDefinition)
                ):
                    continue

                references = self.parent.robot_references.find_variable_references(document, var, False, True)
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
        except (CancelledError, SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            return DiagnosticsResult(
                self.collect_unused_variable_references,
                [
                    Diagnostic(
                        range=Range(
                            start=Position(line=0, character=0),
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
