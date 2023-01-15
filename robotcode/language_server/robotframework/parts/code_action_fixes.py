from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any, List, Optional, Union, cast

from ....utils.logging import LoggingDescriptor
from ...common.decorators import code_action_kinds, command, language_id
from ...common.lsp_types import (
    AnnotatedTextEdit,
    ChangeAnnotation,
    CodeAction,
    CodeActionContext,
    CodeActionKinds,
    CodeActionTriggerKind,
    Command,
    DocumentUri,
    OptionalVersionedTextDocumentIdentifier,
    Position,
    Range,
    TextDocumentEdit,
    WorkspaceEdit,
)
from ...common.text_document import TextDocument
from ..utils.ast_utils import Token, get_node_at_position, range_from_node
from ..utils.async_ast import AsyncVisitor
from .model_helper import ModelHelperMixin

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol  # pragma: no cover

from string import Template

from .protocol_part import RobotLanguageServerProtocolPart

CODEACTIONKINDS_QUICKFIX_CREATEKEYWORD = f"{CodeActionKinds.QUICKFIX}.createKeyword"


KEYWORD_WITH_ARGS_TEMPLATE = Template(
    """\n
${name}
    [Arguments]    ${args}
    Fail    Not implemented
"""
)

KEYWORD_TEMPLATE = Template(
    """\n
${name}
    Fail    Not implemented
"""
)


class FindKeywordSectionVisitor(AsyncVisitor):
    def __init__(self) -> None:
        self.keyword_sections: List[ast.AST] = []

    async def visit_KeywordSection(self, node: ast.AST) -> None:  # noqa: N802
        self.keyword_sections.append(node)


async def find_keyword_sections(node: ast.AST) -> Optional[List[ast.AST]]:
    visitor = FindKeywordSectionVisitor()
    await visitor.visit(node)
    return visitor.keyword_sections if visitor.keyword_sections else None


class RobotCodeActionFixesProtocolPart(RobotLanguageServerProtocolPart, ModelHelperMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.code_action.collect.add(self.collect)

        self.parent.commands.register_all(self)

    @language_id("robotframework")
    @code_action_kinds(
        [
            CODEACTIONKINDS_QUICKFIX_CREATEKEYWORD,
        ]
    )
    @_logger.call
    async def collect(
        self, sender: Any, document: TextDocument, range: Range, context: CodeActionContext
    ) -> Optional[List[Union[Command, CodeAction]]]:

        kw_not_found_in_diagnostics = next((d for d in context.diagnostics if d.code == "KeywordNotFoundError"), None)

        if kw_not_found_in_diagnostics and (
            (context.only and CodeActionKinds.QUICKFIX in context.only)
            or context.trigger_kind in [CodeActionTriggerKind.INVOKED, CodeActionTriggerKind.AUTOMATIC]
        ):
            return [
                CodeAction(
                    "Create Keyword",
                    kind=CodeActionKinds.QUICKFIX + ".createKeyword",
                    command=Command(
                        "Create Keyword",
                        self.parent.commands.get_command_name(self.create_keyword),
                        [document.document_uri, range, context],
                    ),
                    diagnostics=[kw_not_found_in_diagnostics],
                )
            ]

        return None

    @command("robotcode.createKeyword")
    async def create_keyword(self, document_uri: DocumentUri, range: Range, context: CodeActionContext) -> None:
        from robot.parsing.lexer import Token as RobotToken
        from robot.parsing.model.statements import (
            Fixture,
            KeywordCall,
            Template,
            TestTemplate,
        )
        from robot.utils.escaping import split_from_equals

        document = await self.parent.documents.get(document_uri)
        if document is None:
            return

        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return None

        model = await self.parent.documents_cache.get_model(document, False)
        node = await get_node_at_position(model, range.start)

        if isinstance(node, (KeywordCall, Fixture, TestTemplate, Template)):
            keyword = (
                node.value
                if isinstance(node, (TestTemplate, Template))
                else node.keyword
                if isinstance(node, KeywordCall)
                else node.name
            )

            arguments = []

            for t in node.get_tokens(RobotToken.ARGUMENT):
                name, value = split_from_equals(cast(Token, t).value)
                if value is not None:
                    arguments.append(f"${{{name}}}")
                else:
                    arguments.append(f"${{arg{len(arguments)+1}}}")

            insert_text = (
                KEYWORD_WITH_ARGS_TEMPLATE.substitute(name=keyword, args="    ".join(arguments))
                if arguments
                else KEYWORD_TEMPLATE.substitute(name=keyword)
            )

            keyword_sections = await find_keyword_sections(model)
            keyword_section = keyword_sections[-1] if keyword_sections else None

            if keyword_section is not None:
                node_range = range_from_node(keyword_section)

                insert_range = Range(node_range.end, node_range.end)
            else:
                insert_text = f"\n\n\n*** Keywords ***\n{insert_text}"
                doc_pos = Position(len(document.get_lines()), 0)
                insert_range = Range(doc_pos, doc_pos)

            we = WorkspaceEdit(
                document_changes=[
                    TextDocumentEdit(
                        OptionalVersionedTextDocumentIdentifier(str(document.uri), document.version),
                        [AnnotatedTextEdit(insert_range, insert_text, annotation_id="create_keyword")],
                    )
                ],
                change_annotations={"create_keyword": ChangeAnnotation("Create Keyword", False)},
            )

            await self.parent.workspace.apply_edit(we, "Rename Keyword")
