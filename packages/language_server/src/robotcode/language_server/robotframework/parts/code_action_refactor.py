from __future__ import annotations

import ast
import itertools
from enum import Enum
from typing import TYPE_CHECKING, Any, List, Optional, Union

from robotcode.core.logging import LoggingDescriptor
from robotcode.core.lsp.types import (
    AnnotatedTextEdit,
    ChangeAnnotation,
    CodeAction,
    CodeActionContext,
    CodeActionDisabledType,
    CodeActionKind,
    CodeActionTriggerKind,
    Command,
    DocumentUri,
    OptionalVersionedTextDocumentIdentifier,
    Position,
    Range,
    TextDocumentEdit,
    TextEdit,
    WorkspaceEdit,
)
from robotcode.core.utils.inspect import iter_methods
from robotcode.language_server.common.decorators import code_action_kinds, command, language_id
from robotcode.language_server.common.text_document import TextDocument
from robotcode.language_server.robotframework.utils import ast_utils
from robotcode.language_server.robotframework.utils.ast_utils import (
    BodyBlock,
    get_node_at_position,
    get_nodes_at_position,
    range_from_node,
    range_from_token,
)
from robotcode.robot.utils import get_robot_version

from .model_helper import ModelHelperMixin
from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol  # pragma: no cover


class SurroundType(Enum):
    TRY_EXCEPT = "try_except"
    TRY_FINALLY = "try_finally"
    TRY_EXCEPT_FINALLY = "try_except_finally"


