from __future__ import annotations

import ast
import io
import threading
import weakref
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    Union,
    cast,
)

from robot.parsing.lexer.tokens import Token

from robotcode.core.event import event
from robotcode.core.lsp.types import MessageType
from robotcode.core.uri import Uri
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.robot.utils import get_robot_version

from ...common.decorators import language_id_filter
from ...common.parts.workspace import WorkspaceFolder
from ...common.text_document import TextDocument
from ..configuration import RobotCodeConfig, RobotConfig
from ..diagnostics.imports_manager import ImportsManager
from ..diagnostics.namespace import DocumentType, Namespace
from ..languages import Languages
from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


class UnknownFileTypeError(Exception):
    pass


class DocumentsCache(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        self._imports_managers_lock = threading.RLock()
        self._imports_managers: weakref.WeakKeyDictionary[WorkspaceFolder, ImportsManager] = weakref.WeakKeyDictionary()
        self._default_imports_manager: Optional[ImportsManager] = None
        self._workspace_languages: weakref.WeakKeyDictionary[
            WorkspaceFolder, Optional[Languages]
        ] = weakref.WeakKeyDictionary()

    def get_workspace_languages(self, document_or_uri: Union[TextDocument, Uri, str]) -> Optional[Languages]:
        if get_robot_version() < (6, 0):
            return None

        from robot.conf.languages import (
            Languages as RobotLanguages,
        )

        uri: Union[Uri, str]

        if isinstance(document_or_uri, TextDocument):
            uri = document_or_uri.uri
        else:
            uri = document_or_uri

        folder = self.parent.workspace.get_workspace_folder(uri)

        if folder is None:
            return None

        if folder in self._workspace_languages:
            return self._workspace_languages[folder]

        self._logger.debug(lambda: f"Need language config for {uri} in workspace {folder.uri}")
        config = self.parent.workspace.get_configuration(RobotConfig, folder.uri)

        languages = [str(v) for v in self.parent.profile.languages or []]
        languages += config.languages or []

        if not languages:
            self._workspace_languages[folder] = None
            return None

        result = RobotLanguages()
        for lang in languages:
            try:
                result.add_language(lang)
            except ValueError as e:
                self.parent.window.show_message(
                    f"Language configuration is not valid: {e}"
                    "\nPlease check your 'robotcode.robot.language' configuration.",
                    MessageType.ERROR,
                )

        self._workspace_languages[folder] = result

        return cast(Languages, RobotLanguages(result.languages))

    def build_languages_from_model(
        self, document: TextDocument, model: ast.AST
    ) -> Tuple[Optional[Languages], Optional[Languages]]:
        if get_robot_version() < (6, 0):
            return (None, None)

        from robot.conf.languages import (
            Languages as RobotLanguages,
        )

        # pyright: ignore[reportMissingImports]
        from robot.parsing.model.blocks import File

        workspace_langs = self.get_workspace_languages(document)

        return (
            cast(
                Languages,
                RobotLanguages(
                    [
                        *(workspace_langs.languages if workspace_langs else []),
                        *(model.languages if isinstance(model, File) else []),
                    ]
                ),
            ),
            workspace_langs,
        )

    def get_document_type(self, document: TextDocument) -> DocumentType:
        return document.get_cache(self.__get_document_type)

    def __get_document_type(self, document: TextDocument) -> DocumentType:
        path = document.uri.to_path()
        suffix = path.suffix.lower()

        if path.name == "__init__.robot":
            return DocumentType.INIT
        if suffix == ".robot":
            return DocumentType.GENERAL
        if suffix == ".resource":
            return DocumentType.RESOURCE

        return DocumentType.UNKNOWN

    def get_tokens(self, document: TextDocument, data_only: bool = False) -> List[Token]:
        if data_only:
            return document.get_cache(self.__get_tokens_data_only)
        return document.get_cache(self.__get_tokens)

    def __get_tokens_data_only(self, document: TextDocument) -> List[Token]:
        document_type = self.get_document_type(document)
        if document_type == DocumentType.INIT:
            return self.get_init_tokens(document, True)
        if document_type == DocumentType.GENERAL:
            return self.get_general_tokens(document, True)
        if document_type == DocumentType.RESOURCE:
            return self.get_resource_tokens(document, True)

        raise UnknownFileTypeError(str(document.uri))

    def __get_tokens(self, document: TextDocument) -> List[Token]:
        document_type = self.get_document_type(document)
        if document_type == DocumentType.INIT:
            return self.get_init_tokens(document)
        if document_type == DocumentType.GENERAL:
            return self.get_general_tokens(document)
        if document_type == DocumentType.RESOURCE:
            return self.get_resource_tokens(document)

        raise UnknownFileTypeError(str(document.uri))

    def get_general_tokens(self, document: TextDocument, data_only: bool = False) -> List[Token]:
        if data_only:
            return document.get_cache(self.__get_general_tokens_data_only)
        return document.get_cache(self.__get_general_tokens)

    def __internal_get_tokens(
        self,
        source: Any,
        data_only: bool = False,
        tokenize_variables: bool = False,
        lang: Any = None,
    ) -> Any:
        import robot.api

        if get_robot_version() >= (6, 0):
            return robot.api.get_tokens(
                source,
                data_only=data_only,
                tokenize_variables=tokenize_variables,
                lang=lang,
            )

        return robot.api.get_tokens(source, data_only=data_only, tokenize_variables=tokenize_variables)

    def __internal_get_resource_tokens(
        self,
        source: Any,
        data_only: bool = False,
        tokenize_variables: bool = False,
        lang: Any = None,
    ) -> Any:
        import robot.api

        if get_robot_version() >= (6, 0):
            return robot.api.get_resource_tokens(
                source,
                data_only=data_only,
                tokenize_variables=tokenize_variables,
                lang=lang,
            )

        return robot.api.get_resource_tokens(source, data_only=data_only, tokenize_variables=tokenize_variables)

    def __internal_get_init_tokens(
        self,
        source: Any,
        data_only: bool = False,
        tokenize_variables: bool = False,
        lang: Any = None,
    ) -> Any:
        import robot.api

        if get_robot_version() >= (6, 0):
            return robot.api.get_init_tokens(
                source,
                data_only=data_only,
                tokenize_variables=tokenize_variables,
                lang=lang,
            )

        return robot.api.get_init_tokens(source, data_only=data_only, tokenize_variables=tokenize_variables)

    def __get_general_tokens_data_only(self, document: TextDocument) -> List[Token]:
        lang = self.get_workspace_languages(document)

        def get(text: str) -> List[Token]:
            with io.StringIO(text) as content:
                return [e for e in self.__internal_get_tokens(content, True, lang=lang)]

        return self.__get_tokens_internal(document, get)

    def __get_general_tokens(self, document: TextDocument) -> List[Token]:
        lang = self.get_workspace_languages(document)

        def get(text: str) -> List[Token]:
            with io.StringIO(text) as content:
                return [e for e in self.__internal_get_tokens(content, lang=lang)]

        return self.__get_tokens_internal(document, get)

    def __get_tokens_internal(self, document: TextDocument, get: Callable[[str], List[Token]]) -> List[Token]:
        return get(document.text())

    def get_resource_tokens(self, document: TextDocument, data_only: bool = False) -> List[Token]:
        if data_only:
            return document.get_cache(self.__get_resource_tokens_data_only)

        return document.get_cache(self.__get_resource_tokens)

    def __get_resource_tokens_data_only(self, document: TextDocument) -> List[Token]:
        lang = self.get_workspace_languages(document)

        def get(text: str) -> List[Token]:
            with io.StringIO(text) as content:
                return [e for e in self.__internal_get_resource_tokens(content, True, lang=lang)]

        return self.__get_tokens_internal(document, get)

    def __get_resource_tokens(self, document: TextDocument) -> List[Token]:
        lang = self.get_workspace_languages(document)

        def get(text: str) -> List[Token]:
            with io.StringIO(text) as content:
                return [e for e in self.__internal_get_resource_tokens(content, lang=lang)]

        return self.__get_tokens_internal(document, get)

    def get_init_tokens(self, document: TextDocument, data_only: bool = False) -> List[Token]:
        if data_only:
            return document.get_cache(self.__get_init_tokens_data_only)
        return document.get_cache(self.__get_init_tokens)

    def __get_init_tokens_data_only(self, document: TextDocument) -> List[Token]:
        lang = self.get_workspace_languages(document)

        def get(text: str) -> List[Token]:
            with io.StringIO(text) as content:
                return [e for e in self.__internal_get_init_tokens(content, True, lang=lang)]

        return self.__get_tokens_internal(document, get)

    def __get_init_tokens(self, document: TextDocument) -> List[Token]:
        lang = self.get_workspace_languages(document)

        def get(text: str) -> List[Token]:
            with io.StringIO(text) as content:
                return [e for e in self.__internal_get_init_tokens(content, lang=lang)]

        return self.__get_tokens_internal(document, get)

    def get_model(self, document: TextDocument, data_only: bool = True) -> ast.AST:
        document_type = self.get_document_type(document)

        if document_type == DocumentType.INIT:
            return self.get_init_model(document, data_only)
        if document_type == DocumentType.GENERAL:
            return self.get_general_model(document, data_only)
        if document_type == DocumentType.RESOURCE:
            return self.get_resource_model(document, data_only)

        raise UnknownFileTypeError(f"Unknown file type '{document.uri}'.")

    def __get_model(
        self,
        document: TextDocument,
        tokens: Iterable[Any],
        document_type: DocumentType,
    ) -> ast.AST:
        from robot.parsing.parser.parser import _get_model

        def get_tokens(source: str, data_only: bool = False, lang: Any = None) -> Iterator[Token]:
            for t in tokens:
                yield t

        if get_robot_version() >= (6, 0):
            model = _get_model(get_tokens, document.uri.to_path(), False, None, None)
        else:
            model = _get_model(get_tokens, document.uri.to_path(), False, None)

        model.source = str(document.uri.to_path())
        model.model_type = document_type

        return cast(ast.AST, model)

    def get_general_model(self, document: TextDocument, data_only: bool = True) -> ast.AST:
        if data_only:
            return document.get_cache(
                self.__get_general_model_data_only,
                self.get_general_tokens(document, True),
            )
        return document.get_cache(self.__get_general_model, self.get_general_tokens(document))

    def __get_general_model_data_only(self, document: TextDocument, tokens: Iterable[Any]) -> ast.AST:
        return self.__get_model(document, tokens, DocumentType.GENERAL)

    def __get_general_model(self, document: TextDocument, tokens: Iterable[Any]) -> ast.AST:
        return self.__get_model(document, tokens, DocumentType.GENERAL)

    def get_resource_model(self, document: TextDocument, data_only: bool = True) -> ast.AST:
        if data_only:
            return document.get_cache(
                self.__get_resource_model_data_only,
                self.get_resource_tokens(document, True),
            )

        return document.get_cache(self.__get_resource_model, self.get_resource_tokens(document))

    def __get_resource_model_data_only(self, document: TextDocument, tokens: Iterable[Any]) -> ast.AST:
        return self.__get_model(document, tokens, DocumentType.RESOURCE)

    def __get_resource_model(self, document: TextDocument, tokens: Iterable[Any]) -> ast.AST:
        return self.__get_model(document, tokens, DocumentType.RESOURCE)

    def get_init_model(self, document: TextDocument, data_only: bool = True) -> ast.AST:
        if data_only:
            return document.get_cache(
                self.__get_init_model_data_only,
                self.get_init_tokens(document, True),
            )
        return document.get_cache(self.__get_init_model, self.get_init_tokens(document))

    def __get_init_model_data_only(self, document: TextDocument, tokens: Iterable[Any]) -> ast.AST:
        return self.__get_model(document, tokens, DocumentType.INIT)

    def __get_init_model(self, document: TextDocument, tokens: Iterable[Any]) -> ast.AST:
        return self.__get_model(document, tokens, DocumentType.INIT)

    def get_namespace(self, document: TextDocument) -> Namespace:
        return document.get_cache(self.__get_namespace)

    def __get_namespace(self, document: TextDocument) -> Namespace:
        return self.__get_namespace_for_document_type(document, None)

    def get_resource_namespace(self, document: TextDocument) -> Namespace:
        return document.get_cache(self.__get_resource_namespace)

    def __get_resource_namespace(self, document: TextDocument) -> Namespace:
        return self.__get_namespace_for_document_type(document, DocumentType.RESOURCE)

    def get_init_namespace(self, document: TextDocument) -> Namespace:
        return document.get_cache(self.__get_init_namespace)

    def __get_init_namespace(self, document: TextDocument) -> Namespace:
        return self.__get_namespace_for_document_type(document, DocumentType.INIT)

    def get_general_namespace(self, document: TextDocument) -> Namespace:
        return document.get_cache(self.__get_general_namespace)

    def __get_general_namespace(self, document: TextDocument) -> Namespace:
        return self.__get_namespace_for_document_type(document, DocumentType.GENERAL)

    @event
    def namespace_invalidated(sender, namespace: Namespace) -> None:
        ...

    def __invalidate_namespace(self, sender: Namespace) -> None:
        document = sender.document
        if document is not None:
            document.invalidate_cache()

            self.namespace_invalidated(self, sender, callback_filter=language_id_filter(document))

    def __document_cache_invalidated(self, sender: TextDocument) -> None:
        namespace: Optional[Namespace] = sender.get_cache_value(self.__get_namespace)
        if namespace is not None:
            self.namespace_invalidated(self, namespace, callback_filter=language_id_filter(sender))

    def __get_namespace_for_document_type(
        self, document: TextDocument, document_type: Optional[DocumentType]
    ) -> Namespace:
        if document_type is not None and document_type == DocumentType.INIT:
            model = self.get_init_model(document)
        elif document_type is not None and document_type == DocumentType.RESOURCE:
            model = self.get_resource_model(document)
        elif document_type is not None and document_type == DocumentType.GENERAL:
            model = self.get_general_model(document)
        else:
            model = self.get_model(document)

        imports_manager = self.get_imports_manager(document)

        languages, workspace_languages = self.build_languages_from_model(document, model)

        result = Namespace(
            imports_manager,
            model,
            str(document.uri.to_path()),
            document,
            document_type,
            languages,
            workspace_languages,
        )
        result.has_invalidated.add(self.__invalidate_namespace)
        result.has_imports_changed.add(self.__invalidate_namespace)

        document.cache_invalidated.add(self.__document_cache_invalidated)

        return result

    def default_imports_manager(self) -> ImportsManager:
        with self._imports_managers_lock:
            if self._default_imports_manager is None:
                self._default_imports_manager = ImportsManager(
                    self.parent,
                    Uri(self.parent.workspace.root_uri or "."),
                    RobotCodeConfig(),
                )

            return self._default_imports_manager

    def get_imports_manager(self, document: TextDocument) -> ImportsManager:
        return self.get_imports_manager_for_uri(document.uri)

    def get_imports_manager_for_uri(self, uri: Uri) -> ImportsManager:
        return self.get_imports_manager_for_workspace_folder(self.parent.workspace.get_workspace_folder(uri))

    def get_imports_manager_for_workspace_folder(self, folder: Optional[WorkspaceFolder]) -> ImportsManager:
        if folder is None:
            if len(self.parent.workspace.workspace_folders) == 1:
                folder = self.parent.workspace.workspace_folders[0]
            else:
                return self.default_imports_manager()

        with self._imports_managers_lock:
            if folder not in self._imports_managers:
                config = self.parent.workspace.get_configuration(RobotCodeConfig, folder.uri)

                self._imports_managers[folder] = ImportsManager(self.parent, folder.uri, config)

            return self._imports_managers[folder]
