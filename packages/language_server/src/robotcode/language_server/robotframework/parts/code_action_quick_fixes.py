from __future__ import annotations

import ast
from string import Template
from typing import TYPE_CHECKING, Any, List, Optional, Union, cast

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
    WorkspaceEdit,
)
from robotcode.core.utils.inspect import iter_methods
from robotcode.language_server.common.decorators import code_action_kinds, command, language_id
from robotcode.language_server.common.text_document import TextDocument
from robotcode.language_server.robotframework.diagnostics.errors import DIAGNOSTICS_SOURCE_NAME, Error
from robotcode.language_server.robotframework.utils.ast_utils import (
    FirstAndLastRealStatementFinder,
    Token,
    get_node_at_position,
    get_nodes_at_position,
    get_tokens_at_position,
    range_from_node,
    range_from_token,
)
from robotcode.language_server.robotframework.utils.async_ast import Visitor

from .model_helper import ModelHelperMixin
from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol  # pragma: no cover


KEYWORD_WITH_ARGS_TEMPLATE = Template(
    """\
${name}
    [Arguments]    ${args}
    # TODO: implement keyword "${name}".
    Fail    Not Implemented

"""
)

KEYWORD_TEMPLATE = Template(
    """\
${name}
    # TODO: implement keyword "${name}".
    Fail    Not Implemented

"""
)


class FindSectionsVisitor(Visitor):
    def __init__(self) -> None:
        self.keyword_sections: List[ast.AST] = []
        self.variable_sections: List[ast.AST] = []
        self.setting_sections: List[ast.AST] = []
        self.testcase_sections: List[ast.AST] = []
        self.sections: List[ast.AST] = []

    def visit_KeywordSection(self, node: ast.AST) -> None:  # noqa: N802
        self.keyword_sections.append(node)
        self.sections.append(node)

    def visit_VariableSection(self, node: ast.AST) -> None:  # noqa: N802
        self.variable_sections.append(node)
        self.sections.append(node)

    def visit_SettingSection(self, node: ast.AST) -> None:  # noqa: N802
        self.setting_sections.append(node)
        self.sections.append(node)

    def visit_TestCaseSection(self, node: ast.AST) -> None:  # noqa: N802
        self.testcase_sections.append(node)
        self.sections.append(node)

    def visit_CommentSection(self, node: ast.AST) -> None:  # noqa: N802
        self.sections.append(node)


def find_keyword_sections(node: ast.AST) -> Optional[List[ast.AST]]:
    visitor = FindSectionsVisitor()
    visitor.visit(node)
    return visitor.keyword_sections if visitor.keyword_sections else None


