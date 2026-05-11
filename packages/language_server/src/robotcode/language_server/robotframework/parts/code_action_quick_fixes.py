from collections import defaultdict
from dataclasses import dataclass
from string import Template as StringTemplate
from typing import (
    TYPE_CHECKING,
    Any,
    Iterable,
    List,
    Mapping,
    Optional,
    Tuple,
    Union,
    cast,
)

from robot.parsing.lexer.tokens import Token
from robot.parsing.model.blocks import Keyword, TestCase, VariableSection
from robot.parsing.model.statements import (
    Arguments,
    Documentation,
    Fixture,
    KeywordCall,
    KeywordName,
    Statement,
    Template,
    TestCaseName,
    TestTemplate,
    Variable,
)
from robot.utils.escaping import split_from_equals
from robot.variables.search import contains_variable

from robotcode.core.language import language_id
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
    WorkspaceEdit,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.dataclasses import as_dict, from_dict
from robotcode.core.utils.inspect import iter_methods
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.robot.diagnostics.entities import LibraryEntry
from robotcode.robot.diagnostics.errors import DIAGNOSTICS_SOURCE_NAME, Error
from robotcode.robot.diagnostics.model_helper import ModelHelper
from robotcode.robot.diagnostics.namespace import Namespace
from robotcode.robot.diagnostics.semantic_analyzer.enums import TokenKind
from robotcode.robot.diagnostics.semantic_analyzer.model import SemanticModel
from robotcode.robot.diagnostics.semantic_analyzer.nodes import KeywordCallStatement
from robotcode.robot.utils.ast import (
    FirstAndLastRealStatementFinder,
    get_node_at_position,
    get_nodes_at_position,
    get_tokens_at_position,
    iter_nodes,
    range_from_node,
    range_from_token,
)

from ...common.decorators import code_action_kinds
from .code_action_helper_mixin import (
    SHOW_DOCUMENT_SELECT_AND_RENAME_COMMAND,
    CodeActionDataBase,
    CodeActionHelperMixin,
    FindSectionsVisitor,
)
from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol  # pragma: no cover


@dataclass
class CodeActionData(CodeActionDataBase):
    diagnostics_code: Optional[Union[int, str]] = None


KEYWORD_WITH_ARGS_TEMPLATE = StringTemplate(
    """\
${name}
    [Arguments]    ${args}
    # TODO: implement keyword "${name}".
    Fail    Not Implemented
"""
)

KEYWORD_TEMPLATE = StringTemplate(
    """\
${name}
    # TODO: implement keyword "${name}".
    Fail    Not Implemented
"""
)


def _format_create_keyword_args(arg_values: Iterable[str]) -> List[str]:
    """Build the placeholder list for the new keyword's `[Arguments]` line.

    For each argument value:
    - `name=value` with a literal `name` (no variables in it) → `${name}`
    - everything else → `${argN}` (N counted across all arguments)

    Pure function so both the AST and SemanticModel paths produce
    identical output for the same set of argument values.
    """
    out: List[str] = []
    for value in arg_values:
        name, val = split_from_equals(value)
        if val is not None and not contains_variable(name, "$@&%"):
            out.append(f"${{{name}}}")
        else:
            out.append(f"${{arg{len(out) + 1}}}")
    return out