class RobotCodeActionRefactorProtocolPart(RobotLanguageServerProtocolPart, ModelHelperMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.code_action.collect.add(self.collect)

        self.parent.commands.register_all(self)

    @language_id("robotframework")
    @code_action_kinds([CodeActionKind.REFACTOR_REWRITE, CodeActionKind.REFACTOR_EXTRACT])
    async def collect(
        self, sender: Any, document: TextDocument, range: Range, context: CodeActionContext
    ) -> Optional[List[Union[Command, CodeAction]]]:
        result = []
        for method in iter_methods(self, lambda m: m.__name__.startswith("code_action_")):
            code_actions = await method(document, range, context)
            if code_actions:
                result.extend(code_actions)

        if result:
            return list(sorted(result, key=lambda ca: ca.title))

        return None

    def get_valid_nodes_in_range(self, model: ast.AST, range: Range) -> List[ast.AST]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.blocks import Block, Keyword, TestCase, Try
        from robot.parsing.model.statements import (
            Comment,
            Documentation,
            ElseHeader,
            ElseIfHeader,
            EmptyLine,
            End,
            ExceptHeader,
            FinallyHeader,
            Fixture,
            ForHeader,
            IfHeader,
            KeywordName,
            MultiValue,
            SingleValue,
            TestCaseName,
            TryHeader,
            WhileHeader,
        )

        if get_robot_version() >= (5, 0, 0):
            from robot.parsing.model.statements import Break, Continue

        if not isinstance(model, (Keyword, TestCase)):
            return []

        result = []

        blocks: List[BodyBlock] = []
        for node in ast_utils.iter_nodes(model):
            if isinstance(node, Block) and isinstance(node, BodyBlock):
                blocks.append(node)

            r = range_from_node(node, skip_non_data=True, allow_comments=True)
            if r.is_in_range(range):
                if isinstance(
                    node,
                    (
                        Fixture,
                        Documentation,
                        MultiValue,
                        SingleValue,
                        TestCaseName,
                        KeywordName,
                    ),
                ):
                    return []

                result.append(node)
            elif (
                result
                and r.start.is_in_range(range)
                and not r.end.is_in_range(range)
                and not isinstance(node, EmptyLine)
            ):
                return []
            elif (
                not result
                and not isinstance(node, Block)
                and not r.start.is_in_range(range)
                and r.end.is_in_range(range)
            ):
                return []

        results = []
        for block in [model, *blocks]:
            sub = [n for n in result if n in ast_utils.iter_nodes(block, False)]
            if sub:
                results.append(sub)

        if not results:
            return []

        if results:
            result = results[0]

        if any(
            n
            for n in result
            if isinstance(
                n,
                (
                    IfHeader,
                    ElseIfHeader,
                    ElseHeader,
                    ForHeader,
                    End,
                    TryHeader,
                    ExceptHeader,
                    FinallyHeader,
                    WhileHeader,
                ),
            )
        ):
            return []

        if get_robot_version() >= (5, 0, 0) and any(
            n
            for n in result
            if isinstance(n, (Continue, Break))
            or isinstance(n, Try)
            and n.type in [RobotToken.EXCEPT, RobotToken.FINALLY, RobotToken.ELSE]
        ):
            return []

        if all(isinstance(n, (EmptyLine, Comment)) for n in result):
            return []

        return result

    async def code_action_surround(
        self, document: TextDocument, range: Range, context: CodeActionContext
    ) -> Optional[List[Union[Command, CodeAction]]]:
        from robot.parsing.model.blocks import Keyword, TestCase

        if range.start == range.end:
            return None

        model = await self.parent.documents_cache.get_model(document, False)
        start_nodes = await get_nodes_at_position(model, range.start)

        enabled = False
        insert_range = None
        block = next((n for n in start_nodes if isinstance(n, (Keyword, TestCase))), None)
        if block is not None:
            nodes_in_range = self.get_valid_nodes_in_range(block, range)
            if nodes_in_range:
                enabled = True
                start_p = range_from_node(nodes_in_range[0]).start
                start_p.character = 0
                end_p = range_from_node(nodes_in_range[-1]).end
                end_p.line += 1
                end_p.character = 0
                insert_range = Range(start=start_p, end=end_p)

        disabled = CodeActionDisabledType("A keyword call must be selected.") if not enabled else None

        return [
            CodeAction(
                "Surround with TRY...EXCEPT",
                kind=CodeActionKind.REFACTOR_REWRITE,
                command=Command(
                    self.parent.commands.get_command_name(self.surround_with_command),
                    self.parent.commands.get_command_name(self.surround_with_command),
                    [document.document_uri, insert_range, SurroundType.TRY_EXCEPT],
                ),
                disabled=disabled,
            ),
            CodeAction(
                "Surround with TRY...FINALLY",
                kind=CodeActionKind.REFACTOR_REWRITE,
                command=Command(
                    self.parent.commands.get_command_name(self.surround_with_command),
                    self.parent.commands.get_command_name(self.surround_with_command),
                    [document.document_uri, insert_range, SurroundType.TRY_FINALLY],
                ),
                disabled=disabled,
            ),
            CodeAction(
                "Surround with TRY...EXCEPT..FINALLY",
                kind=CodeActionKind.REFACTOR_REWRITE,
                command=Command(
                    self.parent.commands.get_command_name(self.surround_with_command),
                    self.parent.commands.get_command_name(self.surround_with_command),
                    [document.document_uri, insert_range, SurroundType.TRY_EXCEPT_FINALLY],
                ),
                disabled=disabled,
            ),
        ]

    @command("robotcode.surroundWith")
    async def surround_with_command(
        self, document_uri: DocumentUri, insert_range: Optional[Range], type: SurroundType
    ) -> None:
        if insert_range is None or not insert_range:
            return

        document = await self.parent.documents.get(document_uri)
        if document is None:
            return

        spaces = "".join(itertools.takewhile(str.isspace, document.get_lines()[insert_range.start.line]))

        edits: List[Union[TextEdit, AnnotatedTextEdit]] = [
            AnnotatedTextEdit("add_spaces", Range(start=Position(r, 0), end=Position(r, 0)), "    ")
            for r in range(insert_range.start.line, insert_range.end.line)
        ]

        edits.insert(
            0,
            AnnotatedTextEdit(
                "add_try",
                Range(start=Position(insert_range.start.line, 0), end=Position(insert_range.start.line, 0)),
                f"{spaces}TRY\n",
            ),
        )

        selection_range = None
        if type == SurroundType.TRY_EXCEPT:
            edits.append(
                AnnotatedTextEdit(
                    "add_clause",
                    Range(start=Position(insert_range.end.line, 0), end=Position(insert_range.end.line, 0)),
                    f"{spaces}EXCEPT    message\n{spaces}    Fail    implement this\n{spaces}END\n",
                )
            )
            p = Position(insert_range.end.line + 1, len(spaces) + 6 + 4)
            selection_range = Range(start=p, end=p)
            selection_range = selection_range.extend(end_character=selection_range.end.character + 7)

        elif type == SurroundType.TRY_FINALLY:
            edits.append(
                AnnotatedTextEdit(
                    "add_clause",
                    Range(start=Position(insert_range.end.line, 0), end=Position(insert_range.end.line, 0)),
                    f"{spaces}FINALLY\n{spaces}    Fail    implement this\n{spaces}END\n",
                )
            )
            p = Position(insert_range.end.line + 2, len(spaces) + 4)
            selection_range = Range(start=p, end=p)
            selection_range = selection_range.extend(end_character=selection_range.end.character + 14)
        elif type == SurroundType.TRY_EXCEPT_FINALLY:
            edits.append(
                AnnotatedTextEdit(
                    "add_clause",
                    Range(start=Position(insert_range.end.line, 0), end=Position(insert_range.end.line, 0)),
                    f"{spaces}EXCEPT    message\n"
                    f"{spaces}    Fail    implement this\n"
                    f"{spaces}FINALLY\n"
                    f"{spaces}    Fail    implement this\n"
                    f"{spaces}END\n",
                )
            )
            p = Position(insert_range.end.line + 1, len(spaces) + 6 + 4)
            selection_range = Range(start=p, end=p)
            selection_range = selection_range.extend(end_character=selection_range.end.character + 7)

        we = WorkspaceEdit(
            document_changes=[
                TextDocumentEdit(
                    OptionalVersionedTextDocumentIdentifier(str(document.uri), document.version),
                    edits,
                )
            ],
            change_annotations={
                "add_try": ChangeAnnotation("add try", False),
                "add_spaces": ChangeAnnotation("add spaces", False),
                "add_clause": ChangeAnnotation("add clause", False),
            },
        )

        if (await self.parent.workspace.apply_edit(we)).applied and selection_range is not None:
            await self.parent.window.show_document(str(document.uri), take_focus=True, selection=selection_range)

    async def code_action_assign_result_to_variable(
        self, document: TextDocument, range: Range, context: CodeActionContext
    ) -> Optional[List[Union[Command, CodeAction]]]:
        from robot.parsing.lexer import Token as RobotToken
        from robot.parsing.model.statements import (
            Fixture,
            KeywordCall,
            Template,
            TestTemplate,
        )

        if range.start.line == range.end.line and (
            (context.only and CodeActionKind.REFACTOR_EXTRACT in context.only)
            or context.trigger_kind
            in [
                CodeActionTriggerKind.INVOKED,
                CodeActionTriggerKind.AUTOMATIC,
            ]
        ):
            model = await self.parent.documents_cache.get_model(document, False)
            node = await get_node_at_position(model, range.start)

            if not isinstance(node, KeywordCall) or node.assign:
                return None

            keyword_token = (
                node.get_token(RobotToken.NAME)
                if isinstance(node, (TestTemplate, Template, Fixture))
                else node.get_token(RobotToken.KEYWORD)
            )

            if keyword_token is None or range.start not in range_from_token(keyword_token):
                return None

            return [
                CodeAction(
                    "Assign keyword result to variable",
                    kind=CodeActionKind.REFACTOR_EXTRACT,
                    command=Command(
                        self.parent.commands.get_command_name(self.assign_result_to_variable_command),
                        self.parent.commands.get_command_name(self.assign_result_to_variable_command),
                        [document.document_uri, range],
                    ),
                )
            ]

        return None

    @command("robotcode.assignResultToVariable")
    async def assign_result_to_variable_command(self, document_uri: DocumentUri, range: Range) -> None:
        from robot.parsing.lexer import Token as RobotToken
        from robot.parsing.model.statements import (
            Fixture,
            KeywordCall,
            Template,
            TestTemplate,
        )

        if range.start.line == range.end.line and range.start.character <= range.end.character:
            document = await self.parent.documents.get(document_uri)
            if document is None:
                return

            model = await self.parent.documents_cache.get_model(document, False)
            node = await get_node_at_position(model, range.start)

            if not isinstance(node, KeywordCall) or node.assign:
                return

            keyword_token = (
                node.get_token(RobotToken.NAME)
                if isinstance(node, (TestTemplate, Template, Fixture))
                else node.get_token(RobotToken.KEYWORD)
            )

            if keyword_token is None or range.start not in range_from_token(keyword_token):
                return

            start = range_from_token(keyword_token).start
            we = WorkspaceEdit(
                document_changes=[
                    TextDocumentEdit(
                        OptionalVersionedTextDocumentIdentifier(str(document.uri), document.version),
                        [AnnotatedTextEdit("assign_result_to_variable", Range(start, start), "${result}    ")],
                    )
                ],
                change_annotations={"assign_result_to_variable": ChangeAnnotation("Assign result to variable", False)},
            )

            if (await self.parent.workspace.apply_edit(we)).applied:
                insert_range = Range(start, start).extend(start_character=2, end_character=8)

                await self.parent.window.show_document(str(document.uri), take_focus=True, selection=insert_range)