class RobotCodeActionQuickFixesProtocolPart(RobotLanguageServerProtocolPart, ModelHelperMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.code_action.collect.add(self.collect)

        self.parent.commands.register_all(self)

    @language_id("robotframework")
    @code_action_kinds([CodeActionKind.QUICK_FIX])
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

    async def code_action_create_keyword(
        self, document: TextDocument, range: Range, context: CodeActionContext
    ) -> Optional[List[Union[Command, CodeAction]]]:
        from robot.parsing.model.statements import (
            Fixture,
            KeywordCall,
            Template,
            TestTemplate,
        )

        result: List[Union[Command, CodeAction]] = []

        if (context.only and CodeActionKind.QUICK_FIX in context.only) or context.trigger_kind in [
            CodeActionTriggerKind.INVOKED,
            CodeActionTriggerKind.AUTOMATIC,
        ]:
            model = await self.parent.documents_cache.get_model(document, False)
            namespace = await self.parent.documents_cache.get_namespace(document)

            for diagnostic in (
                d
                for d in context.diagnostics
                if d.source == DIAGNOSTICS_SOURCE_NAME and d.code == Error.KEYWORD_NOT_FOUND
            ):
                disabled = None
                node = await get_node_at_position(model, diagnostic.range.start)

                if isinstance(node, (KeywordCall, Fixture, TestTemplate, Template)):
                    tokens = get_tokens_at_position(node, diagnostic.range.start)
                    if not tokens:
                        continue

                    keyword_token = tokens[-1]

                    bdd_token, token = self.split_bdd_prefix(namespace, keyword_token)
                    if bdd_token is not None and token is not None:
                        keyword_token = token

                    lib_entry, kw_namespace = await self.get_namespace_info_from_keyword(namespace, keyword_token)

                    if lib_entry is not None and lib_entry.library_doc.type == "LIBRARY":
                        disabled = CodeActionDisabledType("Keyword is from a library")

                    text = keyword_token.value

                    if lib_entry and kw_namespace:
                        text = text[len(kw_namespace) + 1 :].strip()

                    if not text:
                        continue

                    result.append(
                        CodeAction(
                            f"Create Keyword `{text}`",
                            kind=CodeActionKind.QUICK_FIX,
                            command=Command(
                                self.parent.commands.get_command_name(self.create_keyword_command),
                                self.parent.commands.get_command_name(self.create_keyword_command),
                                [document.document_uri, diagnostic.range],
                            ),
                            diagnostics=[diagnostic],
                            disabled=disabled,
                            is_preferred=True,
                        )
                    )

        return result if result else None

    @command("robotcode.createKeyword")
    async def create_keyword_command(self, document_uri: DocumentUri, range: Range) -> None:
        from robot.parsing.lexer import Token as RobotToken
        from robot.parsing.model.statements import (
            Fixture,
            KeywordCall,
            Template,
            TestTemplate,
        )
        from robot.utils.escaping import split_from_equals
        from robot.variables.search import contains_variable

        document = await self.parent.documents.get(document_uri)
        if document is None:
            return

        model = await self.parent.documents_cache.get_model(document, False)
        node = await get_node_at_position(model, range.start)

        if isinstance(node, (KeywordCall, Fixture, TestTemplate, Template)):
            tokens = get_tokens_at_position(node, range.start)
            if not tokens:
                return

            keyword_token = tokens[-1]

            namespace = await self.parent.documents_cache.get_namespace(document)

            bdd_token, token = self.split_bdd_prefix(namespace, keyword_token)
            if bdd_token is not None and token is not None:
                keyword_token = token

            lib_entry, kw_namespace = await self.get_namespace_info_from_keyword(namespace, keyword_token)

            if lib_entry is not None and lib_entry.library_doc.type == "LIBRARY":
                return

            text = keyword_token.value

            if lib_entry and kw_namespace:
                text = text[len(kw_namespace) + 1 :].strip()

            if not text:
                return

            arguments = []

            # TODO: Check if keyword has a valid namespace and use it instead of the current namespace. (Issue #9)
            for t in node.get_tokens(RobotToken.ARGUMENT):
                name, value = split_from_equals(cast(Token, t).value)
                if value is not None and not contains_variable(name, "$@&%"):
                    arguments.append(f"${{{name}}}")
                else:
                    arguments.append(f"${{arg{len(arguments)+1}}}")

            insert_text = (
                KEYWORD_WITH_ARGS_TEMPLATE.substitute(name=text, args="    ".join(arguments))
                if arguments
                else KEYWORD_TEMPLATE.substitute(name=text)
            )

            if lib_entry is not None and lib_entry.library_doc.type == "RESOURCE" and lib_entry.library_doc.source:
                dest_document = await self.parent.documents.get_or_open_document(lib_entry.library_doc.source)
            else:
                dest_document = document

            await self._apply_create_keyword(dest_document, insert_text)

    async def _apply_create_keyword(self, document: TextDocument, insert_text: str) -> None:
        model = await self.parent.documents_cache.get_model(document, False)
        namespace = await self.parent.documents_cache.get_namespace(document)

        keyword_sections = find_keyword_sections(model)
        keyword_section = keyword_sections[-1] if keyword_sections else None

        if keyword_section is not None:
            node_range = range_from_node(keyword_section)

            insert_pos = Position(node_range.end.line + 1, 0)
            insert_range = Range(insert_pos, insert_pos)

            insert_text = f"\n{insert_text}"
        else:
            if namespace.languages is None or not namespace.languages.languages:
                keywords_text = "Keywords"
            else:
                keywords_text = namespace.languages.languages[-1].keywords_header

            insert_text = f"\n\n*** {keywords_text} ***\n{insert_text}"

            lines = document.get_lines()
            end_line = len(lines) - 1
            while end_line >= 0 and not lines[end_line].strip():
                end_line -= 1
            doc_pos = Position(end_line + 1, 0)

            insert_range = Range(doc_pos, doc_pos)

        we = WorkspaceEdit(
            document_changes=[
                TextDocumentEdit(
                    OptionalVersionedTextDocumentIdentifier(str(document.uri), document.version),
                    [AnnotatedTextEdit("create_keyword", insert_range, insert_text)],
                )
            ],
            change_annotations={"create_keyword": ChangeAnnotation("Create Keyword", False)},
        )

        if (await self.parent.workspace.apply_edit(we)).applied:
            lines = insert_text.rstrip().splitlines()
            insert_range.start.line += len(lines) - 1
            insert_range.start.character = 4
            insert_range.end = Position(insert_range.start.line, insert_range.start.character)
            insert_range.end.character += len(lines[-1])
            await self.parent.window.show_document(str(document.uri), take_focus=True, selection=insert_range)

    async def code_action_disable_robotcode_diagnostics_for_line(
        self, document: TextDocument, range: Range, context: CodeActionContext
    ) -> Optional[List[Union[Command, CodeAction]]]:
        if (context.only and CodeActionKind.QUICK_FIX in context.only) or context.trigger_kind in [
            CodeActionTriggerKind.INVOKED,
            CodeActionTriggerKind.AUTOMATIC,
        ]:
            all_diagnostics = [d for d in context.diagnostics if d.source and d.source.startswith("robotcode.")]
            if all_diagnostics:
                return [
                    CodeAction(
                        f"Disable '{diagnostics.code}' for this line",
                        kind=CodeActionKind.QUICK_FIX,
                        command=Command(
                            self.parent.commands.get_command_name(self.disable_robotcode_diagnostics_for_line_command),
                            self.parent.commands.get_command_name(self.disable_robotcode_diagnostics_for_line_command),
                            [document.document_uri, range],
                        ),
                        diagnostics=[diagnostics],
                    )
                    for diagnostics in all_diagnostics
                ]

        return None

    @command("robotcode.disableRobotcodeDiagnosticsForLine")
    async def disable_robotcode_diagnostics_for_line_command(self, document_uri: DocumentUri, range: Range) -> None:
        if range.start.line == range.end.line and range.start.character <= range.end.character:
            document = await self.parent.documents.get(document_uri)
            if document is None:
                return

            insert_text = "    # robotcode: ignore"

            line = document.get_lines()[range.start.line]
            stripped_line = line.rstrip()

            insert_range = Range(
                start=Position(range.start.line, len(stripped_line)), end=Position(range.start.line, len(line))
            )
            we = WorkspaceEdit(
                document_changes=[
                    TextDocumentEdit(
                        OptionalVersionedTextDocumentIdentifier(str(document.uri), document.version),
                        [AnnotatedTextEdit("disable_robotcode_diagnostics_for_line", insert_range, insert_text)],
                    )
                ],
                change_annotations={
                    "disable_robotcode_diagnostics_for_line": ChangeAnnotation(
                        "Disable robotcode diagnostics for line", False
                    )
                },
            )

            await self.parent.workspace.apply_edit(we)

    async def code_action_create_local_variable(
        self, document: TextDocument, range: Range, context: CodeActionContext
    ) -> Optional[List[Union[Command, CodeAction]]]:
        from robot.parsing.model.blocks import Keyword, TestCase
        from robot.parsing.model.statements import Documentation, Fixture, Statement, Template

        result: List[Union[Command, CodeAction]] = []

        if (context.only and CodeActionKind.QUICK_FIX in context.only) or context.trigger_kind in [
            CodeActionTriggerKind.INVOKED,
            CodeActionTriggerKind.AUTOMATIC,
        ]:
            for diagnostic in (
                d
                for d in context.diagnostics
                if d.source == DIAGNOSTICS_SOURCE_NAME and d.code == Error.VARIABLE_NOT_FOUND
            ):
                if (
                    diagnostic.range.start.line == diagnostic.range.end.line
                    and diagnostic.range.start.character < diagnostic.range.end.character
                ):
                    model = await self.parent.documents_cache.get_model(document, False)
                    nodes = await get_nodes_at_position(model, range.start)

                    if not any(n for n in nodes if isinstance(n, (Keyword, TestCase))):
                        continue

                    node = nodes[-1] if nodes else None
                    if node is None or isinstance(node, (Documentation, Fixture, Template)):
                        continue

                    if not isinstance(node, Statement):
                        continue

                    text = document.get_lines()[diagnostic.range.start.line][
                        diagnostic.range.start.character : diagnostic.range.end.character
                    ]
                    if not text:
                        continue

                    result.append(
                        CodeAction(
                            f"Create local variable `${{{text}}}`",
                            kind=CodeActionKind.QUICK_FIX,
                            command=Command(
                                self.parent.commands.get_command_name(self.create_local_variable_command),
                                self.parent.commands.get_command_name(self.create_local_variable_command),
                                [document.document_uri, diagnostic.range],
                            ),
                            diagnostics=[diagnostic],
                        )
                    )

        return result if result else None

    @command("robotcode.createLocalVariable")
    async def create_local_variable_command(self, document_uri: DocumentUri, range: Range) -> None:
        from robot.parsing.model.blocks import Keyword, TestCase
        from robot.parsing.model.statements import Documentation, Fixture, Statement, Template

        if range.start.line == range.end.line and range.start.character <= range.end.character:
            document = await self.parent.documents.get(document_uri)
            if document is None:
                return

            model = await self.parent.documents_cache.get_model(document, False)
            nodes = await get_nodes_at_position(model, range.start)

            if not any(n for n in nodes if isinstance(n, (Keyword, TestCase))):
                return

            node = nodes[-1] if nodes else None
            if node is None or isinstance(node, (Documentation, Fixture, Template)):
                return

            if not isinstance(node, Statement):
                return

            text = document.get_lines()[range.start.line][range.start.character : range.end.character]
            if not text:
                return

            spaces = node.tokens[0].value if node.tokens and node.tokens[0].type == "SEPARATOR" else "    "

            insert_text = f"{spaces}${{{text}}}    Set Variable    value\n"
            node_range = range_from_node(node)
            insert_range = Range(start=Position(node_range.start.line, 0), end=Position(node_range.start.line, 0))
            we = WorkspaceEdit(
                document_changes=[
                    TextDocumentEdit(
                        OptionalVersionedTextDocumentIdentifier(str(document.uri), document.version),
                        [AnnotatedTextEdit("create_local_variable", insert_range, insert_text)],
                    )
                ],
                change_annotations={"create_local_variable": ChangeAnnotation("Create Local variable", False)},
            )

            if (await self.parent.workspace.apply_edit(we)).applied:
                insert_range.start.character += insert_text.rindex("value")
                insert_range.end.character = insert_range.start.character + len("value")

                await self.parent.window.show_document(str(document.uri), take_focus=False, selection=insert_range)

    async def code_action_create_suite_variable(
        self, document: TextDocument, range: Range, context: CodeActionContext
    ) -> Optional[List[Union[Command, CodeAction]]]:
        result: List[Union[Command, CodeAction]] = []

        if (context.only and CodeActionKind.QUICK_FIX in context.only) or context.trigger_kind in [
            CodeActionTriggerKind.INVOKED,
            CodeActionTriggerKind.AUTOMATIC,
        ]:
            for diagnostic in (
                d
                for d in context.diagnostics
                if d.source == DIAGNOSTICS_SOURCE_NAME and d.code == Error.VARIABLE_NOT_FOUND
            ):
                if (
                    diagnostic.range.start.line == diagnostic.range.end.line
                    and diagnostic.range.start.character < diagnostic.range.end.character
                ):
                    lines = document.get_lines()
                    text = lines[diagnostic.range.start.line][
                        diagnostic.range.start.character : diagnostic.range.end.character
                    ]
                    if not text:
                        continue
                    result.append(
                        CodeAction(
                            f"Create suite variable `${{{text}}}`",
                            kind=CodeActionKind.QUICK_FIX,
                            command=Command(
                                self.parent.commands.get_command_name(self.create_suite_variable_command),
                                self.parent.commands.get_command_name(self.create_suite_variable_command),
                                [document.document_uri, diagnostic.range],
                            ),
                            diagnostics=[diagnostic],
                        )
                    )

        return result if result else None

    @command("robotcode.createSuiteVariable")
    async def create_suite_variable_command(self, document_uri: DocumentUri, range: Range) -> None:
        from robot.parsing.model.blocks import VariableSection
        from robot.parsing.model.statements import Variable

        if range.start.line == range.end.line and range.start.character <= range.end.character:
            document = await self.parent.documents.get(document_uri)
            if document is None:
                return

            model = await self.parent.documents_cache.get_model(document, False)
            nodes = await get_nodes_at_position(model, range.start)

            node = nodes[-1] if nodes else None

            if node is None:
                return

            insert_range_prefix = ""
            insert_range_suffix = ""

            if any(n for n in nodes if isinstance(n, (VariableSection))) and isinstance(node, Variable):
                node_range = range_from_node(node)
                insert_range = Range(start=Position(node_range.start.line, 0), end=Position(node_range.start.line, 0))
            else:
                finder = FindSectionsVisitor()
                finder.visit(model)

                if finder.variable_sections:
                    section = finder.variable_sections[-1]

                    _, last_stmt = FirstAndLastRealStatementFinder.find_from(section)
                    end_lineno = last_stmt.end_lineno if last_stmt else section.end_lineno
                    if end_lineno is None:
                        return

                    insert_range = Range(start=Position(end_lineno, 0), end=Position(end_lineno, 0))
                else:
                    insert_range_prefix = "\n\n*** Variables ***\n"
                    if finder.setting_sections:
                        insert_range_prefix = "\n\n*** Variables ***\n"
                        insert_range_suffix = "\n\n"
                        section = finder.setting_sections[-1]

                        _, last_stmt = FirstAndLastRealStatementFinder.find_from(section)
                        end_lineno = last_stmt.end_lineno if last_stmt else section.end_lineno
                        if end_lineno is None:
                            return

                        insert_range = Range(start=Position(end_lineno, 0), end=Position(end_lineno, 0))
                    else:
                        insert_range_prefix = "*** Variables ***\n"
                        insert_range_suffix = "\n\n"
                        insert_range = Range(start=Position(0, 0), end=Position(0, 0))

            lines = document.get_lines()
            text = lines[range.start.line][range.start.character : range.end.character]
            if not text:
                return
            if insert_range.start.line == insert_range.end.line and insert_range.start.line >= len(lines):
                insert_range.start.line = len(lines) - 1
                insert_range.start.character = len(lines[-1])
                insert_range_prefix = "\n" + insert_range_prefix
            insert_text = insert_range_prefix + f"${{{text}}}    value\n" + insert_range_suffix
            we = WorkspaceEdit(
                document_changes=[
                    TextDocumentEdit(
                        OptionalVersionedTextDocumentIdentifier(str(document.uri), document.version),
                        [AnnotatedTextEdit("create_suite_variable", insert_range, insert_text)],
                    )
                ],
                change_annotations={"create_suite_variable": ChangeAnnotation("Create suite variable", False)},
            )

            if (await self.parent.workspace.apply_edit(we)).applied:
                splitted = insert_text.splitlines()
                start_line = next((i for i, l in enumerate(splitted) if "value" in l), 0)
                insert_range.start.line = insert_range.start.line + start_line
                insert_range.end.line = insert_range.start.line
                insert_range.start.character = splitted[start_line].rindex("value")
                insert_range.end.character = insert_range.start.character + len("value")

                await self.parent.window.show_document(str(document.uri), take_focus=False, selection=insert_range)

    async def code_action_add_argument(
        self, document: TextDocument, range: Range, context: CodeActionContext
    ) -> Optional[List[Union[Command, CodeAction]]]:
        from robot.parsing.model.blocks import Keyword

        result: List[Union[Command, CodeAction]] = []

        if (context.only and CodeActionKind.QUICK_FIX in context.only) or context.trigger_kind in [
            CodeActionTriggerKind.INVOKED,
            CodeActionTriggerKind.AUTOMATIC,
        ]:
            for diagnostic in (
                d
                for d in context.diagnostics
                if d.source == DIAGNOSTICS_SOURCE_NAME and d.code == Error.VARIABLE_NOT_FOUND
            ):
                if (
                    diagnostic.range.start.line == diagnostic.range.end.line
                    and diagnostic.range.start.character < diagnostic.range.end.character
                ):
                    diagnostic.range.start.line == diagnostic.range.end.line
                    text = document.get_lines()[diagnostic.range.start.line][
                        diagnostic.range.start.character : diagnostic.range.end.character
                    ]
                    if not text:
                        continue

                    model = await self.parent.documents_cache.get_model(document, False)
                    nodes = await get_nodes_at_position(model, range.start)

                    if not any(n for n in nodes if isinstance(n, Keyword)):
                        continue

                    result.append(
                        CodeAction(
                            f"Add argument `${{{text}}}`",
                            kind=CodeActionKind.QUICK_FIX,
                            command=Command(
                                self.parent.commands.get_command_name(self.action_add_argument_command),
                                self.parent.commands.get_command_name(self.action_add_argument_command),
                                [document.document_uri, diagnostic.range],
                            ),
                            diagnostics=[diagnostic],
                        )
                    )

        return result if result else None

    @command("robotcode.actionAddArgument")
    async def action_add_argument_command(self, document_uri: DocumentUri, range: Range) -> None:
        from robot.parsing.lexer.tokens import Token
        from robot.parsing.model.blocks import Keyword
        from robot.parsing.model.statements import Arguments, Documentation

        if range.start.line == range.end.line and range.start.character <= range.end.character:
            document = await self.parent.documents.get(document_uri)
            if document is None:
                return

            text = document.get_lines()[range.start.line][range.start.character : range.end.character]
            if not text:
                return

            model = await self.parent.documents_cache.get_model(document, False)
            nodes = await get_nodes_at_position(model, range.start)

            keyword = next((n for n in nodes if isinstance(n, Keyword)), None)
            if keyword is None:
                return

            arguments = next((n for n in keyword.body if isinstance(n, Arguments)), None)

            if arguments is None:
                i = 0
                first_stmt = keyword.body[i]

                while isinstance(first_stmt, Documentation) and i < len(keyword.body):
                    i += 1
                    first_stmt = keyword.body[i]

                if i >= len(keyword.body):
                    return

                spaces = (
                    first_stmt.tokens[0].value
                    if first_stmt is not None and first_stmt.tokens and first_stmt.tokens[0].type == "SEPARATOR"
                    else "    "
                )

                insert_text = f"{spaces}[Arguments]    ${{{text}}}=\n"
                node_range = range_from_node(first_stmt)
                insert_range = Range(start=Position(node_range.start.line, 0), end=Position(node_range.start.line, 0))
            else:
                insert_text = f"    ${{{text}}}="
                argument_tokens = arguments.get_tokens(Token.ARGUMENT)
                if argument_tokens:
                    token_range = range_from_token(argument_tokens[-1])
                else:
                    token_range = range_from_token(arguments.get_token(Token.ARGUMENTS))
                insert_range = Range(start=token_range.end, end=token_range.end)

            we = WorkspaceEdit(
                document_changes=[
                    TextDocumentEdit(
                        OptionalVersionedTextDocumentIdentifier(str(document.uri), document.version),
                        [AnnotatedTextEdit("add_argument", insert_range, insert_text)],
                    )
                ],
                change_annotations={"add_argument": ChangeAnnotation("Add Argument", False)},
            )

            if (await self.parent.workspace.apply_edit(we)).applied:
                insert_range.start.character += len(insert_text)
                insert_range.end.character = insert_range.start.character

                await self.parent.window.show_document(str(document.uri), take_focus=False, selection=insert_range)
