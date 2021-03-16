from __future__ import annotations

import ast
import asyncio
import io
import weakref
from typing import TYPE_CHECKING, Iterator, List, Optional, cast

from ...language_server.parts.workspace import WorkspaceFolder
from ...language_server.text_document import TextDocument
from ...utils.async_event import async_tasking_event
from ...utils.uri import Uri
from ..configuration import RobotConfig
from ..diagnostics.imports_manager import ImportsManager
from ..diagnostics.namespace import Namespace
from ..utils.ast import Token

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .protocol_part import RobotLanguageServerProtocolPart


class UnknownFileTypeError(Exception):
    pass


class DocumentsCache(RobotLanguageServerProtocolPart):
    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)
        self._loop = asyncio.get_event_loop()

        self._imports_managers_lock = asyncio.Lock()
        self._imports_managers: weakref.WeakKeyDictionary[WorkspaceFolder, ImportsManager] = weakref.WeakKeyDictionary()
        self._default_imports_manager: Optional[ImportsManager] = None

    async def get_tokens(self, document: TextDocument) -> List[Token]:
        return await document.get_cache(self.__get_tokens)

    async def __get_tokens(self, document: TextDocument) -> List[Token]:
        import robot.api

        def get() -> List[Token]:
            gen_func: Iterator[Token]

            with io.StringIO(document.text) as content:
                path = document.uri.to_path()
                suffix = path.suffix.lower()

                if path.name == "__init__.robot":
                    gen_func = robot.api.get_init_tokens(content)

                elif suffix == ".robot":
                    gen_func = robot.api.get_tokens(content)

                elif suffix == ".resource":
                    gen_func = robot.api.get_resource_tokens(content)

                else:
                    raise UnknownFileTypeError(str(document.uri))

                return [e for e in gen_func]

        return await asyncio.get_event_loop().run_in_executor(None, get)

    async def get_model(self, document: TextDocument) -> ast.AST:
        return await document.get_cache(self.__get_model)

    async def __get_model(self, document: TextDocument) -> ast.AST:
        import robot.api

        def get() -> ast.AST:
            with io.StringIO(document.text) as content:
                path = document.uri.to_path()
                suffix = path.suffix.lower()

                if path.name == "__init__.robot":
                    model = cast(ast.AST, robot.api.get_init_model(content))
                elif suffix in (".robot",):
                    model = cast(ast.AST, robot.api.get_model(content))
                elif suffix in (".resource", ".rst", ".rest"):
                    model = cast(ast.AST, robot.api.get_resource_model(content))
                else:
                    raise UnknownFileTypeError(f"Unknown file type '{document.uri}'.")

                setattr(model, "source", str(path))

                return model

        return await asyncio.get_event_loop().run_in_executor(None, get)

    async def get_namespace(self, document: TextDocument) -> Namespace:
        return await document.get_cache(self.__get_namespace)

    @async_tasking_event
    async def namespace_invalidated(sender, document: TextDocument) -> None:
        ...

    async def __invalidate_namespace(self, document: TextDocument, namespace: Namespace) -> None:
        await document.remove_cache_entry(self.__get_namespace)
        await self.namespace_invalidated(self, document)

    async def __get_namespace(self, document: TextDocument) -> Namespace:
        model = await self.get_model(document)
        imports_manager = await self.get_imports_manager(document)

        def invalidate(namespace: Namespace) -> None:
            if self._loop.is_running():
                asyncio.ensure_future(self.__invalidate_namespace(document, namespace))

        return Namespace(imports_manager, model, str(document.uri.to_path()), document.parent or document, invalidate)

    @property
    def default_imports_manager(self) -> ImportsManager:
        if self._default_imports_manager is None:
            self._default_imports_manager = ImportsManager(
                self.parent, Uri(self.parent.workspace.root_uri or "."), RobotConfig(args=(), pythonpath=[])
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
