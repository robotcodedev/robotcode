from __future__ import annotations

import ast
import io
import weakref
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generator,
    Iterable,
    List,
    Optional,
    Tuple,
    Union,
    cast,
)

from ....utils.async_tools import Lock, async_tasking_event, check_canceled_sync
from ....utils.uri import Uri
from ...common.decorators import language_id_filter
from ...common.lsp_types import MessageType
from ...common.parts.workspace import WorkspaceFolder
from ...common.text_document import TextDocument
from ..configuration import RobotCodeConfig, RobotConfig
from ..diagnostics.imports_manager import ImportsManager
from ..diagnostics.namespace import DocumentType, Namespace
from ..utils.ast_utils import Token
from ..utils.version import get_robot_version

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from ..languages import Languages
from .protocol_part import RobotLanguageServerProtocolPart


class UnknownFileTypeError(Exception):
    pass


class DocumentsCache(RobotLanguageServerProtocolPart):
    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        self._imports_managers_lock = Lock()
        self._imports_managers: weakref.WeakKeyDictionary[WorkspaceFolder, ImportsManager] = weakref.WeakKeyDictionary()
        self._default_imports_manager: Optional[ImportsManager] = None
        self._workspace_languages: weakref.WeakKeyDictionary[WorkspaceFolder, Languages] = weakref.WeakKeyDictionary()

    async def get_workspace_languages(self, document_or_uri: Union[TextDocument, Uri, str]) -> Optional[Languages]:
        if get_robot_version() < (6, 0):
            return None

        from robot.conf.languages import (
            Languages as RobotLanguages,  # pyright: reportMissingImports=false
        )

        uri: Union[Uri, str]

        if isinstance(document_or_uri, TextDocument):
            uri = document_or_uri.uri
        else:
            uri = document_or_uri

        folder = self.parent.workspace.get_workspace_folder(uri)
        if folder is None:
            return None

        result = self._workspace_languages.get(folder, None)
        if result is None:
            config = await self.parent.workspace.get_configuration(RobotConfig, folder.uri)

            languages = config.languages

            if isinstance(languages, List) and len(languages) == 0:
                languages = None
            if languages is None:
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

    async def build_languages_from_model(
        self, document: TextDocument, model: ast.AST
    ) -> Tuple[Optional[Languages], Optional[Languages]]:
        if get_robot_version() < (6, 0):
            return (None, None)

        from robot.conf.languages import Languages as RobotLanguages
        from robot.parsing.model.blocks import File

        workspace_langs = await self.get_workspace_languages(document)

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

    async def get_document_type(self, document: TextDocument) -> DocumentType:
        return await document.get_cache(self.__get_document_type)

    async def __get_document_type(self, document: TextDocument) -> DocumentType:
        path = document.uri.to_path()
        suffix = path.suffix.lower()

        if path.name == "__init__.robot":
            return DocumentType.INIT
        elif suffix == ".robot":
            return DocumentType.GENERAL
        elif suffix == ".resource":
            return DocumentType.RESOURCE
        else:
            return DocumentType.UNKNOWN

    async def get_tokens(self, document: TextDocument, data_only: bool = False) -> List[Token]:
        if data_only:
            return await document.get_cache(self.__get_tokens_data_only)
        return await document.get_cache(self.__get_tokens)

    async def __get_tokens_data_only(self, document: TextDocument) -> List[Token]:
        document_type = await self.get_document_type(document)
        if document_type == DocumentType.INIT:
            return await self.get_init_tokens(document, True)
        elif document_type == DocumentType.GENERAL:
            return await self.get_general_tokens(document, True)
        elif document_type == DocumentType.RESOURCE:
            return await self.get_resource_tokens(document, True)
        else:
            raise UnknownFileTypeError(str(document.uri))

    async def __get_tokens(self, document: TextDocument) -> List[Token]:
        document_type = await self.get_document_type(document)
        if document_type == DocumentType.INIT:
            return await self.get_init_tokens(document)
        elif document_type == DocumentType.GENERAL:
            return await self.get_general_tokens(document)
        elif document_type == DocumentType.RESOURCE:
            return await self.get_resource_tokens(document)
        else:
            raise UnknownFileTypeError(str(document.uri))

    async def get_general_tokens(self, document: TextDocument, data_only: bool = False) -> List[Token]:
        if data_only:
            return await document.get_cache(self.__get_general_tokens_data_only)
        return await document.get_cache(self.__get_general_tokens)

    def __internal_get_tokens(
        self, source: Any, data_only: bool = False, tokenize_variables: bool = False, lang: Any = None
    ) -> Any:
        import robot.api

        if get_robot_version() >= (6, 0):
            return robot.api.get_tokens(source, data_only=data_only, tokenize_variables=tokenize_variables, lang=lang)
        else:
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
                source, data_only=data_only, tokenize_variables=tokenize_variables, lang=lang
            )
        else:
            return robot.api.get_resource_tokens(source, data_only=data_only, tokenize_variables=tokenize_variables)

    def __internal_get_init_tokens(
        self, source: Any, data_only: bool = False, tokenize_variables: bool = False, lang: Any = None
    ) -> Any:
        import robot.api

        if get_robot_version() >= (6, 0):
            return robot.api.get_init_tokens(
                source, data_only=data_only, tokenize_variables=tokenize_variables, lang=lang
            )
        else:
            return robot.api.get_init_tokens(source, data_only=data_only, tokenize_variables=tokenize_variables)

    async def __get_general_tokens_data_only(self, document: TextDocument) -> List[Token]:
        lang = await self.get_workspace_languages(document)

        def get(text: str) -> List[Token]:
            with io.StringIO(text) as content:
                return [e for e in self.__internal_get_tokens(content, True, lang=lang) if check_canceled_sync()]

        return await self.__get_tokens_internal(document, get)

    async def __get_general_tokens(self, document: TextDocument) -> List[Token]:
        lang = await self.get_workspace_languages(document)

        def get(text: str) -> List[Token]:
            with io.StringIO(text) as content:
                return [e for e in self.__internal_get_tokens(content, lang=lang) if check_canceled_sync()]

        return await self.__get_tokens_internal(document, get)

    async def __get_tokens_internal(
        self,
        document: TextDocument,
        get: Callable[[str], List[Token]],
    ) -> List[Token]:

        return get(document.text())

    async def get_resource_tokens(self, document: TextDocument, data_only: bool = False) -> List[Token]:
        if data_only:
            return await document.get_cache(self.__get_resource_tokens_data_only)

        return await document.get_cache(self.__get_resource_tokens)

    async def __get_resource_tokens_data_only(self, document: TextDocument) -> List[Token]:
        lang = await self.get_workspace_languages(document)

        def get(text: str) -> List[Token]:
            with io.StringIO(text) as content:
                return [
                    e for e in self.__internal_get_resource_tokens(content, True, lang=lang) if check_canceled_sync()
                ]

        return await self.__get_tokens_internal(document, get)

    async def __get_resource_tokens(self, document: TextDocument) -> List[Token]:
        lang = await self.get_workspace_languages(document)

        def get(text: str) -> List[Token]:
            with io.StringIO(text) as content:
                return [e for e in self.__internal_get_resource_tokens(content, lang=lang) if check_canceled_sync()]

        return await self.__get_tokens_internal(document, get)

    async def get_init_tokens(self, document: TextDocument, data_only: bool = False) -> List[Token]:
        if data_only:
            return await document.get_cache(self.__get_init_tokens_data_only)
        return await document.get_cache(self.__get_init_tokens)

    async def __get_init_tokens_data_only(self, document: TextDocument) -> List[Token]:
        lang = await self.get_workspace_languages(document)

        def get(text: str) -> List[Token]:
            with io.StringIO(text) as content:
                return [e for e in self.__internal_get_init_tokens(content, True, lang=lang) if check_canceled_sync()]

        return await self.__get_tokens_internal(document, get)

    async def __get_init_tokens(self, document: TextDocument) -> List[Token]:
        lang = await self.get_workspace_languages(document)

        def get(text: str) -> List[Token]:
            with io.StringIO(text) as content:
                return [e for e in self.__internal_get_init_tokens(content, lang=lang) if check_canceled_sync()]

        return await self.__get_tokens_internal(document, get)

    async def get_model(self, document: TextDocument, data_only: bool = True) -> ast.AST:
        document_type = await self.get_document_type(document)

        if document_type == DocumentType.INIT:
            return await self.get_init_model(document, data_only)
        if document_type == DocumentType.GENERAL:
            return await self.get_general_model(document, data_only)
        if document_type == DocumentType.RESOURCE:
            return await self.get_resource_model(document, data_only)
        else:
            raise UnknownFileTypeError(f"Unknown file type '{document.uri}'.")

    def __get_model(self, document: TextDocument, tokens: Iterable[Any], document_type: DocumentType) -> ast.AST:
        from robot.parsing.lexer import Token
        from robot.parsing.parser.parser import _get_model

        def get_tokens(source: str, data_only: bool = False, lang: Any = None) -> Generator[Token, None, None]:
            for t in tokens:
                check_canceled_sync()

                yield t

        model = _get_model(get_tokens, document.uri.to_path())

        setattr(model, "source", str(document.uri.to_path()))
        setattr(model, "model_type", document_type)

        return cast(ast.AST, model)

    async def get_general_model(self, document: TextDocument, data_only: bool = True) -> ast.AST:
        if data_only:
            return await document.get_cache(
                self.__get_general_model_data_only, await self.get_general_tokens(document, True)
            )
        return await document.get_cache(self.__get_general_model, await self.get_general_tokens(document))

    async def __get_general_model_data_only(self, document: TextDocument, tokens: Iterable[Any]) -> ast.AST:
        return self.__get_model(document, tokens, DocumentType.GENERAL)

    async def __get_general_model(self, document: TextDocument, tokens: Iterable[Any]) -> ast.AST:
        return self.__get_model(document, tokens, DocumentType.GENERAL)

    async def get_resource_model(self, document: TextDocument, data_only: bool = True) -> ast.AST:
        if data_only:
            return await document.get_cache(
                self.__get_resource_model_data_only, await self.get_resource_tokens(document, True)
            )

        return await document.get_cache(self.__get_resource_model, await self.get_resource_tokens(document))

    async def __get_resource_model_data_only(self, document: TextDocument, tokens: Iterable[Any]) -> ast.AST:
        return self.__get_model(document, tokens, DocumentType.RESOURCE)

    async def __get_resource_model(self, document: TextDocument, tokens: Iterable[Any]) -> ast.AST:
        return self.__get_model(document, tokens, DocumentType.RESOURCE)

    async def get_init_model(self, document: TextDocument, data_only: bool = True) -> ast.AST:
        if data_only:
            return await document.get_cache(self.__get_init_model_data_only, await self.get_init_tokens(document, True))
        return await document.get_cache(self.__get_init_model, await self.get_init_tokens(document))

    async def __get_init_model_data_only(self, document: TextDocument, tokens: Iterable[Any]) -> ast.AST:
        return self.__get_model(document, tokens, DocumentType.INIT)

    async def __get_init_model(self, document: TextDocument, tokens: Iterable[Any]) -> ast.AST:
        return self.__get_model(document, tokens, DocumentType.INIT)

    async def get_namespace(self, document: TextDocument) -> Namespace:
        return await document.get_cache(self.__get_namespace)

    async def __get_namespace(self, document: TextDocument) -> Namespace:
        return await self.__get_namespace_for_document_type(document, None)

    async def get_resource_namespace(self, document: TextDocument) -> Namespace:
        return await document.get_cache(self.__get_resource_namespace)

    async def __get_resource_namespace(self, document: TextDocument) -> Namespace:
        return await self.__get_namespace_for_document_type(document, DocumentType.RESOURCE)

    async def get_init_namespace(self, document: TextDocument) -> Namespace:
        return await document.get_cache(self.__get_init_namespace)

    async def __get_init_namespace(self, document: TextDocument) -> Namespace:
        return await self.__get_namespace_for_document_type(document, DocumentType.INIT)

    async def get_general_namespace(self, document: TextDocument) -> Namespace:
        return await document.get_cache(self.__get_general_namespace)

    async def __get_general_namespace(self, document: TextDocument) -> Namespace:
        return await self.__get_namespace_for_document_type(document, DocumentType.GENERAL)

    @async_tasking_event
    async def namespace_invalidated(sender, namespace: Namespace) -> None:  # NOSONAR
        ...

    async def __invalidate_namespace(self, sender: Namespace) -> None:
        document = sender.document
        if document is not None:
            document.invalidate_cache()

            await self.namespace_invalidated(
                self,
                sender,
                callback_filter=language_id_filter(document),
            )

    async def __document_cache_invalidate(self, sender: TextDocument) -> None:
        namespace: Optional[Namespace] = sender.get_cache_value(self.__get_namespace)
        if namespace is not None:
            await self.namespace_invalidated(
                self,
                namespace,
                callback_filter=language_id_filter(sender),
            )

    async def __get_namespace_for_document_type(
        self,
        document: TextDocument,
        document_type: Optional[DocumentType],
    ) -> Namespace:

        if document_type is not None and document_type == DocumentType.INIT:
            model = await self.get_init_model(document)
        elif document_type is not None and document_type == DocumentType.RESOURCE:
            model = await self.get_resource_model(document)
        elif document_type is not None and document_type == DocumentType.GENERAL:
            model = await self.get_general_model(document)
        else:
            model = await self.get_model(document)

        imports_manager = await self.get_imports_manager(document)

        languages, workspace_languages = await self.build_languages_from_model(document, model)

        result = Namespace(
            imports_manager, model, str(document.uri.to_path()), document, document_type, languages, workspace_languages
        )
        result.has_invalidated.add(self.__invalidate_namespace)
        result.has_imports_changed.add(self.__invalidate_namespace)

        document.cache_invalidate.add(self.__document_cache_invalidate)

        return result

    async def default_imports_manager(self) -> ImportsManager:
        async with self._imports_managers_lock:
            if self._default_imports_manager is None:
                self._default_imports_manager = ImportsManager(
                    self.parent,
                    Uri(self.parent.workspace.root_uri or "."),
                    RobotCodeConfig(),
                )

            return self._default_imports_manager

    async def get_imports_manager(self, document: TextDocument) -> ImportsManager:
        return await self.get_imports_manager_for_uri(document.uri)

    async def get_imports_manager_for_uri(self, uri: Uri) -> ImportsManager:
        return await self.get_imports_manager_for_workspace_folder(self.parent.workspace.get_workspace_folder(uri))

    async def get_imports_manager_for_workspace_folder(self, folder: Optional[WorkspaceFolder]) -> ImportsManager:
        if folder is None:
            if len(self.parent.workspace.workspace_folders) == 1:
                folder = self.parent.workspace.workspace_folders[0]
            else:
                return await self.default_imports_manager()

        async with self._imports_managers_lock:
            if folder not in self._imports_managers:
                config = await self.parent.workspace.get_configuration(RobotCodeConfig, folder.uri)

                self._imports_managers[folder] = ImportsManager(self.parent, folder.uri, config)

            return self._imports_managers[folder]
