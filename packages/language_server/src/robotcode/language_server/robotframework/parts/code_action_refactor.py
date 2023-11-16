from __future__ import annotations

import ast
import itertools
from dataclasses import dataclass
from enum import Enum
from string import Template
from typing import TYPE_CHECKING, Any, List, Mapping, Optional, Union

from robotcode.core.dataclasses import as_dict, from_dict
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
    OptionalVersionedTextDocumentIdentifier,
    Position,
    Range,
    TextDocumentEdit,
    TextEdit,
    WorkspaceEdit,
)
from robotcode.core.utils.inspect import iter_methods
from robotcode.robot.utils import get_robot_version

from ...common.decorators import code_action_kinds, language_id
from ...common.text_document import TextDocument
from ..diagnostics.model_helper import ModelHelperMixin
from ..utils import ast_utils
from ..utils.ast_utils import (
    BodyBlock,
    get_node_at_position,
    get_nodes_at_position,
    range_from_node,
    range_from_token,
)
from .code_action_helper_mixin import SHOW_DOCUMENT_SELECT_AND_RENAME_COMMAND, CodeActionDataBase, CodeActionHelperMixin
from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol  # pragma: no cover


class SurroundType(Enum):
    TRY_EXCEPT = "try_except"
    TRY_FINALLY = "try_finally"
    TRY_EXCEPT_FINALLY = "try_except_finally"


@dataclass
class CodeActionData(CodeActionDataBase):
    surround_type: Optional[SurroundType] = None


CODE_ACTION_KIND_SURROUND_WITH = CodeActionKind.REFACTOR.value + ".surround"
CODE_ACTION_KIND_REFACTOR_EXTRACT_FUNCTION = CodeActionKind.REFACTOR_EXTRACT + ".function"
CODE_ACTION_KIND_REFACTOR_EXTRACT_VARIABLE = CodeActionKind.REFACTOR_EXTRACT + ".variable"

TRY_EXCEPT_TEMPLATE = Template(
    """\
${spaces}TRY
${body}
${spaces}EXCEPT    message
${spaces}    Fail    Not Implemented
${spaces}END
"""
)

TRY_EXCEPT_FINALLY_TEMPLATE = Template(
    """\
${spaces}TRY
${body}
${spaces}EXCEPT    message
${spaces}    Fail    Not Implemented
${spaces}FINALLY
${spaces}    Fail    Not Implemented
${spaces}END
"""
)

TRY_FINALLY_TEMPLATE = Template(
    """\
${spaces}TRY
${body}
${spaces}FINALLY
${spaces}    Fail    Not Implemented
${spaces}END
"""
)


