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
    cast,
)

from ....utils.async_tools import (
    Lock,
    async_tasking_event,
    check_canceled_sync,
    create_sub_task,
)
from ....utils.uri import Uri
from ...common.decorators import language_id_filter
from ...common.parts.workspace import WorkspaceFolder
from ...common.text_document import TextDocument
from ..configuration import RobotConfig
from ..diagnostics.imports_manager import ImportsManager
from ..diagnostics.namespace import DocumentType, Namespace
from ..utils.ast import Token

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .protocol_part import RobotLanguageServerProtocolPart


class UnknownFileTypeError(Exception):
    pass


class DocumentsCache(RobotLanguageServerProtocolPart):
    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        self._imports_managers_lock = Lock()
        self._imports_managers: weakref.WeakKeyDictionary[WorkspaceFolder, ImportsManager] = weakref.WeakKeyDictionary()
        self._default_imports_manager: Optional[ImportsManager] = None

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

    async def get_tokens(self, document: TextDocument) -> List[Token]:
        return await document.get_cache(self.__get_tokens)

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

    async def get_general_tokens(self, document: TextDocument) -> List[Token]:
        return await document.get_cache(self.__get_general_tokens)

    async def __get_general_tokens(self, document: TextDocument) -> List[Token]:
        import robot.api

        def get(text: str) -> List[Token]:
            with io.StringIO(text) as content:
                return [e for e in robot.api.get_tokens(content) if check_canceled_sync()]

        return await self.__get_tokens_internal(document, get)

    async def __get_tokens_internal(
        self,
        document: TextDocument,
        get: Callable[[str], List[Token]],
    ) -> List[Token]:

        return get(await document.text())

    async def get_resource_tokens(self, document: TextDocument) -> List[Token]:
        return await document.get_cache(self.__get_resource_tokens)

    async def __get_resource_tokens(self, document: TextDocument) -> List[Token]:
        import robot.api

        def get(text: str) -> List[Token]:
            with io.StringIO(text) as content:
                return [e for e in robot.api.get_resource_tokens(content) if check_canceled_sync()]

        return await self.__get_tokens_internal(document, get)

    async def get_init_tokens(self, document: TextDocument) -> List[Token]:
        return await document.get_cache(self.__get_init_tokens)

    async def __get_init_tokens(self, document: TextDocument) -> List[Token]:
        import robot.api

        def get(text: str) -> List[Token]:
            with io.StringIO(text) as content:
                return [e for e in robot.api.get_init_tokens(content) if check_canceled_sync()]

        return await self.__get_tokens_internal(document, get)

    async def get_model(self, document: TextDocument) -> ast.AST:
        document_type = await self.get_document_type(document)

        if document_type == DocumentType.INIT:
            return await self.get_init_model(document)
        if document_type == DocumentType.GENERAL:
            return await self.get_general_model(document)
        if document_type == DocumentType.RESOURCE:
            return await self.get_resource_model(document)
        else:
            raise UnknownFileTypeError(f"Unknown file type '{document.uri}'.")

    def __get_model(self, document: TextDocument, tokens: Iterable[Any], document_type: DocumentType) -> ast.AST:
        from robot.parsing.lexer import Token
        from robot.parsing.parser.parser import _get_model

        def get_tokens(_source: str, _data_only: bool = False) -> Generator[Token, None, None]:
            for t in tokens:
                check_canceled_sync()

                yield t

        model = _get_model(get_tokens, document.uri.to_path())

        setattr(model, "source", str(document.uri.to_path()))
        setattr(model, "model_type", document_type)

        return cast(ast.AST, model)

    async def get_general_model(self, document: TextDocument) -> ast.AST:
        return await document.get_cache(self.__get_general_model)

    async def __get_general_model(self, document: TextDocument) -> ast.AST:
        return self.__get_model(document, await self.get_general_tokens(document), DocumentType.GENERAL)

    async def get_resource_model(self, document: TextDocument) -> ast.AST:
        return await document.get_cache(self.__get_resource_model)

    async def __get_resource_model(self, document: TextDocument) -> ast.AST:
        return self.__get_model(document, await self.get_resource_tokens(document), DocumentType.RESOURCE)

    async def get_init_model(self, document: TextDocument) -> ast.AST:
        return await document.get_cache(self.__get_init_model)

    async def __get_init_model(self, document: TextDocument) -> ast.AST:
        return self.__get_model(document, await self.get_init_tokens(document), DocumentType.INIT)

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
    async def namespace_invalidated(sender, document: TextDocument) -> None:  # NOSONAR
        ...

    async def __invalidate_namespace(self, namespace: Namespace) -> None:
        document = namespace.document
        if document is not None:
            await document.remove_cache_entry(self.__get_namespace)
            await self.namespace_invalidated(
                self,
                document,
                callback_filter=language_id_filter(document),
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

        def invalidate(namespace: Namespace) -> None:
            create_sub_task(self.__invalidate_namespace(namespace))

        return Namespace(imports_manager, model, str(document.uri.to_path()), invalidate, document, document_type)

    @property
    async def default_imports_manager(self) -> ImportsManager:
        if self._default_imports_manager is None:
            async with self._imports_managers_lock:
                if self._default_imports_manager is None:
                    self._default_imports_manager = ImportsManager(
                        self.parent,
                        Uri(self.parent.workspace.root_uri or "."),
                        RobotConfig(args=(), python_path=[], env={}, variables={}),
                    )
        return self._default_imports_manager

    async def get_imports_manager(self, document: TextDocument) -> ImportsManager:
        folder = self.parent.workspace.get_workspace_folder(document.uri)
        if folder is None:
            return await self.default_imports_manager

        if folder not in self._imports_managers:
            async with self._imports_managers_lock:
                if folder not in self._imports_managers:
                    config = await self.parent.workspace.get_configuration(RobotConfig, folder.uri)

                    self._imports_managers[folder] = ImportsManager(self.parent, folder.uri, config)
        return self._imports_managers[folder]
