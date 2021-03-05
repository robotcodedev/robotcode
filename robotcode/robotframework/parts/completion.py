from __future__ import annotations, print_function

import ast
import builtins
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Iterator,
    List,
    Optional,
    Type,
    Union,
    cast,
)

from ...language_server.language import language_id, trigger_characters
from ...language_server.text_document import TextDocument
from ...language_server.types import (
    CompletionContext,
    CompletionItem,
    CompletionItemKind,
    CompletionList,
    InsertTextFormat,
    MarkupContent,
    MarkupKind,
    Position,
    Range,
    TextEdit,
)
from ...utils.logging import LoggingDescriptor
from ..diagnostics.namespace import Namespace
from ..utils.ast import Token, range_from_node, range_from_token
from ..utils.async_ast import walk

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .model_helper import ModelHelperMixin
from .protocol_part import RobotLanguageServerProtocolPart

_CompleteMethod = Callable[
    [ast.AST, List[ast.AST], TextDocument, Position, Optional[CompletionContext]],
    Awaitable[Optional[Union[List[CompletionItem], CompletionList, None]]],
]


class RobotCompletionProtocolPart(RobotLanguageServerProtocolPart, ModelHelperMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.completion.collect.add(self.collect)

    def _find_method(self, cls: Type[Any]) -> Optional[_CompleteMethod]:
        if cls is ast.AST:
            return None
        method_name = "complete_" + cls.__name__
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            if callable(method):
                return cast(_CompleteMethod, method)
        for base in cls.__bases__:
            method = self._find_method(base)
            if method:
                return cast(_CompleteMethod, method)
        return None

    @language_id("robotframework")
    @trigger_characters([" ", "*", "\t", "."])
    # @all_commit_characters(['\n'])
    async def collect(
        self, sender: Any, document: TextDocument, position: Position, context: Optional[CompletionContext]
    ) -> Union[List[CompletionItem], CompletionList, None]:
        freezed_doc = await document.freeze()

        result_nodes = [
            node
            async for node in walk(await self.parent.documents_cache.get_model(freezed_doc))
            if position.is_in_range(range_from_node(node))
        ]

        result_nodes.reverse()

        for result_node in result_nodes:
            method = self._find_method(type(result_node))
            if method is None:
                continue

            result = await method(result_node, result_nodes, freezed_doc, position, context)
            if result is not None:
                return result

        return await self.complete_default()

    async def complete_default(self) -> List[CompletionItem]:

        return [
            CompletionItem(
                label="*** test case ***",
            ),
            CompletionItem(
                label="*** test cases ***",
            ),
            CompletionItem(
                label="*** settings ***",
            ),
            CompletionItem(
                label="*** variables ***",
            ),
        ]

    async def get_keyword_completion_items(
        self,
        namespace: Namespace,
        token: Optional[Token],
        document: TextDocument,
        position: Position,
        context: Optional[CompletionContext],
    ) -> List[CompletionItem]:
        result: List[CompletionItem] = []

        range: Optional[Range] = None

        if token is not None:
            range = range_from_token(token)

            if "." in token.value:

                def enumerate_indexes(s: str, c: str) -> Iterator[int]:
                    for i in builtins.range(len(s)):
                        if s[i] == c:
                            yield i

                lib_name_index = -1
                for e in enumerate_indexes(token.value, "."):
                    e += range.start.character
                    if e < position.character and lib_name_index < e:
                        lib_name_index = e

                if lib_name_index > -1:
                    library_name = token.value[0 : lib_name_index - range.start.character]  # noqa: E203

                    libraries = await namespace.get_libraries()
                    if library_name in libraries:
                        range.start.character = lib_name_index + 1
                        for kw in libraries[library_name].library_doc.keywords.values():
                            c = CompletionItem(
                                label=kw.name,
                                kind=CompletionItemKind.FUNCTION,
                                detail="Keyword",
                                documentation=MarkupContent(kind=MarkupKind.MARKDOWN, value=kw.to_markdown()),
                                insert_text_format=InsertTextFormat.PLAINTEXT,
                                text_edit=TextEdit(range=range, new_text=kw.name) if range is not None else None,
                            )
                            result.append(c)
                        return result

        settings = ["Documentation", "Tags", "Setup", "Teardown", "Template", "Timeout"]

        for setting in settings:
            c = CompletionItem(
                label=f"[{setting}]",
                kind=CompletionItemKind.KEYWORD,
                detail="Setting",
                insert_text_format=InsertTextFormat.PLAINTEXT,
                text_edit=TextEdit(range=range, new_text=f"[{setting}]") if range is not None else None,
            )
            result.append(c)

        for kw in await namespace.get_keywords():
            c = CompletionItem(
                label=kw.name,
                kind=CompletionItemKind.FUNCTION,
                detail="Keyword",
                documentation=MarkupContent(kind=MarkupKind.MARKDOWN, value=kw.to_markdown()),
                insert_text_format=InsertTextFormat.PLAINTEXT,
                text_edit=TextEdit(range=range, new_text=kw.name) if range is not None else None,
            )
            result.append(c)

        for k, v in (await namespace.get_libraries()).items():
            c = CompletionItem(
                label=k,
                kind=CompletionItemKind.MODULE,
                detail="Library",
                documentation=MarkupContent(kind=MarkupKind.MARKDOWN, value=v.library_doc.to_markdown()),
                insert_text_format=InsertTextFormat.PLAINTEXT,
                text_edit=TextEdit(range=range, new_text=k) if range is not None else None,
            )
            result.append(c)

        return result

    async def get_settings_completion_items(self, namespace: Namespace, range: Optional[Range]) -> List[CompletionItem]:
        settings = [
            "Documentation",
            "Metadata",
            "Suite Setup",
            "Suite Teardown",
            "Test Setup",
            "Test Teardown",
            "Test Template",
            "Test Timeout",
            "Force Tags",
            "Default Tags",
            "Library",
            "Resource",
            "Variables",
            "Task Setup",
            "Task Teardown",
            "Task Template",
            "Task Timeout",
        ]

        result: List[CompletionItem] = []

        for setting in settings:
            c = CompletionItem(
                label=setting,
                detail="Setting",
                insert_text_format=InsertTextFormat.PLAINTEXT,
                text_edit=TextEdit(range=range, new_text=setting) if range is not None else None,
            )
            result.append(c)

        return result

    async def complete_KeywordCall(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        document: TextDocument,
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import KeywordCall

        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return None

        kw_node = cast(KeywordCall, node)

        tokens_at_position = [cast(Token, t) for t in kw_node.tokens if position.is_in_range(range_from_token(t))]
        if not tokens_at_position:
            return None

        token_at_position = tokens_at_position[-1]

        if token_at_position.type in [RobotToken.KEYWORD, RobotToken.EOL, RobotToken.SEPARATOR]:
            index = kw_node.tokens.index(token_at_position)
            # token_after = kw_node.tokens[index + 1] if len(kw_node.tokens) > index + 1 else None
            token_before = cast(Token, kw_node.tokens[index - 1]) if len(kw_node.tokens) > index - 1 else None

            if (
                token_at_position.type in [RobotToken.EOL, RobotToken.SEPARATOR]
                and token_before is not None
                and token_before.type == RobotToken.KEYWORD
            ):
                range = range_from_token(token_at_position)
                if len(token_at_position.value) > 0 and position.character - range.start.character <= 1:
                    return await self.get_keyword_completion_items(namespace, token_before, document, position, context)

                return None

            return await self.get_keyword_completion_items(namespace, token_at_position, document, position, context)

        return []

    async def complete_EmptyLine(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        document: TextDocument,
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.blocks import SettingSection, TestCase
        from robot.parsing.model.statements import EmptyLine

        if len(nodes_at_position) < 2:
            return None

        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return None

        testcase_node = cast(EmptyLine, node)

        tokens_at_position = [cast(Token, t) for t in testcase_node.tokens if position.is_in_range(range_from_token(t))]
        if not tokens_at_position:
            return None

        token_at_position = tokens_at_position[0]

        if token_at_position.type in [RobotToken.EOL, RobotToken.SEPARATOR]:

            if isinstance(nodes_at_position[1], TestCase) and position.character >= 2:
                return await self.get_keyword_completion_items(namespace, None, document, position, context)
            if isinstance(nodes_at_position[1], SettingSection):
                return await self.get_settings_completion_items(namespace, None)

        return None
