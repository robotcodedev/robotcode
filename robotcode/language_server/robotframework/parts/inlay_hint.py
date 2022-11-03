from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Any, Awaitable, Callable, List, Optional, Type, cast

from ....utils.logging import LoggingDescriptor
from ...common.decorators import language_id
from ...common.lsp_types import InlayHint, InlayHintKind, Range
from ...common.text_document import TextDocument
from ..configuration import InlayHintsConfig
from ..diagnostics.library_doc import KeywordArgumentKind
from ..diagnostics.namespace import Namespace
from ..utils.ast_utils import Token, range_from_node, range_from_token
from ..utils.async_ast import iter_nodes

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .model_helper import ModelHelperMixin
from .protocol_part import RobotLanguageServerProtocolPart

_HandlerMethod = Callable[
    [TextDocument, Range, ast.AST, ast.AST, Namespace, InlayHintsConfig], Awaitable[Optional[List[InlayHint]]]
]


class RobotInlayHintProtocolPart(RobotLanguageServerProtocolPart, ModelHelperMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.inlay_hint.collect.add(self.collect)

    async def get_config(self, document: TextDocument) -> Optional[InlayHintsConfig]:
        folder = self.parent.workspace.get_workspace_folder(document.uri)
        if folder is None:
            return None

        return await self.parent.workspace.get_configuration(InlayHintsConfig, folder.uri)

    def _find_method(self, cls: Type[Any]) -> Optional[_HandlerMethod]:
        if cls is ast.AST:
            return None
        method_name = "handle_" + cls.__name__
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            if callable(method):
                return cast(_HandlerMethod, method)
        for base in cls.__bases__:
            method = self._find_method(base)
            if method:
                return cast(_HandlerMethod, method)

        return None

    @language_id("robotframework")
    @_logger.call
    async def collect(self, sender: Any, document: TextDocument, range: Range) -> Optional[List[InlayHint]]:
        config = await self.get_config(document)
        if config is None or not config.parameter_names and not config.namespaces:
            return None

        model = await self.parent.documents_cache.get_model(document, False)
        namespace = await self.parent.documents_cache.get_namespace(document)

        result: List[InlayHint] = []

        async for node in iter_nodes(model):
            node_range = range_from_node(node)
            if node_range.end < range.start:
                continue

            if node_range.start > range.end:
                break

            method = self._find_method(type(node))
            if method is not None:
                r = await method(document, range, node, model, namespace, config)
                if r is not None:
                    result.extend(r)

        return result

    async def _handle_keywordcall_fixture_template(  # noqa: N802
        self,
        keyword_token: Token,
        arguments: List[Token],
        namespace: Namespace,
        config: InlayHintsConfig,
    ) -> Optional[List[InlayHint]]:
        from robot.utils.escaping import split_from_equals

        kw_result = await self.get_keyworddoc_and_token_from_position(
            keyword_token.value,
            keyword_token,
            arguments,
            namespace,
            range_from_token(keyword_token).start,
        )

        if kw_result is None:
            return None

        kw_doc, _ = kw_result

        if kw_doc is None:
            return None

        result: List[InlayHint] = []

        if config.parameter_names:
            for i, arg_value in enumerate(arguments):
                name, _ = split_from_equals(arg_value.value)
                has_name = any(v for v in kw_doc.args if v.kind == KeywordArgumentKind.VAR_NAMED or v.name == name)
                if not has_name and i < len(kw_doc.args):
                    arg = kw_doc.args[i]
                    prefix = ""
                    if arg.kind == KeywordArgumentKind.VAR_POSITIONAL:
                        prefix = "*"
                    elif arg.kind == KeywordArgumentKind.VAR_NAMED:
                        prefix = "**"
                    result.append(
                        InlayHint(range_from_token(arg_value).start, f"{prefix}{arg.name}=", InlayHintKind.PARAMETER)
                    )

        if config.namespaces:
            lib_entry, kw_namespace = await self.get_namespace_info_from_keyword(namespace, keyword_token)
            if lib_entry is None and kw_namespace is None:
                if kw_doc.libtype == "LIBRARY":
                    lib = next(
                        (
                            lib
                            for lib in (await namespace.get_libraries()).values()
                            if lib.name == kw_doc.libname and kw_doc in lib.library_doc.keywords.keywords
                        ),
                        None,
                    )
                else:
                    lib = next(
                        (
                            lib
                            for lib in (await namespace.get_resources()).values()
                            if lib.name == kw_doc.libname and kw_doc in lib.library_doc.keywords.keywords
                        ),
                        None,
                    )
                if lib is not None:
                    result.append(InlayHint(range_from_token(keyword_token).start, f"{lib.alias or lib.name}."))

        return result

    async def handle_KeywordCall(  # noqa: N802
        self,
        document: TextDocument,
        range: Range,
        node: ast.AST,
        model: ast.AST,
        namespace: Namespace,
        config: InlayHintsConfig,
    ) -> Optional[List[InlayHint]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import KeywordCall

        keyword_call = cast(KeywordCall, node)
        keyword_token = keyword_call.get_token(RobotToken.KEYWORD)
        if keyword_token is None or not keyword_token.value:
            return None

        arguments = keyword_call.get_tokens(RobotToken.ARGUMENT)
        return await self._handle_keywordcall_fixture_template(keyword_token, arguments, namespace, config)

    async def handle_Fixture(  # noqa: N802
        self,
        document: TextDocument,
        range: Range,
        node: ast.AST,
        model: ast.AST,
        namespace: Namespace,
        config: InlayHintsConfig,
    ) -> Optional[List[InlayHint]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Fixture

        fixture = cast(Fixture, node)
        keyword_token = fixture.get_token(RobotToken.NAME)
        if keyword_token is None or not keyword_token.value:
            return None

        arguments = fixture.get_tokens(RobotToken.ARGUMENT)
        return await self._handle_keywordcall_fixture_template(keyword_token, arguments, namespace, config)

    async def handle_TestTemplate(  # noqa: N802
        self,
        document: TextDocument,
        range: Range,
        node: ast.AST,
        model: ast.AST,
        namespace: Namespace,
        config: InlayHintsConfig,
    ) -> Optional[List[InlayHint]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import TestTemplate

        template = cast(TestTemplate, node)
        keyword_token = template.get_token(RobotToken.NAME, RobotToken.ARGUMENT)
        if keyword_token is None or not keyword_token.value:
            return None

        return await self._handle_keywordcall_fixture_template(keyword_token, [], namespace, config)

    async def handle_Template(  # noqa: N802
        self,
        document: TextDocument,
        range: Range,
        node: ast.AST,
        model: ast.AST,
        namespace: Namespace,
        config: InlayHintsConfig,
    ) -> Optional[List[InlayHint]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Template

        template = cast(Template, node)
        keyword_token = template.get_token(RobotToken.NAME, RobotToken.ARGUMENT)
        if keyword_token is None or not keyword_token.value:
            return None

        return await self._handle_keywordcall_fixture_template(keyword_token, [], namespace, config)