class RobotCodeActionRefactorProtocolPart(RobotLanguageServerProtocolPart, ModelHelperMixin, CodeActionHelperMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.code_action.collect.add(self.collect)
        parent.code_action.resolve.add(self.resolve)

        self.parent.commands.register_all(self)

    @language_id("robotframework")
    @code_action_kinds([CODE_ACTION_KIND_REFACTOR_EXTRACT_FUNCTION, CODE_ACTION_KIND_SURROUND_WITH])
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

    async def resolve(self, sender: Any, code_action: CodeAction) -> Optional[CodeAction]:
        if code_action.data is not None and isinstance(code_action.data, Mapping):
            type = code_action.data.get("type", None)
            if type == "refactor":
                method_name = code_action.data.get("method")
                method = next(iter_methods(self, lambda m: m.__name__ == f"resolve_code_action_{method_name}"))
                await method(code_action, data=from_dict(code_action.data, CodeActionData))

        return None

    def get_valid_nodes_in_range(self, model: ast.AST, range: Range, also_return: bool = False) -> List[ast.AST]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.blocks import Block, Keyword, TestCase
        from robot.parsing.model.statements import (
            Comment,
            Documentation,
            ElseHeader,
            ElseIfHeader,
            EmptyLine,
            End,
            Fixture,
            ForHeader,
            IfHeader,
            KeywordName,
            MultiValue,
            SingleValue,
            TemplateArguments,
            TestCaseName,
        )

        if get_robot_version() >= (5, 0, 0):
            from robot.parsing.model.blocks import Try
            from robot.parsing.model.statements import (
                Break,
                Continue,
                ExceptHeader,
                FinallyHeader,
                ReturnStatement,
                TryHeader,
                WhileHeader,
            )

        if not isinstance(model, (Keyword, TestCase)):
            return []

        result = []

        blocks: List[BodyBlock] = []
        for node in ast_utils.iter_nodes(model):
            if isinstance(node, Block) and isinstance(node, BodyBlock):
                blocks.append(node)

            r = range_from_node(node, skip_non_data=True, allow_comments=True)
            if r.is_in_range(range):
                if (
                    isinstance(
                        node,
                        (
                            Fixture,
                            Documentation,
                            MultiValue,
                            SingleValue,
                            TestCaseName,
                            KeywordName,
                            TemplateArguments,
                        ),
                    )
                    or also_return
                    and get_robot_version() >= (5, 0, 0)
                    and isinstance(node, ReturnStatement)
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
                ),
            )
            or get_robot_version() >= (5, 0)
            and isinstance(n, (WhileHeader, TryHeader, ExceptHeader, FinallyHeader))
        ):
            return []

        if get_robot_version() >= (5, 0, 0) and any(
            n
            for n in result
            if isinstance(n, (Continue, Break))
            or isinstance(n, Try)
            and n.type in [RobotToken.EXCEPT, RobotToken.FINALLY, RobotToken.ELSE]
            or also_return
            and isinstance(n, ReturnStatement)
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
                kind=CODE_ACTION_KIND_SURROUND_WITH,
                data=as_dict(
                    CodeActionData("refactor", "surround", document.document_uri, insert_range, SurroundType.TRY_EXCEPT)
                )
                if insert_range
                else None,
                disabled=disabled,
            ),
            CodeAction(
                "Surround with TRY...FINALLY",
                kind=CODE_ACTION_KIND_SURROUND_WITH,
                data=as_dict(
                    CodeActionData(
                        "refactor", "surround", document.document_uri, insert_range, SurroundType.TRY_FINALLY
                    )
                )
                if insert_range
                else None,
                disabled=disabled,
            ),
            CodeAction(
                "Surround with TRY...EXCEPT..FINALLY",
                kind=CODE_ACTION_KIND_SURROUND_WITH,
                data=as_dict(
                    CodeActionData(
                        "refactor", "surround", document.document_uri, insert_range, SurroundType.TRY_EXCEPT_FINALLY
                    )
                )
                if insert_range
                else None,
                disabled=disabled,
            ),
        ]

    async def resolve_code_action_surround(self, code_action: CodeAction, data: CodeActionData) -> Optional[CodeAction]:
        insert_range = data.range

        if not insert_range:
            return None

        document = await self.parent.documents.get(data.document_uri)
        if document is None:
            return None

        lines = document.get_lines()

        if insert_range.end.line >= len(lines):
            insert_range.end.line == len(lines) - 1
            insert_range.end.character = len(lines[-1])

        spaces = "".join(itertools.takewhile(str.isspace, document.get_lines()[insert_range.start.line]))

        body = "".join("    " + lines[r] for r in range(insert_range.start.line, insert_range.end.line))
        body = body.rstrip("\r\n")

        selection_range = None
        template = None

        if data.surround_type == SurroundType.TRY_EXCEPT:
            template = TRY_EXCEPT_TEMPLATE

            p = Position(insert_range.end.line + 1, len(spaces) + 6 + 4)
            selection_range = Range(start=p, end=p)
            selection_range = selection_range.extend(end_character=selection_range.end.character + 7)

        elif data.surround_type == SurroundType.TRY_FINALLY:
            template = TRY_FINALLY_TEMPLATE
            p = Position(insert_range.end.line + 2, len(spaces) + 4)
            selection_range = Range(start=p, end=p)
            selection_range = selection_range.extend(end_character=selection_range.end.character + 14)
        elif data.surround_type == SurroundType.TRY_EXCEPT_FINALLY:
            template = TRY_EXCEPT_FINALLY_TEMPLATE
            p = Position(insert_range.end.line + 1, len(spaces) + 6 + 4)
            selection_range = Range(start=p, end=p)
            selection_range = selection_range.extend(end_character=selection_range.end.character + 7)

        if template is None or selection_range is None:
            return None

        code_action.edit = WorkspaceEdit(
            document_changes=[
                TextDocumentEdit(
                    OptionalVersionedTextDocumentIdentifier(str(document.uri), document.version),
                    [
                        AnnotatedTextEdit(
                            "surround",
                            insert_range,
                            template.substitute(spaces=spaces, body=body),
                        )
                    ],
                )
            ],
            change_annotations={
                "surround": ChangeAnnotation("surround", False),
            },
        )

        code_action.command = Command(
            SHOW_DOCUMENT_SELECT_AND_RENAME_COMMAND,
            SHOW_DOCUMENT_SELECT_AND_RENAME_COMMAND,
            [document.document_uri, selection_range, False],
        )

        return code_action

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
                    kind=CODE_ACTION_KIND_REFACTOR_EXTRACT_VARIABLE,
                    data=as_dict(CodeActionData("refactor", "assign_result_to_variable", document.document_uri, range)),
                )
            ]

        return None

    async def resolve_code_action_assign_result_to_variable(
        self, code_action: CodeAction, data: CodeActionData
    ) -> Optional[CodeAction]:
        from robot.parsing.lexer import Token as RobotToken
        from robot.parsing.model.statements import (
            Fixture,
            KeywordCall,
            Template,
            TestTemplate,
        )

        range = data.range
        document_uri = data.document_uri

        if range.start.line != range.end.line:
            return None

        document = await self.parent.documents.get(document_uri)
        if document is None:
            return None

        model = await self.parent.documents_cache.get_model(document, False)
        nodes = await get_nodes_at_position(model, range.start)
        if not nodes:
            return None
        node = nodes[-1]

        if not isinstance(node, KeywordCall) or node.assign:
            return None

        keyword_token = (
            node.get_token(RobotToken.NAME)
            if isinstance(node, (TestTemplate, Template, Fixture))
            else node.get_token(RobotToken.KEYWORD)
        )

        if keyword_token is None or range.start not in range_from_token(keyword_token):
            return None

        var_name = "new_variable"
        counter = 0
        namespace = await self.parent.documents_cache.get_namespace(document)
        while True:
            if await namespace.find_variable(f"${{{var_name}}}", nodes, range.start, ignore_error=True) is None:
                break
            counter += 1
            var_name = f"new_variable_{counter}"
            if counter > 100:
                return None

        start = range_from_token(keyword_token).start
        code_action.edit = WorkspaceEdit(
            document_changes=[
                TextDocumentEdit(
                    OptionalVersionedTextDocumentIdentifier(str(document.uri), document.version),
                    [AnnotatedTextEdit("assign_result_to_variable", Range(start, start), f"${{{var_name}}}    ")],
                )
            ],
            change_annotations={"assign_result_to_variable": ChangeAnnotation("Assign result to variable", False)},
        )

        selection_range = Range(start, start).extend(start_character=2, end_character=len(var_name) + 2)

        code_action.command = Command(
            SHOW_DOCUMENT_SELECT_AND_RENAME_COMMAND,
            SHOW_DOCUMENT_SELECT_AND_RENAME_COMMAND,
            [document.document_uri, selection_range, False],
        )

        return code_action

    async def code_action_extract_keyword(
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
            nodes_in_range = self.get_valid_nodes_in_range(block, range, also_return=True)
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
                "Extract keyword",
                kind=CODE_ACTION_KIND_REFACTOR_EXTRACT_FUNCTION,
                data=as_dict(CodeActionData("refactor", "extract_keyword", document.document_uri, insert_range))
                if insert_range
                else None,
                disabled=disabled,
            ),
        ]

    async def resolve_code_action_extract_keyword(
        self, code_action: CodeAction, data: CodeActionData
    ) -> Optional[CodeAction]:
        from robot.parsing.model.blocks import Keyword, TestCase

        document = await self.parent.documents.get(data.document_uri)
        if document is None:
            return None

        lines = document.get_lines()
        spaces = "".join(itertools.takewhile(str.isspace, lines[data.range.start.line]))

        model = await self.parent.documents_cache.get_model(document, False)
        namespace = await self.parent.documents_cache.get_namespace(document)

        orig_keyword_name = "New Keyword"
        keyword_name = orig_keyword_name

        kw_counter = 0
        while True:
            kw = await namespace.find_keyword(keyword_name, raise_keyword_error=False)
            if kw is None:
                break
            kw_counter += 1
            keyword_name = f"{orig_keyword_name} {kw_counter}"
            if kw_counter > 100:
                break

        if kw_counter > 100:
            return None

        start_nodes = await get_nodes_at_position(model, data.range.start)
        block = next((n for n in start_nodes if isinstance(n, (Keyword, TestCase))), None)
        if block is None:
            return None

        variable_references = await namespace.get_variable_references()
        local_variable_assignments = await namespace.get_local_variable_assignments()

        block_range = range_from_node(block, skip_non_data=True, allow_comments=True)
        argument_variables = {
            k: v
            for k, v in variable_references.items()
            if hasattr(model, "source")
            and k.source == model.source
            and k.range in block_range
            and k.range not in data.range
            and any(iv for iv in v if iv.uri == document.document_uri and iv.range in data.range)
        }

        end_range = Range(data.range.end, block_range.end)
        assigned_variables = {
            k: v
            for k, v in variable_references.items()
            if hasattr(model, "source")
            and k.source == model.source
            and (
                (
                    k in local_variable_assignments
                    and any(av for av in local_variable_assignments[k] if av in data.range)
                )
                or (
                    k.range in data.range
                    and any(iv for iv in v if iv.uri == document.document_uri and iv.range in end_range)
                )
            )
        }

        argument_variables_text = "    ".join(n.name for n in argument_variables.keys())
        keyword_text = f"{keyword_name}\n"
        if argument_variables_text:
            keyword_text += f"    [Arguments]    {argument_variables_text}\n"

        remove_spaces = None
        for i in range(data.range.start.line, data.range.end.line):
            l = lines[i]
            if not l.rstrip("\r\n").strip():
                continue
            sc = len("".join(itertools.takewhile(str.isspace, l)))
            if remove_spaces is None:
                remove_spaces = sc
            if sc < remove_spaces:
                remove_spaces = sc

        if remove_spaces is None:
            remove_spaces = 0

        for i in range(data.range.start.line, data.range.end.line):
            l = lines[i]
            sc = len("".join(itertools.takewhile(str.isspace, l)))
            if sc >= remove_spaces:
                l = l[remove_spaces:]
            keyword_text += "    " + l

        if assigned_variables:
            keyword_text += "\n    RETURN    " + "    ".join(n.name for n in assigned_variables.keys())

        keyword_text, keyword_range = await self.create_insert_keyword_workspace_edit(
            document, model, namespace, keyword_text
        )

        assigned_variables_text = ""
        if assigned_variables:
            assigned_variables_text += "    ".join(n.name for n in assigned_variables.keys()) + "    "

        keyword_call_text = f"{spaces}{assigned_variables_text}{keyword_name}"
        if argument_variables_text:
            keyword_call_text += f"    {argument_variables_text}"

        edits: List[Union[TextEdit, AnnotatedTextEdit]] = [
            AnnotatedTextEdit("replace_keyword_call", data.range, keyword_call_text + "\n"),
            AnnotatedTextEdit("add_keyword", keyword_range, keyword_text),
        ]

        code_action.edit = WorkspaceEdit(
            document_changes=[
                TextDocumentEdit(
                    OptionalVersionedTextDocumentIdentifier(str(document.uri), document.version),
                    edits,
                )
            ],
            change_annotations={
                "replace_keyword_call": ChangeAnnotation("replace as keyword call", False),
                "add_keyword": ChangeAnnotation("add keyword", False),
            },
        )

        code_action.command = Command(
            SHOW_DOCUMENT_SELECT_AND_RENAME_COMMAND,
            SHOW_DOCUMENT_SELECT_AND_RENAME_COMMAND,
            [
                document.document_uri,
                Range(
                    Position(data.range.start.line, len(spaces) + len(assigned_variables_text)),
                    Position(data.range.start.line, len(spaces) + len(assigned_variables_text) + len(keyword_name)),
                ),
            ],
        )

        return code_action
