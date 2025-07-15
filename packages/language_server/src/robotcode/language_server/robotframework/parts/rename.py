import ast
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

from robotcode.core.concurrent import check_current_task_canceled
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
    Range,
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

    @language_id("robotframework")
    @_logger.call
    def collect(
        self, sender: Any, document: TextDocument, position: Position, new_name: str
    ) -> Optional[WorkspaceEdit]:
        result = self._rename_variable(document, position, new_name)
        if result:
            return result

        result = self._rename_keyword(document, position, new_name)
        if result:
            return result

        return None

    @language_id("robotframework")
    @_logger.call
    def collect_prepare(self, sender: Any, document: TextDocument, position: Position) -> Optional[PrepareRenameResult]:
        result = self._prepare_rename_variable(document, position)
        if result:
            return result

        result = self._prepare_rename_keyword(document, position)
        if result:
            return result

        return None

    def _prepare_rename_variable(self, document: TextDocument, position: Position) -> Optional[PrepareRenameResult]:
        result = self._find_variable_definition_on_pos(document, position)
        if result is not None:
            var, found_range = result

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
                self.parent.window.show_message(
                    "You are about to rename an environment variable. "
                    "Only references are renamed and you have to rename the variable definition yourself."
                )

            return PrepareRenameResultType1(found_range, document.get_text(found_range))

        return None

    def _rename_variable(self, document: TextDocument, position: Position, new_name: str) -> Optional[WorkspaceEdit]:
        if "  " in new_name or "\t" in new_name:
            raise CantRenameError(
                "Variable names cannot contain more then one spaces or tabs. "
                "Please use only one space or underscores instead.",
            )

        result = self._find_variable_definition_on_pos(document, position)

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

    def _find_variable_definition_on_pos(
        self, document: TextDocument, position: Position
    ) -> Optional[Tuple[VariableDefinition, Range]]:
        namespace = self.parent.documents_cache.get_namespace(document)

        all_variable_refs = namespace.get_variable_references()
        if all_variable_refs:
            for variable, var_refs in all_variable_refs.items():
                check_current_task_canceled()

                found_range = (
                    variable.name_range
                    if variable.source == namespace.source and position.is_in_range(variable.name_range, False)
                    else next(
                        (r.range for r in var_refs if position.is_in_range(r.range)),
                        None,
                    )
                )

                if found_range is not None:
                    return variable, found_range
        return None

    def _prepare_rename_keyword(self, document: TextDocument, position: Position) -> Optional[PrepareRenameResult]:
        result = self._find_keyword_definition_on_pos(document, position)
        if result is not None:
            kw_doc, found_range = result

            if kw_doc.is_embedded:
                raise CantRenameError("Renaming of keywords with embedded parameters is not supported.")

            if kw_doc.is_library_keyword:
                self.parent.window.show_message(
                    "You are about to rename a library keyword. "
                    "Only references are renamed and you have to rename the keyword definition yourself."
                )

            return PrepareRenameResultType1(found_range, document.get_text(found_range))

        return None

    def _rename_keyword(self, document: TextDocument, position: Position, new_name: str) -> Optional[WorkspaceEdit]:
        if "  " in new_name or "\t" in new_name:
            raise CantRenameError(
                "Keyword names cannot contain more then one spaces or tabs. "
                "Please use only one space or underscores instead.",
            )

        result = self._find_keyword_definition_on_pos(document, position)
        if result is not None:
            kw_doc, _ = result

            references = self.parent.robot_references.find_keyword_references(
                document,
                kw_doc,
                include_declaration=kw_doc.is_resource_keyword,
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

    def _find_keyword_definition_on_pos(
        self, document: TextDocument, position: Position
    ) -> Optional[Tuple[KeywordDoc, Range]]:
        namespace = self.parent.documents_cache.get_namespace(document)

        all_refs = namespace.get_keyword_references()
        if all_refs:
            for keyword, kw_refs in all_refs.items():
                check_current_task_canceled()

                found_range = (
                    keyword.name_range
                    if keyword.source == namespace.source and position.is_in_range(keyword.name_range, False)
                    else next(
                        (r.range for r in kw_refs if position.is_in_range(r.range)),
                        None,
                    )
                )

                if found_range is not None:
                    return keyword, found_range
        return None

    # TODO: rename tags
    # TODO: rename resource files and libraries
