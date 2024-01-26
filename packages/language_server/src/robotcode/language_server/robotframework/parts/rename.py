import ast
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from robot.parsing.lexer.tokens import Token
from robot.parsing.model.statements import Statement

from robotcode.core.language import language_id
from robotcode.core.lsp.types import (
    AnnotatedTextEdit,
    ChangeAnnotation,
    CreateFile,
    DeleteFile,
    OptionalVersionedTextDocumentIdentifier,
    Position,
    PrepareRenameResult,
    PrepareRenameResultType1,
    RenameFile,
    TextDocumentEdit,
    WorkspaceEdit,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.robot.diagnostics.entities import (
    VariableDefinition,
    VariableDefinitionType,
)
from robotcode.robot.diagnostics.library_doc import KeywordDoc
from robotcode.robot.diagnostics.model_helper import ModelHelper
from robotcode.robot.utils.ast import (
    get_nodes_at_position,
    get_tokens_at_position,
    range_from_token,
)

from ...common.parts.rename import CantRenameError
from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


_RenameMethod = Callable[[ast.AST, TextDocument, Position, str], Optional[WorkspaceEdit]]
_PrepareRenameMethod = Callable[[ast.AST, TextDocument, Position], Optional[PrepareRenameResult]]

_T = TypeVar("_T", bound=Callable[..., Any])


class RobotRenameProtocolPart(RobotLanguageServerProtocolPart, ModelHelper):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

        parent.rename.collect.add(self.collect)
        parent.rename.collect_prepare.add(self.collect_prepare)

    def _find_method(self, cls: Type[Any], prefix: str) -> Optional[_T]:
        if cls is ast.AST:
            return None
        method_name = prefix + "_" + cls.__name__
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            if callable(method):
                return cast(_T, method)
        for base in cls.__bases__:
            method = self._find_method(base, prefix)
            if method:
                return cast(_T, method)
        return None

    @language_id("robotframework")
    @_logger.call
    def collect(
        self,
        sender: Any,
        document: TextDocument,
        position: Position,
        new_name: str,
    ) -> Optional[WorkspaceEdit]:
        result_nodes = get_nodes_at_position(
            self.parent.documents_cache.get_model(document),
            position,
            include_end=True,
        )

        if not result_nodes:
            return None

        result_node = result_nodes[-1]

        result = self._rename_default(result_nodes, document, position, new_name)
        if result:
            return result

        method: Optional[_RenameMethod] = self._find_method(type(result_node), "rename")
        if method is not None:
            result = method(result_node, document, position, new_name)
            if result is not None:
                return result

        return None

    @language_id("robotframework")
    @_logger.call
    def collect_prepare(self, sender: Any, document: TextDocument, position: Position) -> Optional[PrepareRenameResult]:
        result_nodes = get_nodes_at_position(
            self.parent.documents_cache.get_model(document),
            position,
            include_end=True,
        )

        if not result_nodes:
            return None

        result_node = result_nodes[-1]

        result = self._prepare_rename_default(result_nodes, document, position)
        if result:
            return result

        method: Optional[_PrepareRenameMethod] = self._find_method(type(result_node), "prepare_rename")
        if method is not None:
            result = method(result_node, document, position)
            if result is not None:
                return result

        return None

    def _prepare_rename_default(
        self, nodes: List[ast.AST], document: TextDocument, position: Position
    ) -> Optional[PrepareRenameResult]:
        result = self._find_default(nodes, document, position)
        if result is not None:
            var, token = result

            if var.type == VariableDefinitionType.BUILTIN_VARIABLE:
                self.parent.window.show_message("You cannot rename a builtin variable, only references are renamed.")

            elif var.type == VariableDefinitionType.IMPORTED_VARIABLE:
                self.parent.window.show_message(
                    "You are about to rename an imported variable. "
                    "Only references are renamed and you have to rename the variable definition yourself."
                )
            elif var.type == VariableDefinitionType.COMMAND_LINE_VARIABLE:
                self.parent.window.show_message(
                    "You are about to rename a variable defined at commandline. "
                    "Only references are renamed and you have to rename the variable definition yourself."
                )
            elif var.type == VariableDefinitionType.ENVIRONMENT_VARIABLE:
                token.value, _, _ = token.value.partition("=")
                self.parent.window.show_message(
                    "You are about to rename an environment variable. "
                    "Only references are renamed and you have to rename the variable definition yourself."
                )

            return PrepareRenameResultType1(range_from_token(token), token.value)

        return None

    def _rename_default(
        self,
        nodes: List[ast.AST],
        document: TextDocument,
        position: Position,
        new_name: str,
    ) -> Optional[WorkspaceEdit]:
        result = self._find_default(nodes, document, position)

        if result is not None:
            var, _ = result

            references = self.parent.robot_references.find_variable_references(
                document,
                var,
                include_declaration=var.type
                in [
                    VariableDefinitionType.VARIABLE,
                    VariableDefinitionType.ARGUMENT,
                    VariableDefinitionType.LOCAL_VARIABLE,
                ],
            )
            changes: List[Union[TextDocumentEdit, CreateFile, RenameFile, DeleteFile]] = []

            for reference in references:
                changes.append(
                    TextDocumentEdit(
                        OptionalVersionedTextDocumentIdentifier(reference.uri, None),
                        [AnnotatedTextEdit("rename_variable", reference.range, new_name)],
                    )
                )

            return WorkspaceEdit(
                document_changes=changes,
                change_annotations={"rename_variable": ChangeAnnotation("Rename Variable", False)},
            )

        return None

    def _find_default(
        self, nodes: List[ast.AST], document: TextDocument, position: Position
    ) -> Optional[Tuple[VariableDefinition, Token]]:
        from robot.parsing.lexer.tokens import Token as RobotToken

        namespace = self.parent.documents_cache.get_namespace(document)

        if not nodes:
            return None

        node = nodes[-1]

        if not isinstance(node, Statement):
            return None

        tokens = get_tokens_at_position(node, position)

        token_and_var: Optional[Tuple[VariableDefinition, Token]] = None

        for token in tokens:
            token_and_var = next(
                (
                    (var, var_token)
                    for var_token, var in self.iter_variables_from_token(token, namespace, nodes, position)
                    if position in range_from_token(var_token)
                ),
                None,
            )

        if (
            token_and_var is None
            and isinstance(node, self.get_expression_statement_types())
            and (token := node.get_token(RobotToken.ARGUMENT)) is not None
            and position in range_from_token(token)
        ):
            token_and_var = next(
                (
                    (var, var_token)
                    for var_token, var in self.iter_expression_variables_from_token(token, namespace, nodes, position)
                    if position in range_from_token(var_token)
                ),
                None,
            )

        return token_and_var

    def _prepare_rename_keyword(self, result: Optional[Tuple[KeywordDoc, Token]]) -> Optional[PrepareRenameResult]:
        if result is not None:
            kw_doc, token = result

            if kw_doc.is_embedded:
                raise CantRenameError("Renaming of keywords with embedded parameters is not supported.")

            if kw_doc.is_library_keyword:
                self.parent.window.show_message(
                    "You are about to rename a library keyword. "
                    "Only references are renamed and you have to rename the keyword definition yourself."
                )

            return PrepareRenameResultType1(range_from_token(token), token.value)

        return None

    def _rename_keyword(
        self,
        document: TextDocument,
        new_name: str,
        result: Optional[Tuple[KeywordDoc, Token]],
    ) -> Optional[WorkspaceEdit]:
        if result is not None:
            kw_doc, _ = result

            references = self.parent.robot_references.find_keyword_references(
                document, kw_doc, include_declaration=kw_doc.is_resource_keyword
            )
            changes: List[Union[TextDocumentEdit, CreateFile, RenameFile, DeleteFile]] = []

            for reference in references:
                changes.append(
                    TextDocumentEdit(
                        OptionalVersionedTextDocumentIdentifier(reference.uri, None),
                        [AnnotatedTextEdit("rename_keyword", reference.range, new_name)],
                    )
                )

            return WorkspaceEdit(
                document_changes=changes,
                change_annotations={"rename_keyword": ChangeAnnotation("Rename Keyword", False)},
            )

        return None

    def prepare_rename_KeywordCall(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[PrepareRenameResult]:
        return self._prepare_rename_keyword(self._find_KeywordCall(node, document, position))

    def rename_KeywordCall(  # noqa: N802
        self,
        node: ast.AST,
        document: TextDocument,
        position: Position,
        new_name: str,
    ) -> Optional[WorkspaceEdit]:
        return self._rename_keyword(document, new_name, self._find_KeywordCall(node, document, position))

    def _find_KeywordCall(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[Tuple[KeywordDoc, Token]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import KeywordCall

        namespace = self.parent.documents_cache.get_namespace(document)

        kw_node = cast(KeywordCall, node)
        result = self.get_keyworddoc_and_token_from_position(
            kw_node.keyword,
            cast(Token, kw_node.get_token(RobotToken.KEYWORD)),
            [cast(Token, t) for t in kw_node.get_tokens(RobotToken.ARGUMENT)],
            namespace,
            position,
        )

        if result is not None:
            keyword_doc, keyword_token = result

            if (
                namespace.find_keyword(
                    keyword_token.value,
                    raise_keyword_error=False,
                    handle_bdd_style=False,
                )
                is None
            ):
                keyword_token = self.strip_bdd_prefix(namespace, keyword_token)

            (
                lib_entry,
                kw_namespace,
            ) = self.get_namespace_info_from_keyword_token(namespace, keyword_token)

            kw_range = range_from_token(keyword_token)

            if lib_entry and kw_namespace:
                r = range_from_token(keyword_token)
                r.end.character = r.start.character + len(kw_namespace)
                kw_range.start.character = r.end.character + 1
                if position in r:
                    # TODO namespaces
                    return None
            if (
                position in kw_range
                and keyword_doc is not None
                and not keyword_doc.is_error_handler
                and keyword_doc.source
            ):
                return (
                    keyword_doc,
                    (
                        RobotToken(
                            keyword_token.type,
                            keyword_token.value[len(kw_namespace) + 1 :],
                            keyword_token.lineno,
                            keyword_token.col_offset + len(kw_namespace) + 1,
                            keyword_token.error,
                        )
                        if lib_entry and kw_namespace
                        else keyword_token
                    ),
                )

        return None

    def prepare_rename_KeywordName(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[PrepareRenameResult]:
        return self._prepare_rename_keyword(self._find_KeywordName(node, document, position))

    def rename_KeywordName(  # noqa: N802
        self,
        node: ast.AST,
        document: TextDocument,
        position: Position,
        new_name: str,
    ) -> Optional[WorkspaceEdit]:
        return self._rename_keyword(document, new_name, self._find_KeywordName(node, document, position))

    def _find_KeywordName(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[Tuple[KeywordDoc, Token]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import KeywordName

        namespace = self.parent.documents_cache.get_namespace(document)

        kw_node = cast(KeywordName, node)

        name_token = cast(RobotToken, kw_node.get_token(RobotToken.KEYWORD_NAME))

        if not name_token:
            return None

        doc = namespace.get_library_doc()
        if doc is not None:
            keyword = next(
                (v for v in doc.keywords.keywords if v.name == name_token.value and v.line_no == kw_node.lineno),
                None,
            )

            if keyword is not None and keyword.source and not keyword.is_error_handler:
                return keyword, name_token

        return None

    def prepare_rename_Fixture(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[PrepareRenameResult]:
        return self._prepare_rename_keyword(self._find_Fixture(node, document, position))

    def rename_Fixture(  # noqa: N802
        self,
        node: ast.AST,
        document: TextDocument,
        position: Position,
        new_name: str,
    ) -> Optional[WorkspaceEdit]:
        return self._rename_keyword(document, new_name, self._find_Fixture(node, document, position))

    def _find_Fixture(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[Tuple[KeywordDoc, Token]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Fixture

        namespace = self.parent.documents_cache.get_namespace(document)

        fixture_node = cast(Fixture, node)

        name_token = cast(Token, fixture_node.get_token(RobotToken.NAME))
        if name_token is None or name_token.value is None or name_token.value.upper() in ("", "NONE"):
            return None

        result = self.get_keyworddoc_and_token_from_position(
            fixture_node.name,
            name_token,
            [cast(Token, t) for t in fixture_node.get_tokens(RobotToken.ARGUMENT)],
            namespace,
            position,
        )

        if result is not None:
            keyword_doc, keyword_token = result

            if (
                namespace.find_keyword(
                    keyword_token.value,
                    raise_keyword_error=False,
                    handle_bdd_style=False,
                )
                is None
            ):
                keyword_token = self.strip_bdd_prefix(namespace, keyword_token)

            (
                lib_entry,
                kw_namespace,
            ) = self.get_namespace_info_from_keyword_token(namespace, keyword_token)

            kw_range = range_from_token(keyword_token)

            if lib_entry and kw_namespace:
                r = range_from_token(keyword_token)
                r.end.character = r.start.character + len(kw_namespace)
                kw_range.start.character = r.end.character + 1
                if position in r:
                    # TODO namespaces
                    return None

            if position in kw_range and keyword_doc is not None and not keyword_doc.is_error_handler:
                return (
                    keyword_doc,
                    (
                        RobotToken(
                            keyword_token.type,
                            keyword_token.value[len(kw_namespace) + 1 :],
                            keyword_token.lineno,
                            keyword_token.col_offset + len(kw_namespace) + 1,
                            keyword_token.error,
                        )
                        if lib_entry and kw_namespace
                        else keyword_token
                    ),
                )

        return None

    def _find_Template_or_TestTemplate(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[Tuple[KeywordDoc, Token]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Template, TestTemplate

        template_node = cast(Union[Template, TestTemplate], node)
        if template_node.value:
            keyword_token = cast(RobotToken, template_node.get_token(RobotToken.NAME))
            if keyword_token is None or keyword_token.value is None or keyword_token.value.upper() in ("", "NONE"):
                return None

            namespace = self.parent.documents_cache.get_namespace(document)

            if (
                namespace.find_keyword(
                    keyword_token.value,
                    raise_keyword_error=False,
                    handle_bdd_style=False,
                )
                is None
            ):
                keyword_token = self.strip_bdd_prefix(namespace, keyword_token)

            if position.is_in_range(range_from_token(keyword_token), False):
                keyword_doc = namespace.find_keyword(template_node.value)

                if keyword_doc is not None:
                    (
                        lib_entry,
                        kw_namespace,
                    ) = self.get_namespace_info_from_keyword_token(namespace, keyword_token)

                    kw_range = range_from_token(keyword_token)

                    if lib_entry and kw_namespace:
                        r = range_from_token(keyword_token)
                        r.end.character = r.start.character + len(kw_namespace)
                        kw_range.start.character = r.end.character + 1
                        if position in r:
                            # TODO namespaces
                            return None

                    if not keyword_doc.is_error_handler:
                        return (
                            keyword_doc,
                            (
                                RobotToken(
                                    keyword_token.type,
                                    keyword_token.value[len(kw_namespace) + 1 :],
                                    keyword_token.lineno,
                                    keyword_token.col_offset + len(kw_namespace) + 1,
                                    keyword_token.error,
                                )
                                if lib_entry and kw_namespace
                                else keyword_token
                            ),
                        )
        return None

    def prepare_rename_TestTemplate(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[PrepareRenameResult]:
        return self._prepare_rename_keyword(self._find_Template_or_TestTemplate(node, document, position))

    def rename_TestTemplate(  # noqa: N802
        self,
        node: ast.AST,
        document: TextDocument,
        position: Position,
        new_name: str,
    ) -> Optional[WorkspaceEdit]:
        return self._rename_keyword(
            document,
            new_name,
            self._find_Template_or_TestTemplate(node, document, position),
        )

    def prepare_rename_Template(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[PrepareRenameResult]:
        return self._prepare_rename_keyword(self._find_Template_or_TestTemplate(node, document, position))

    def rename_Template(  # noqa: N802
        self,
        node: ast.AST,
        document: TextDocument,
        position: Position,
        new_name: str,
    ) -> Optional[WorkspaceEdit]:
        return self._rename_keyword(
            document,
            new_name,
            self._find_Template_or_TestTemplate(node, document, position),
        )

    def _prepare_rename_tags(
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[PrepareRenameResult]:
        from robot.parsing.lexer.tokens import Token as RobotToken

        tokens = get_tokens_at_position(cast(Statement, node), position)
        if not tokens:
            return None

        token = tokens[-1]

        if token.type == RobotToken.ARGUMENT and token.value:
            return PrepareRenameResultType1(range_from_token(token), token.value)

        return None

    def prepare_rename_ForceTags(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[PrepareRenameResult]:
        return self._prepare_rename_tags(node, document, position)

    def prepare_rename_DefaultTags(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[PrepareRenameResult]:
        return self._prepare_rename_tags(node, document, position)

    def prepare_rename_Tags(  # noqa: N802
        self, node: ast.AST, document: TextDocument, position: Position
    ) -> Optional[PrepareRenameResult]:
        return self._prepare_rename_tags(node, document, position)

    def _rename_tags(
        self,
        node: ast.AST,
        document: TextDocument,
        position: Position,
        new_name: str,
    ) -> Optional[WorkspaceEdit]:
        from robot.parsing.lexer.tokens import Token as RobotToken

        tokens = get_tokens_at_position(cast(Statement, node), position)
        if not tokens:
            return None

        token = tokens[-1]

        if token.type == RobotToken.ARGUMENT and token.value:
            references = self.parent.robot_references.find_tag_references(document, token.value)

            changes: List[Union[TextDocumentEdit, CreateFile, RenameFile, DeleteFile]] = []

            for reference in references:
                changes.append(
                    TextDocumentEdit(
                        OptionalVersionedTextDocumentIdentifier(reference.uri, None),
                        [AnnotatedTextEdit("rename_tag", reference.range, new_name)],
                    )
                )

            return WorkspaceEdit(
                document_changes=changes,
                change_annotations={"rename_keyword": ChangeAnnotation("Rename Tag", False)},
            )

        return None

    def rename_ForceTags(  # noqa: N802
        self,
        node: ast.AST,
        document: TextDocument,
        position: Position,
        new_name: str,
    ) -> Optional[WorkspaceEdit]:
        return self._rename_tags(node, document, position, new_name)

    def rename_DefaultTags(  # noqa: N802
        self,
        node: ast.AST,
        document: TextDocument,
        position: Position,
        new_name: str,
    ) -> Optional[WorkspaceEdit]:
        return self._rename_tags(node, document, position, new_name)

    def rename_Tags(  # noqa: N802
        self,
        node: ast.AST,
        document: TextDocument,
        position: Position,
        new_name: str,
    ) -> Optional[WorkspaceEdit]:
        return self._rename_tags(node, document, position, new_name)