class RobotCodeActionQuickFixesProtocolPart(RobotLanguageServerProtocolPart, ModelHelper, CodeActionHelperMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

        parent.code_action.collect.add(self.collect)
        parent.code_action.resolve.add(self.resolve)

        self.parent.commands.register_all(self)

    @language_id("robotframework")
    @code_action_kinds([CodeActionKind.QUICK_FIX])
    def collect(
        self,
        sender: Any,
        document: TextDocument,
        range: Range,
        context: CodeActionContext,
    ) -> Optional[List[Union[Command, CodeAction]]]:
        result = []
        for method in iter_methods(self, lambda m: m.__name__.startswith("code_action_")):
            code_actions = method(document, range, context)
            if code_actions:
                result.extend(code_actions)

        if result:
            return sorted(result, key=lambda ca: ca.title)

        return None

    def resolve(self, sender: Any, code_action: CodeAction) -> Optional[CodeAction]:
        if code_action.data is not None and isinstance(code_action.data, Mapping):
            type = code_action.data.get("type", None)
            if type == "quickfix":
                method_name = code_action.data.get("method")
                method = next(
                    iter_methods(
                        self,
                        lambda m: m.__name__ == f"resolve_code_action_{method_name}",
                    )
                )
                method(
                    code_action,
                    data=from_dict(code_action.data, CodeActionData),
                )

        return None

    def code_action_create_keyword(
        self, document: TextDocument, range: Range, context: CodeActionContext
    ) -> Optional[List[Union[Command, CodeAction]]]:
        result: List[Union[Command, CodeAction]] = []

        if (context.only and CodeActionKind.QUICK_FIX in context.only) or context.trigger_kind in [
            CodeActionTriggerKind.INVOKED,
            CodeActionTriggerKind.AUTOMATIC,
        ]:
            namespace = self.parent.documents_cache.get_namespace(document)

            for diagnostic in (
                d
                for d in context.diagnostics
                if d.source == DIAGNOSTICS_SOURCE_NAME and d.code == Error.KEYWORD_NOT_FOUND
            ):
                resolved = self._resolve_create_keyword_target(document, diagnostic.range.start, namespace)
                if resolved is None:
                    continue
                text, lib_entry = resolved

                disabled = None
                if lib_entry is not None and lib_entry.library_doc.type == "LIBRARY":
                    disabled = CodeActionDisabledType("Keyword is from a library")

                result.append(
                    CodeAction(
                        f"Create Keyword `{text}`",
                        kind=CodeActionKind.QUICK_FIX,
                        data=as_dict(
                            CodeActionData(
                                "quickfix",
                                "create_keyword",
                                document.document_uri,
                                diagnostic.range,
                            )
                        ),
                        diagnostics=[diagnostic],
                        disabled=disabled,
                        is_preferred=True,
                    )
                )

        return result if result else None

    # ------------------------------------------------------------------
    # Tier 2 model-based resolution for the "Create Keyword" quick fix
    # ------------------------------------------------------------------

    def _resolve_create_keyword_target(
        self,
        document: TextDocument,
        position: Position,
        namespace: Namespace,
    ) -> Optional[Tuple[str, Optional[LibraryEntry]]]:
        """Resolve the bare keyword name + owning LibraryEntry for the
        "Create Keyword" quick fix at `position`.

        Returns `(text, lib_entry)` or `None` if the position isn't a
        KeywordCall / Fixture / Template AST node, or the keyword name is
        empty after stripping the BDD / namespace prefix.

        When the experimental SemanticAnalyzer is enabled the data comes
        directly from the SemanticStatement; otherwise we fall back to
        the legacy AST + `ModelHelper` path.
        """
        semantic_model = namespace.semantic_model
        if semantic_model is not None:
            return self._resolve_create_keyword_target_from_model(position, semantic_model)
        return self._resolve_create_keyword_target_legacy(document, position, namespace)

    def _resolve_create_keyword_target_from_model(
        self,
        position: Position,
        model: SemanticModel,
    ) -> Optional[Tuple[str, Optional[LibraryEntry]]]:
        """SemanticModel branch: KEYWORD SemanticToken already has the bare
        name (BDD prefix and namespace are split into their own tokens),
        and `KeywordCallStatement.lib_entry` is the pre-resolved owner."""
        stmt = model.statement_at(position.line + 1)
        if not isinstance(stmt, KeywordCallStatement):
            return None
        kw_tok = next((t for t in stmt.tokens if t.kind is TokenKind.KEYWORD), None)
        if kw_tok is None or not kw_tok.value:
            return None
        return kw_tok.value, stmt.lib_entry

    def _resolve_create_keyword_target_legacy(
        self,
        document: TextDocument,
        position: Position,
        namespace: Namespace,
    ) -> Optional[Tuple[str, Optional[LibraryEntry]]]:
        """AST + `ModelHelper` fallback (used when the experimental
        analyzer is off). Mirrors the original inline logic exactly so
        the model-path migration stays output-equivalent."""
        model = self.parent.documents_cache.get_model(document)
        node = get_node_at_position(model, position)
        if not isinstance(node, (KeywordCall, Fixture, TestTemplate, Template)):
            return None

        tokens = get_tokens_at_position(node, position)
        if not tokens:
            return None
        keyword_token = tokens[-1]

        bdd_token, token = self.split_bdd_prefix(namespace, keyword_token)
        if bdd_token is not None and token is not None:
            keyword_token = token

        lib_entry, kw_namespace = self.get_namespace_info_from_keyword_token(namespace, keyword_token)

        text = keyword_token.value
        if lib_entry and kw_namespace:
            text = text[len(kw_namespace) + 1 :].strip()
        if not text:
            return None

        return text, lib_entry

    def resolve_code_action_create_keyword(self, code_action: CodeAction, data: CodeActionData) -> Optional[CodeAction]:
        document = self.parent.documents.get(data.document_uri)
        if document is None:
            return None

        namespace = self.parent.documents_cache.get_namespace(document)

        resolved = self._resolve_create_keyword_target(document, data.range.start, namespace)
        if resolved is None:
            return None
        text, lib_entry = resolved

        # Library keywords can't be auto-created; legacy returns None here.
        if lib_entry is not None and lib_entry.library_doc.type == "LIBRARY":
            return None

        arguments = self._collect_create_keyword_arguments(document, data.range.start, namespace)

        insert_text = (
            KEYWORD_WITH_ARGS_TEMPLATE.substitute(name=text, args="    ".join(arguments))
            if arguments
            else KEYWORD_TEMPLATE.substitute(name=text)
        )

        if lib_entry is not None and lib_entry.library_doc.type == "RESOURCE" and lib_entry.library_doc.source:
            dest_document = self.parent.documents.get_or_open_document(lib_entry.library_doc.source)
        else:
            dest_document = document

        code_action.edit, select_range = self._apply_create_keyword(dest_document, insert_text)

        code_action.command = Command(
            SHOW_DOCUMENT_SELECT_AND_RENAME_COMMAND,
            SHOW_DOCUMENT_SELECT_AND_RENAME_COMMAND,
            [dest_document.document_uri, select_range, False],
        )
        return code_action

    def _collect_create_keyword_arguments(
        self,
        document: TextDocument,
        position: Position,
        namespace: Namespace,
    ) -> List[str]:
        """Build the `${name}` / `${argN}` placeholder list for the new
        keyword's `[Arguments]` line, derived from the offending call's
        ARGUMENT tokens.

        SemanticModel-based when available (iterates `stmt.tokens`),
        falls back to the AST `node.get_tokens(ARGUMENT)` walk otherwise.
        Both paths apply the same `name=value` heuristic via
        `split_from_equals`.
        """
        semantic_model = namespace.semantic_model
        if semantic_model is not None:
            stmt = semantic_model.statement_at(position.line + 1)
            if isinstance(stmt, KeywordCallStatement):
                arg_tokens = [t for t in stmt.tokens if t.kind is TokenKind.ARGUMENT]
                return _format_create_keyword_args(t.value for t in arg_tokens)
            return []

        ast_model = self.parent.documents_cache.get_model(document)
        node = get_node_at_position(ast_model, position)
        if not isinstance(node, (KeywordCall, Fixture, TestTemplate, Template)):
            return []
        return _format_create_keyword_args(cast(Token, t).value for t in node.get_tokens(Token.ARGUMENT))

    def _apply_create_keyword(self, document: TextDocument, insert_text: str) -> Tuple[WorkspaceEdit, Range]:
        model = self.parent.documents_cache.get_model(document)
        namespace = self.parent.documents_cache.get_namespace(document)

        insert_text, insert_range = self.create_insert_keyword_workspace_edit(document, model, namespace, insert_text)

        we = WorkspaceEdit(
            document_changes=[
                TextDocumentEdit(
                    OptionalVersionedTextDocumentIdentifier(str(document.uri), document.version),
                    [AnnotatedTextEdit("create_keyword", insert_range, insert_text)],
                )
            ],
            change_annotations={"create_keyword": ChangeAnnotation("Create Keyword", False)},
        )

        lines = insert_text.rstrip().splitlines()
        selection_range = insert_range.extend(start_line=len(lines) - 1, end_line=len(lines) - 1)
        selection_range.start.character = 4
        selection_range.end.character = len(lines[-1])

        return we, selection_range

    def code_action_disable_robotcode_diagnostics_for_line(
        self, document: TextDocument, range: Range, context: CodeActionContext
    ) -> Optional[List[Union[Command, CodeAction]]]:
        if (
            range.start.line == range.end.line
            and range.start.character <= range.end.character
            and (
                (context.only and CodeActionKind.QUICK_FIX in context.only)
                or context.trigger_kind
                in [
                    CodeActionTriggerKind.INVOKED,
                    CodeActionTriggerKind.AUTOMATIC,
                ]
            )
        ):
            all_diagnostics = [d for d in context.diagnostics if d.source and d.source.startswith("robotcode.")]
            if all_diagnostics:
                result = defaultdict(list)
                for diagnostics in all_diagnostics:
                    result[diagnostics.code].append(diagnostics)

                return [
                    CodeAction(
                        f"Disable '{k}' for this line",
                        kind=CodeActionKind.QUICK_FIX,
                        data=as_dict(
                            CodeActionData(
                                "quickfix",
                                "disable_robotcode_diagnostics_for_line",
                                document.document_uri,
                                range,
                                k,
                            )
                        ),
                        diagnostics=v,
                    )
                    for k, v in result.items()
                ]

        return None

    def resolve_code_action_disable_robotcode_diagnostics_for_line(
        self, code_action: CodeAction, data: CodeActionData
    ) -> Optional[CodeAction]:
        if data.range.start.line == data.range.end.line and data.range.start.character <= data.range.end.character:
            document = self.parent.documents.get(data.document_uri)
            if document is None:
                return None

            # TODO add the correct code to the diagnostics
            insert_text = "    # robotcode: ignore"

            line = document.get_lines()[data.range.start.line]
            stripped_line = line.rstrip()

            insert_range = Range(
                start=Position(data.range.start.line, len(stripped_line)),
                end=Position(data.range.start.line, len(line)),
            )

            code_action.edit = WorkspaceEdit(
                document_changes=[
                    TextDocumentEdit(
                        OptionalVersionedTextDocumentIdentifier(str(document.uri), document.version),
                        [
                            AnnotatedTextEdit(
                                "disable_robotcode_diagnostics_for_line",
                                insert_range,
                                insert_text,
                            )
                        ],
                    )
                ],
                change_annotations={
                    "disable_robotcode_diagnostics_for_line": ChangeAnnotation(
                        "Disable robotcode diagnostics for line", False
                    )
                },
            )

            return code_action

        return None

    def code_action_create_local_variable(
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
                    model = self.parent.documents_cache.get_model(document)
                    nodes = get_nodes_at_position(model, range.start)

                    if not any(n for n in nodes if isinstance(n, (Keyword, TestCase))):
                        continue

                    node = nodes[-1] if nodes else None
                    if node is None or isinstance(node, (Documentation, Fixture, Template, TestCaseName)):
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
                            data=as_dict(
                                CodeActionData(
                                    "quickfix",
                                    "create_local_variable",
                                    document.document_uri,
                                    diagnostic.range,
                                )
                            ),
                            diagnostics=[diagnostic],
                        )
                    )

        return result if result else None

    def resolve_code_action_create_local_variable(
        self, code_action: CodeAction, data: CodeActionData
    ) -> Optional[CodeAction]:
        if data.range.start.line == data.range.end.line and data.range.start.character <= data.range.end.character:
            document = self.parent.documents.get(data.document_uri)
            if document is None:
                return None

            model = self.parent.documents_cache.get_model(document)
            nodes = get_nodes_at_position(model, data.range.start)

            if not any(n for n in nodes if isinstance(n, (Keyword, TestCase))):
                return None

            node = nodes[-1] if nodes else None
            if node is None or isinstance(node, (Documentation, Fixture, Template)):
                return None

            if not isinstance(node, Statement):
                return None

            text = document.get_lines()[data.range.start.line][data.range.start.character : data.range.end.character]
            if not text:
                return None

            spaces = node.tokens[0].value if node.tokens and node.tokens[0].type == "SEPARATOR" else "    "

            insert_text = f"{spaces}${{{text}}}    Set Variable    value\n"
            node_range = range_from_node(node)
            insert_range = Range(
                start=Position(node_range.start.line, 0),
                end=Position(node_range.start.line, 0),
            )
            code_action.edit = WorkspaceEdit(
                document_changes=[
                    TextDocumentEdit(
                        OptionalVersionedTextDocumentIdentifier(str(document.uri), document.version),
                        [
                            AnnotatedTextEdit(
                                "create_local_variable",
                                insert_range,
                                insert_text,
                            )
                        ],
                    )
                ],
                change_annotations={"create_local_variable": ChangeAnnotation("Create Local variable", False)},
            )

            select_range = insert_range.extend(start_character=insert_text.rindex("value"))
            select_range.end.character = select_range.start.character + len("value")

            code_action.command = Command(
                SHOW_DOCUMENT_SELECT_AND_RENAME_COMMAND,
                SHOW_DOCUMENT_SELECT_AND_RENAME_COMMAND,
                [data.document_uri, select_range, False],
            )
            return code_action

        return None

    def code_action_create_suite_variable(
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
                            data=as_dict(
                                CodeActionData(
                                    "quickfix",
                                    "create_suite_variable",
                                    document.document_uri,
                                    diagnostic.range,
                                )
                            ),
                            diagnostics=[diagnostic],
                        )
                    )

        return result if result else None

    def resolve_code_action_create_suite_variable(
        self, code_action: CodeAction, data: CodeActionData
    ) -> Optional[CodeAction]:
        if data.range.start.line == data.range.end.line and data.range.start.character <= data.range.end.character:
            document = self.parent.documents.get(data.document_uri)
            if document is None:
                return None

            model = self.parent.documents_cache.get_model(document)
            nodes = get_nodes_at_position(model, data.range.start)

            node = nodes[-1] if nodes else None

            if node is None:
                return None

            insert_range_prefix = ""
            insert_range_suffix = ""

            if any(n for n in nodes if isinstance(n, (VariableSection))) and isinstance(node, Variable):
                node_range = range_from_node(node)
                insert_range = Range(
                    start=Position(node_range.start.line, 0),
                    end=Position(node_range.start.line, 0),
                )
            else:
                finder = FindSectionsVisitor()
                finder.visit(model)

                if finder.variable_sections:
                    section = finder.variable_sections[-1]

                    _, last_stmt = FirstAndLastRealStatementFinder.find_from(section)
                    end_lineno = last_stmt.end_lineno if last_stmt else section.end_lineno  # type: ignore
                    if end_lineno is None:
                        return None

                    insert_range = Range(
                        start=Position(end_lineno, 0),
                        end=Position(end_lineno, 0),
                    )
                else:
                    insert_range_prefix = "\n\n*** Variables ***\n"
                    if finder.setting_sections:
                        insert_range_prefix = "\n\n*** Variables ***\n"
                        insert_range_suffix = "\n\n"
                        section = finder.setting_sections[-1]

                        (
                            _,
                            last_stmt,
                        ) = FirstAndLastRealStatementFinder.find_from(section)
                        end_lineno = last_stmt.end_lineno if last_stmt else section.end_lineno  # type: ignore
                        if end_lineno is None:
                            return None

                        insert_range = Range(
                            start=Position(end_lineno, 0),
                            end=Position(end_lineno, 0),
                        )
                    else:
                        insert_range_prefix = "*** Variables ***\n"
                        insert_range_suffix = "\n\n"
                        insert_range = Range(start=Position(0, 0), end=Position(0, 0))

            lines = document.get_lines()
            text = lines[data.range.start.line][data.range.start.character : data.range.end.character]
            if not text:
                return None

            if insert_range.start.line == insert_range.end.line and insert_range.start.line >= len(lines):
                insert_range.start.line = len(lines) - 1
                insert_range.start.character = len(lines[-1])
                insert_range_prefix = "\n" + insert_range_prefix
            insert_text = insert_range_prefix + f"${{{text}}}    value\n" + insert_range_suffix

            code_action.edit = WorkspaceEdit(
                document_changes=[
                    TextDocumentEdit(
                        OptionalVersionedTextDocumentIdentifier(str(document.uri), document.version),
                        [
                            AnnotatedTextEdit(
                                "create_suite_variable",
                                insert_range,
                                insert_text,
                            )
                        ],
                    )
                ],
                change_annotations={"create_suite_variable": ChangeAnnotation("Create suite variable", False)},
            )

            splitted = insert_text.splitlines()
            start_line = next((i for i, l in enumerate(splitted) if "value" in l), 0)
            select_range = insert_range.extend(start_line=start_line, end_line=start_line)

            select_range.end.line = insert_range.start.line
            select_range.start.character = splitted[start_line].rindex("value")
            select_range.end.character = select_range.start.character + len("value")

            code_action.command = Command(
                SHOW_DOCUMENT_SELECT_AND_RENAME_COMMAND,
                SHOW_DOCUMENT_SELECT_AND_RENAME_COMMAND,
                [data.document_uri, select_range, False],
            )
            return code_action
        return None

    def code_action_add_argument(
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
                    diagnostic.range.start.line == diagnostic.range.end.line
                    text = document.get_lines()[diagnostic.range.start.line][
                        diagnostic.range.start.character : diagnostic.range.end.character
                    ]
                    if not text:
                        continue

                    model = self.parent.documents_cache.get_model(document)
                    nodes = get_nodes_at_position(model, range.start)

                    if not any(n for n in nodes if isinstance(n, Keyword)):
                        continue

                    result.append(
                        CodeAction(
                            f"Add argument `${{{text}}}`",
                            kind=CodeActionKind.QUICK_FIX,
                            data=as_dict(
                                CodeActionData(
                                    "quickfix",
                                    "add_argument",
                                    document.document_uri,
                                    diagnostic.range,
                                )
                            ),
                            diagnostics=[diagnostic],
                        )
                    )

        return result if result else None

    def resolve_code_action_add_argument(self, code_action: CodeAction, data: CodeActionData) -> Optional[CodeAction]:
        if data.range.start.line == data.range.end.line and data.range.start.character <= data.range.end.character:
            document = self.parent.documents.get(data.document_uri)
            if document is None:
                return None

            text = document.get_lines()[data.range.start.line][data.range.start.character : data.range.end.character]
            if not text:
                return None

            model = self.parent.documents_cache.get_model(document)
            nodes = get_nodes_at_position(model, data.range.start)

            keyword = next((n for n in nodes if isinstance(n, Keyword)), None)
            if keyword is None:
                return None

            arguments = next((n for n in keyword.body if isinstance(n, Arguments)), None)

            if arguments is None:
                first_stmt = next(
                    (
                        n
                        for n in iter_nodes(keyword)
                        if isinstance(n, Statement) and not isinstance(n, (KeywordName, Documentation))
                    ),
                    None,
                )

                if first_stmt is None:
                    return None

                spaces = (
                    first_stmt.tokens[0].value
                    if first_stmt is not None and first_stmt.tokens and first_stmt.tokens[0].type == "SEPARATOR"
                    else "    "
                )

                insert_text = f"{spaces}[Arguments]    ${{{text}}}=\n"
                node_range = range_from_node(first_stmt)
                insert_range = Range(
                    start=Position(node_range.start.line, 0),
                    end=Position(node_range.start.line, 0),
                )
            else:
                insert_text = f"    ${{{text}}}="
                argument_tokens = arguments.get_tokens(Token.ARGUMENT)
                if argument_tokens:
                    token_range = range_from_token(argument_tokens[-1])
                else:
                    token_range = range_from_token(arguments.get_token(Token.ARGUMENTS))
                insert_range = Range(start=token_range.end, end=token_range.end)

            code_action.edit = WorkspaceEdit(
                document_changes=[
                    TextDocumentEdit(
                        OptionalVersionedTextDocumentIdentifier(str(document.uri), document.version),
                        [AnnotatedTextEdit("add_argument", insert_range, insert_text)],
                    )
                ],
                change_annotations={"add_argument": ChangeAnnotation("Add Argument", False)},
            )

            select_range = insert_range.extend(start_character=len(insert_text))
            select_range.end.character = select_range.start.character

            code_action.command = Command(
                SHOW_DOCUMENT_SELECT_AND_RENAME_COMMAND,
                SHOW_DOCUMENT_SELECT_AND_RENAME_COMMAND,
                [data.document_uri, select_range, False],
            )
            return code_action
        return None
