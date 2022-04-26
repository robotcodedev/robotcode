from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any, List, Optional, cast

from ....utils.async_tools import threaded
from ....utils.logging import LoggingDescriptor
from ...common.decorators import language_id
from ...common.lsp_types import CodeLens, Command
from ...common.text_document import TextDocument
from ..configuration import AnalysisConfig
from ..utils.ast_utils import range_from_token
from .model_helper import ModelHelperMixin

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .protocol_part import RobotLanguageServerProtocolPart


class RobotCodeLensProtocolPart(RobotLanguageServerProtocolPart, ModelHelperMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.code_lens.collect.add(self.collect)
        parent.code_lens.resolve.add(self.resolve)

    @language_id("robotframework")
    @threaded()
    async def collect(self, sender: Any, document: TextDocument) -> Optional[List[CodeLens]]:

        from ..utils.async_ast import AsyncVisitor

        class Visitor(AsyncVisitor):
            def __init__(self, parent: RobotCodeLensProtocolPart) -> None:
                super().__init__()
                self.parent = parent

                self.result: List[CodeLens] = []

            async def visit(self, node: ast.AST) -> None:
                await super().visit(node)

            @classmethod
            async def find_from(cls, model: ast.AST, parent: RobotCodeLensProtocolPart) -> Optional[List[CodeLens]]:

                finder = cls(parent)

                await finder.visit(model)

                return finder.result if finder.result else None

            async def visit_Section(self, node: ast.AST) -> None:  # noqa: N802
                from robot.parsing.model.blocks import KeywordSection

                if isinstance(node, KeywordSection):
                    await self.generic_visit(node)

            async def visit_KeywordName(self, node: ast.AST) -> None:  # noqa: N802
                from robot.parsing.lexer.tokens import Token as RobotToken
                from robot.parsing.model.statements import KeywordName

                kw_node = cast(KeywordName, node)
                name_token = cast(RobotToken, kw_node.get_token(RobotToken.KEYWORD_NAME))
                if not name_token:
                    return None

                self.result.append(
                    CodeLens(
                        range_from_token(name_token),
                        command=None,
                        data={"uri": str(document.uri), "name": name_token.value, "line": name_token.lineno},
                    )
                )

        if not (await self.parent.workspace.get_configuration(AnalysisConfig, document.uri)).references_code_lens:
            return None

        return await Visitor.find_from(await self.parent.documents_cache.get_model(document), self)

    @language_id("robotframework")
    @threaded()
    async def resolve(self, sender: Any, code_lens: CodeLens) -> Optional[CodeLens]:
        if code_lens.data is None:
            return code_lens

        document = await self.parent.documents.get(code_lens.data.get("uri", None))
        if document is None:
            return None

        if not (await self.parent.workspace.get_configuration(AnalysisConfig, document.uri)).references_code_lens:
            return None

        namespace = await self.parent.documents_cache.get_namespace(document)

        if namespace is None:
            return None

        name = code_lens.data["name"]
        line = code_lens.data["line"]

        if self.parent.robot_workspace.workspace_loaded:
            kw_doc = await self.get_keyword_definition_at_line(namespace, name, line)

            if kw_doc is not None and not kw_doc.is_error_handler:
                references = await self.parent.robot_references.find_keyword_references(
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
