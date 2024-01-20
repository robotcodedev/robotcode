import ast
from typing import TYPE_CHECKING, Any, List, Optional, Set, Tuple, cast

from robotcode.core.concurrent import run_as_task
from robotcode.core.language import language_id
from robotcode.core.lsp.types import CodeLens, Command
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.language_server.robotframework.configuration import AnalysisConfig
from robotcode.robot.diagnostics.library_doc import KeywordDoc
from robotcode.robot.diagnostics.model_helper import ModelHelper
from robotcode.robot.utils.ast import range_from_token
from robotcode.robot.utils.visitor import Visitor

from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


class RobotCodeLensProtocolPart(RobotLanguageServerProtocolPart, ModelHelper):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

        parent.code_lens.collect.add(self.collect)
        parent.code_lens.resolve.add(self.resolve)

        self._running_task: Set[Tuple[TextDocument, KeywordDoc]] = set()
        self._enabled: Optional[bool] = None

    @property
    def enabled(self) -> bool:
        if self._enabled is None:
            self._enabled = any(
                self.parent.workspace.get_configuration(AnalysisConfig, f.uri).references_code_lens
                for f in self.parent.workspace.workspace_folders
            )
            if self._enabled:
                self.parent.diagnostics.on_workspace_diagnostics_collect.add(self.codelens_refresh)
                self.parent.robot_references.cache_cleared.add(self.codelens_refresh)

        return self._enabled

    def codelens_refresh(self, sender: Any) -> None:
        if self.enabled:
            self.parent.code_lens.refresh()

    @language_id("robotframework")
    def collect(self, sender: Any, document: TextDocument) -> Optional[List[CodeLens]]:
        if self.enabled and self.parent.workspace.get_configuration(AnalysisConfig, document.uri).references_code_lens:
            return _Visitor.find_from(self.parent.documents_cache.get_model(document), self, document)
        return None

    @language_id("robotframework")
    def resolve(self, sender: Any, code_lens: CodeLens) -> Optional[CodeLens]:
        if not self.enabled:
            return None

        if code_lens.data is None:
            return code_lens

        document = self.parent.documents.get(code_lens.data.get("uri", None))
        if document is None:
            return None

        if not (self.parent.workspace.get_configuration(AnalysisConfig, document.uri)).references_code_lens:
            return None

        namespace = self.parent.documents_cache.get_namespace(document)

        name = code_lens.data["name"]
        line = code_lens.data["line"]

        if self.parent.diagnostics.workspace_loaded_event.is_set():
            kw_doc = self.get_keyword_definition_at_line(namespace.get_library_doc(), name, line)

            if kw_doc is not None and not kw_doc.is_error_handler:
                if not self.parent.robot_references.has_cached_keyword_references(
                    document, kw_doc, include_declaration=False
                ):
                    code_lens.command = Command(
                        "...",
                        "editor.action.showReferences",
                        [str(document.uri), code_lens.range.start, []],
                    )

                    def find_refs() -> None:
                        if document is None or kw_doc is None:
                            return  # type: ignore[unreachable]

                        self.parent.robot_references.find_keyword_references(
                            document, kw_doc, include_declaration=False
                        )

                        self.parent.code_lens.refresh()

                    key = (document, kw_doc)
                    if key not in self._running_task:
                        task = run_as_task(find_refs)

                        def done(task: Any) -> None:
                            if key in self._running_task:
                                self._running_task.discard(key)

                        task.add_done_callback(done)

                        self._running_task.add(key)
                else:
                    references = self.parent.robot_references.find_keyword_references(
                        document, kw_doc, include_declaration=False
                    )
                    code_lens.command = Command(
                        f"{len(references)} references",
                        "editor.action.showReferences",
                        [str(document.uri), code_lens.range.start, references],
                    )
            else:
                code_lens.command = Command(
                    "0 references",
                    "editor.action.showReferences",
                    [str(document.uri), code_lens.range.start, []],
                )
        else:
            code_lens.command = Command(
                "...",
                "editor.action.showReferences",
                [str(document.uri), code_lens.range.start, []],
            )

        return code_lens


class _Visitor(Visitor):
    def __init__(self, parent: RobotCodeLensProtocolPart, document: TextDocument) -> None:
        super().__init__()
        self.parent = parent
        self.document = document

        self.result: List[CodeLens] = []

    def visit(self, node: ast.AST) -> None:
        super().visit(node)

    @classmethod
    def find_from(
        cls,
        model: ast.AST,
        parent: RobotCodeLensProtocolPart,
        document: TextDocument,
    ) -> Optional[List[CodeLens]]:
        finder = cls(parent, document)

        finder.visit(model)

        return finder.result if finder.result else None

    def visit_Section(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.model.blocks import KeywordSection

        if isinstance(node, KeywordSection):
            self.generic_visit(node)

    def visit_KeywordName(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import KeywordName

        kw_node = cast(KeywordName, node)
        name_token = cast(RobotToken, kw_node.get_token(RobotToken.KEYWORD_NAME))
        if not name_token:
            return

        self.result.append(
            CodeLens(
                range_from_token(name_token),
                command=None,
                data={
                    "uri": str(self.document.uri),
                    "name": name_token.value,
                    "line": name_token.lineno,
                },
            )
        )
