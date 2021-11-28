from __future__ import annotations

import ast
import asyncio
import enum
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

from ....utils.async_tools import CancelationToken, async_tasking_event, to_thread
from ....utils.uri import Uri
from ...common.language import language_id_filter
from ...common.parts.workspace import WorkspaceFolder
from ...common.text_document import TextDocument
from ..configuration import RobotConfig
from ..diagnostics.imports_manager import ImportsManager
from ..diagnostics.namespace import Namespace
from ..utils.ast import Token

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .protocol_part import RobotLanguageServerProtocolPart


class UnknownFileTypeError(Exception):
    pass


class DocumentType(enum.Enum):
    UNKNOWN = "unknown"
    GENERAL = "robot"
    RESOURCE = "resource"
    INIT = "init"


class DocumentsCache(RobotLanguageServerProtocolPart):
    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)
        self._loop = asyncio.get_event_loop()

        self._imports_managers_lock = asyncio.Lock()
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

    async def get_tokens(
        self, document: TextDocument, cancelation_token: Optional[CancelationToken] = None
    ) -> List[Token]:
        return await document.get_cache(self.__get_tokens, cancelation_token)

    async def __get_tokens(
        self, document: TextDocument, cancelation_token: Optional[CancelationToken] = None
    ) -> List[Token]:
        document_type = await self.get_document_type(document)
        if document_type == DocumentType.INIT:
            return await self.get_init_tokens(document, cancelation_token)
        elif document_type == DocumentType.GENERAL:
            return await self.get_general_tokens(document, cancelation_token)
        elif document_type == DocumentType.RESOURCE:
            return await self.get_resource_tokens(document, cancelation_token)
        else:
            raise UnknownFileTypeError(str(document.uri))

    async def get_general_tokens(
        self, document: TextDocument, cancelation_token: Optional[CancelationToken] = None
    ) -> List[Token]:
        return await document.get_cache(self.__get_general_tokens, cancelation_token)

    async def __get_general_tokens(
        self, document: TextDocument, cancelation_token: Optional[CancelationToken] = None
    ) -> List[Token]:
        import robot.api

        def get(text: str, cancelation_token: CancelationToken) -> List[Token]:
            with io.StringIO(text) as content:
                return [e for e in robot.api.get_tokens(content) if not cancelation_token.throw_if_canceled()]

        return await self.__get_tokens_internal(document, get, cancelation_token)

    async def __get_tokens_internal(
        self,
        document: TextDocument,
        get: Callable[[str, CancelationToken], List[Token]],
        cancelation_token: Optional[CancelationToken] = None,
    ) -> List[Token]:
        try:
            if cancelation_token is None:
                cancelation_token = CancelationToken()
            return await to_thread(get, document.text, cancelation_token)
        except asyncio.CancelledError:
            if cancelation_token is not None:
                cancelation_token.cancel()
            raise

    async def get_resource_tokens(
        self, document: TextDocument, cancelation_token: Optional[CancelationToken] = None
    ) -> List[Token]:
        return await document.get_cache(self.__get_resource_tokens, cancelation_token)

    async def __get_resource_tokens(
        self, document: TextDocument, cancelation_token: Optional[CancelationToken] = None
    ) -> List[Token]:
        import robot.api

        def get(text: str, cancelation_token: CancelationToken) -> List[Token]:
            with io.StringIO(text) as content:
                return [e for e in robot.api.get_resource_tokens(content) if not cancelation_token.throw_if_canceled()]

        return await self.__get_tokens_internal(document, get, cancelation_token)

    async def get_init_tokens(
        self, document: TextDocument, cancelation_token: Optional[CancelationToken] = None
    ) -> List[Token]:
        return await document.get_cache(self.__get_init_tokens, cancelation_token)

    async def __get_init_tokens(
        self, document: TextDocument, cancelation_token: Optional[CancelationToken] = None
    ) -> List[Token]:
        import robot.api

        def get(text: str, cancelation_token: CancelationToken) -> List[Token]:
            with io.StringIO(text) as content:
                return [e for e in robot.api.get_init_tokens(content) if not cancelation_token.throw_if_canceled()]

        return await self.__get_tokens_internal(document, get, cancelation_token)

    async def get_model(self, document: TextDocument, cancelation_token: Optional[CancelationToken] = None) -> ast.AST:
        document_type = await self.get_document_type(document)

        if document_type == DocumentType.INIT:
            return await self.get_init_model(document, cancelation_token)
        if document_type == DocumentType.GENERAL:
            return await self.get_general_model(document, cancelation_token)
        if document_type == DocumentType.RESOURCE:
            return await self.get_resource_model(document, cancelation_token)
        else:
            raise UnknownFileTypeError(f"Unknown file type '{document.uri}'.")

    async def __get_model(
        self,
        document: TextDocument,
        tokens: Iterable[Any],
        document_type: DocumentType,
        cancelation_token: Optional[CancelationToken] = None,
    ) -> ast.AST:
        from robot.parsing.lexer import Token
        from robot.parsing.parser.parser import _get_model

        if cancelation_token is not None:
            cancelation_token = CancelationToken()

        def get_tokens(_source: str, _data_only: bool = False) -> Generator[Token, None, None]:
            for t in tokens:
                if cancelation_token is not None:
                    cancelation_token.throw_if_canceled()
                yield t

        try:
            model = await to_thread(_get_model, get_tokens, document.uri.to_path())
        except asyncio.CancelledError:
            if cancelation_token is not None:
                cancelation_token.cancel()
            raise

        setattr(model, "source", str(document.uri.to_path()))
        setattr(model, "model_type", document_type)

        return cast(ast.AST, model)

    async def get_general_model(
        self, document: TextDocument, cancelation_token: Optional[CancelationToken] = None
    ) -> ast.AST:
        return await document.get_cache(self.__get_general_model, cancelation_token)

    async def __get_general_model(
        self, document: TextDocument, cancelation_token: Optional[CancelationToken] = None
    ) -> ast.AST:
        return await self.__get_model(
            document, await self.get_general_tokens(document), DocumentType.GENERAL, cancelation_token
        )

    async def get_resource_model(
        self, document: TextDocument, cancelation_token: Optional[CancelationToken] = None
    ) -> ast.AST:
        return await document.get_cache(self.__get_resource_model, cancelation_token)

    async def __get_resource_model(
        self, document: TextDocument, cancelation_token: Optional[CancelationToken] = None
    ) -> ast.AST:
        return await self.__get_model(
            document, await self.get_resource_tokens(document), DocumentType.RESOURCE, cancelation_token
        )

    async def get_init_model(
        self, document: TextDocument, cancelation_token: Optional[CancelationToken] = None
    ) -> ast.AST:
        return await document.get_cache(self.__get_init_model, cancelation_token)

    async def __get_init_model(
        self, document: TextDocument, cancelation_token: Optional[CancelationToken] = None
    ) -> ast.AST:
        return await self.__get_model(
            document, await self.get_init_tokens(document), DocumentType.INIT, cancelation_token
        )

    async def get_namespace(
        self, document: TextDocument, cancelation_token: Optional[CancelationToken] = None
    ) -> Namespace:
        return await document.get_cache(self.__get_namespace, cancelation_token)

    async def __get_namespace(
        self, document: TextDocument, cancelation_token: Optional[CancelationToken] = None
    ) -> Namespace:
        return await self.__get_namespace_for_document_type(document, None, cancelation_token)

    async def get_resource_namespace(
        self, document: TextDocument, cancelation_token: Optional[CancelationToken] = None
    ) -> Namespace:
        return await document.get_cache(self.__get_resource_namespace, cancelation_token)

    async def __get_resource_namespace(
        self, document: TextDocument, cancelation_token: Optional[CancelationToken] = None
    ) -> Namespace:
        return await self.__get_namespace_for_document_type(document, DocumentType.RESOURCE, cancelation_token)

    async def get_init_namespace(
        self, document: TextDocument, cancelation_token: Optional[CancelationToken] = None
    ) -> Namespace:
        return await document.get_cache(self.__get_init_namespace, cancelation_token)

    async def __get_init_namespace(
        self, document: TextDocument, cancelation_token: Optional[CancelationToken] = None
    ) -> Namespace:
        return await self.__get_namespace_for_document_type(document, DocumentType.INIT, cancelation_token)

    async def get_general_namespace(
        self, document: TextDocument, cancelation_token: Optional[CancelationToken] = None
    ) -> Namespace:
        return await document.get_cache(self.__get_general_namespace, cancelation_token)

    async def __get_general_namespace(
        self, document: TextDocument, cancelation_token: Optional[CancelationToken] = None
    ) -> Namespace:
        return await self.__get_namespace_for_document_type(document, DocumentType.GENERAL, cancelation_token)

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
        cancelation_token: Optional[CancelationToken] = None,
    ) -> Namespace:
        if document_type is not None and document_type == DocumentType.INIT:
            model = await self.get_init_model(document, cancelation_token)
        elif document_type is not None and document_type == DocumentType.RESOURCE:
            model = await self.get_resource_model(document, cancelation_token)
        elif document_type is not None and document_type == DocumentType.GENERAL:
            model = await self.get_general_model(document, cancelation_token)
        else:
            model = await self.get_model(document, cancelation_token)

        imports_manager = await self.get_imports_manager(document)

        def invalidate(namespace: Namespace) -> None:
            if self._loop.is_running():
                asyncio.create_task(self.__invalidate_namespace(namespace))

        return Namespace(imports_manager, model, str(document.uri.to_path()), invalidate, document)

    @property
    def default_imports_manager(self) -> ImportsManager:
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
            return self.default_imports_manager

        async with self._imports_managers_lock:
            if folder not in self._imports_managers:
                config = await self.parent.workspace.get_configuration(RobotConfig, folder.uri)

                self._imports_managers[folder] = ImportsManager(self.parent, folder.uri, config)
            return self._imports_managers[folder]
