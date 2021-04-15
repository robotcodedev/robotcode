from __future__ import annotations

import ast
import asyncio
import builtins
import os
import weakref
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterator,
    List,
    Optional,
    Tuple,
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
    CompletionTriggerKind,
    InsertTextFormat,
    MarkupContent,
    MarkupKind,
    Position,
    Range,
    TextEdit,
)
from ...utils.async_itertools import async_chain, async_chain_iterator
from ...utils.logging import LoggingDescriptor
from ..configuration import SyntaxConfig
from ..diagnostics.library_doc import (
    CompleteResultKind,
    KeywordArgumentKind,
    KeywordDoc,
)
from ..utils.ast import (
    Token,
    get_nodes_at_position,
    get_tokens_at_position,
    range_from_token,
    whitespace_at_begin_of_token,
    whitespace_from_begin_of_token,
)
from .model_helper import ModelHelperMixin

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .protocol_part import RobotLanguageServerProtocolPart


class RobotCompletionProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.completion.collect.add(self.collect)
        parent.completion.resolve.add(self.resolve)

    @language_id("robotframework")
    @trigger_characters([" ", "*", "\t", ".", "/", os.sep])
    # @all_commit_characters(['\n'])
    async def collect(
        self, sender: Any, document: TextDocument, position: Position, context: Optional[CompletionContext]
    ) -> Union[List[CompletionItem], CompletionList, None]:
        return await CompletionCollector(self.parent, document).collect(position, context)

    @language_id("robotframework")
    async def resolve(self, sender: Any, completion_item: CompletionItem) -> CompletionItem:
        return await CompletionCollector(self.parent).resolve(completion_item)


_CompleteMethod = Callable[
    [ast.AST, List[ast.AST], Position, Optional[CompletionContext]],
    Awaitable[Optional[Optional[List[CompletionItem]]]],
]

SECTIONS = [
    "Test Case",
    "Test Cases",
    "Settings",
    "Setting",
    "Variable",
    "Variables",
    "Keywords",
    "Comment",
    "Comments",
]
DEFAULT_SECTIONS_STYLE = "*** {name} ***"

SETTINGS = [
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

TESTCASE_SETTINGS = ["Documentation", "Tags", "Setup", "Teardown", "Template", "Timeout"]
KEYWORD_SETTINGS = ["Documentation", "Tags", "Arguments", "Return", "Teardown", "Timeout"]

SNIPPETS = {
    "FOR": [r"FOR  \${${1}}  ${2|IN,IN ENUMERATE,IN RANGE,IN ZIP|}  ${3:arg}", "$0", "END", ""],
    "IF": [r"IF  \${${1}}", "$0", "END", ""],
}


class CompletionCollector(ModelHelperMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol, document: Optional[TextDocument] = None) -> None:
        self.parent = parent
        self._section_style: Optional[str] = None
        self._document = weakref.ref(document) if document is not None else None

    @property
    def document(self) -> Optional[TextDocument]:
        return self._document() if self._document is not None else None

    async def get_section_style(self) -> str:
        if self.document is not None and self._section_style is None:
            folder = self.parent.workspace.get_workspace_folder(self.document.uri)
            if folder is None:
                self._section_style = DEFAULT_SECTIONS_STYLE
            else:
                config = await self.parent.workspace.get_configuration(SyntaxConfig, folder.uri)

                self._section_style = config.section_style

        return self._section_style or DEFAULT_SECTIONS_STYLE

    async def _find_methods(self, cls: Type[Any]) -> AsyncIterator[_CompleteMethod]:
        if cls is ast.AST:
            return

        method_name = "complete_" + cls.__name__
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            if callable(method):
                yield cast(_CompleteMethod, method)
        for base in cls.__bases__:
            async for m in self._find_methods(base):
                yield m

    @language_id("robotframework")
    @trigger_characters([" ", "*", "\t", ".", "/"])
    # @all_commit_characters(['\n'])
    async def collect(
        self, position: Position, context: Optional[CompletionContext]
    ) -> Union[List[CompletionItem], CompletionList, None]:

        if self.document is None:
            return []

        result_nodes = await get_nodes_at_position(await self.parent.documents_cache.get_model(self.document), position)

        result_nodes.reverse()

        async def iter_results() -> AsyncIterator[List[CompletionItem]]:
            for result_node in result_nodes:
                async for method in self._find_methods(type(result_node)):
                    r = await method(result_node, result_nodes, position, context)
                    if r is not None:
                        yield r

            r = await self.complete_default(result_nodes, position, context)
            if r is not None:
                yield r

        result = CompletionList(is_incomplete=False, items=[e async for e in async_chain_iterator(iter_results())])
        if not result.items:
            return None
        return result

    async def resolve(self, completion_item: CompletionItem) -> CompletionItem:
        if completion_item.data is not None:
            document_uri = completion_item.data.get("document_uri", None)
            if document_uri is not None:
                document = self.parent.documents.get(document_uri, None)
                if document is not None and (type := completion_item.data.get("type", None)) is not None:
                    if type in [
                        CompleteResultKind.MODULE.name,
                        CompleteResultKind.MODULE_INTERNAL.name,
                        CompleteResultKind.FILE.name,
                    ]:
                        name = completion_item.data.get("name", None)
                        if name is not None:
                            try:
                                lib_doc = await (
                                    await self.parent.documents_cache.get_imports_manager(document)
                                ).get_libdoc_for_library_import(
                                    name, (), str(document.uri.to_path().parent), sentinel=self
                                )

                                if lib_doc is not None:
                                    completion_item.documentation = MarkupContent(
                                        kind=MarkupKind.MARKDOWN, value=lib_doc.to_markdown()
                                    )

                            except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
                                raise
                            except BaseException as e:
                                completion_item.documentation = MarkupContent(
                                    kind=MarkupKind.MARKDOWN, value=f"Error:\n{e}"
                                )
                    elif type in [CompleteResultKind.RESOURCE.name]:
                        name = completion_item.data.get("name", None)
                        if name is not None:
                            try:
                                lib_doc = lib_doc = await (
                                    await self.parent.documents_cache.get_imports_manager(document)
                                ).get_libdoc_for_resource_import(
                                    name, str(document.uri.to_path().parent), sentinel=self
                                )

                                if lib_doc is not None:
                                    completion_item.documentation = MarkupContent(
                                        kind=MarkupKind.MARKDOWN, value=lib_doc.to_markdown()
                                    )

                            except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
                                raise
                            except BaseException as e:
                                completion_item.documentation = MarkupContent(
                                    kind=MarkupKind.MARKDOWN, value=f"Error:\n{e}"
                                )
                    elif type in [CompleteResultKind.KEYWORD.name]:
                        libname = completion_item.data.get("libname", None)
                        name = completion_item.data.get("name", None)
                        namespace = await self.parent.documents_cache.get_namespace(document)

                        if libname is not None and name is not None and namespace is not None:
                            try:
                                kw_doc = next(
                                    (kw for kw in await namespace.get_keywords() if kw.name == name),
                                    None,
                                )

                                if kw_doc is not None:
                                    completion_item.documentation = MarkupContent(
                                        kind=MarkupKind.MARKDOWN, value=kw_doc.to_markdown()
                                    )

                            except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
                                raise
                            except BaseException:
                                pass

        return completion_item

    async def create_section_completion_items(self, range: Optional[Range]) -> List[CompletionItem]:
        style = await self.get_section_style()

        return [
            CompletionItem(
                label=s[0],
                kind=CompletionItemKind.CLASS,
                detail="Section",
                sort_text=f"100_{s[1]}",
                insert_text_format=InsertTextFormat.PLAINTEXT,
                text_edit=TextEdit(
                    range=range,
                    new_text=s[0],
                )
                if range is not None
                else None,
            )
            for s in ((style.format(name=k), k) for k in SECTIONS)
        ]

    async def create_settings_completion_items(self, range: Optional[Range]) -> List[CompletionItem]:
        return [
            CompletionItem(
                label=setting,
                kind=CompletionItemKind.KEYWORD,
                detail="Setting",
                sort_text=f"090_{setting}",
                insert_text_format=InsertTextFormat.PLAINTEXT,
                text_edit=TextEdit(range=range, new_text=setting) if range is not None else None,
            )
            for setting in SETTINGS
        ]

    async def create_keyword_snippet_completion_items(self, range: Optional[Range]) -> List[CompletionItem]:
        line_end = "\n"
        return [
            CompletionItem(
                label=f"{snippet_name}",
                kind=CompletionItemKind.SNIPPET,
                detail="Snippet",
                sort_text=f"010_{snippet_name}",
                insert_text_format=InsertTextFormat.SNIPPET,
                text_edit=TextEdit(range=range, new_text=line_end.join(snippet_value)) if range is not None else None,
            )
            for snippet_name, snippet_value in SNIPPETS.items()
        ]

    async def create_testcase_settings_completion_items(self, range: Optional[Range]) -> List[CompletionItem]:
        return [
            CompletionItem(
                label=f"[{setting}]",
                kind=CompletionItemKind.KEYWORD,
                detail="Setting",
                sort_text=f"070_{setting}",
                insert_text_format=InsertTextFormat.PLAINTEXT,
                text_edit=TextEdit(range=range, new_text=f"[{setting}]") if range is not None else None,
            )
            for setting in TESTCASE_SETTINGS
        ]

    async def create_keyword_settings_completion_items(self, range: Optional[Range]) -> List[CompletionItem]:
        return [
            CompletionItem(
                label=f"[{setting}]",
                kind=CompletionItemKind.KEYWORD,
                detail="Setting",
                sort_text=f"070_{setting}",
                insert_text_format=InsertTextFormat.PLAINTEXT,
                text_edit=TextEdit(range=range, new_text=f"[{setting}]") if range is not None else None,
            )
            for setting in KEYWORD_SETTINGS
        ]

    async def create_keyword_completion_items(
        self,
        token: Optional[Token],
        position: Position,
    ) -> List[CompletionItem]:
        result: List[CompletionItem] = []
        if self.document is None:
            return []

        namespace = await self.parent.documents_cache.get_namespace(self.document)
        if namespace is None:
            return []

        r: Optional[Range] = None

        # TODO: create Snippet for embedded keywords?

        if token is not None:
            r = range_from_token(token)

            if r is not None and "." in token.value:

                def enumerate_indexes(s: str, c: str) -> Iterator[int]:
                    for i in builtins.range(len(s)):
                        if s[i] == c:
                            yield i

                lib_name_index = -1
                for e in enumerate_indexes(token.value, "."):
                    e += r.start.character
                    if position.character > e > lib_name_index:
                        lib_name_index = e

                if lib_name_index >= 0:
                    library_name = token.value[0 : lib_name_index - r.start.character]  # noqa: E203

                    libraries = await namespace.get_libraries()
                    if library_name in libraries:
                        r.start.character = lib_name_index + 1
                        for kw in libraries[library_name].library_doc.keywords.values():
                            if kw.is_error_handler:
                                continue
                            c = CompletionItem(
                                label=kw.name,
                                kind=CompletionItemKind.FUNCTION,
                                detail=CompleteResultKind.KEYWORD.value,
                                sort_text=f"020_{kw.name}",
                                insert_text_format=InsertTextFormat.PLAINTEXT,
                                text_edit=TextEdit(range=r, new_text=kw.name) if r is not None else None,
                                data={
                                    "document_uri": str(self.document.uri),
                                    "type": CompleteResultKind.KEYWORD.name,
                                    "libname": kw.libname,
                                    "name": kw.name,
                                },
                            )
                            result.append(c)
                        return result

                    resources = await namespace.get_resources()
                    if library_name in resources:
                        r.start.character = lib_name_index + 1
                        for kw in resources[library_name].library_doc.keywords.values():
                            if kw.is_error_handler:
                                continue
                            c = CompletionItem(
                                label=kw.name,
                                kind=CompletionItemKind.FUNCTION,
                                detail=CompleteResultKind.KEYWORD.value,
                                sort_text=f"020_{kw.name}",
                                insert_text_format=InsertTextFormat.PLAINTEXT,
                                text_edit=TextEdit(range=r, new_text=kw.name) if r is not None else None,
                                data={
                                    "document_uri": str(self.document.uri),
                                    "type": CompleteResultKind.KEYWORD.name,
                                    "libname": kw.libname,
                                    "name": kw.name,
                                },
                            )
                            result.append(c)
                        return result

        for kw in await namespace.get_keywords():
            if kw.is_error_handler:
                continue

            c = CompletionItem(
                label=kw.name,
                kind=CompletionItemKind.FUNCTION,
                detail=f"{CompleteResultKind.KEYWORD.value} {f'({kw.libname})' if kw.libname is not None else ''}",
                deprecated=kw.is_deprecated,
                sort_text=f"020_{kw.name}",
                insert_text_format=InsertTextFormat.PLAINTEXT,
                text_edit=TextEdit(range=r, new_text=kw.name) if r is not None else None,
                data={
                    "document_uri": str(self.document.uri),
                    "type": CompleteResultKind.KEYWORD.name,
                    "libname": kw.libname,
                    "name": kw.name,
                },
            )
            result.append(c)

        for k, v in (await namespace.get_libraries()).items():
            c = CompletionItem(
                label=k,
                kind=CompletionItemKind.MODULE,
                detail="Library",
                sort_text=f"030_{k}",
                deprecated=v.library_doc.is_deprecated,
                # documentation=MarkupContent(kind=MarkupKind.MARKDOWN, value=v.library_doc.to_markdown()),
                insert_text_format=InsertTextFormat.PLAINTEXT,
                text_edit=TextEdit(range=r, new_text=k) if r is not None else None,
                data={
                    "document_uri": str(self.document.uri),
                    "type": CompleteResultKind.MODULE.name,
                    "name": v.name,
                },
            )
            result.append(c)

        for k, v in (await namespace.get_resources()).items():
            c = CompletionItem(
                label=k,
                kind=CompletionItemKind.MODULE,
                detail="Resource",
                deprecated=v.library_doc.is_deprecated,
                sort_text=f"030_{k}",
                documentation=MarkupContent(kind=MarkupKind.MARKDOWN, value=v.library_doc.to_markdown()),
                insert_text_format=InsertTextFormat.PLAINTEXT,
                text_edit=TextEdit(range=r, new_text=k) if r is not None else None,
                data={
                    "document_uri": str(self.document.uri),
                    "type": CompleteResultKind.RESOURCE.name,
                    "name": v.name,
                },
            )
            result.append(c)

        return result

    async def complete_default(
        self,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Optional[List[CompletionItem]]:
        from robot.parsing.model.statements import Statement

        if len(nodes_at_position) > 1 and isinstance(nodes_at_position[0], Statement):
            statement_node = cast(Statement, nodes_at_position[0])
            if len(statement_node.tokens) > 0:
                token = cast(Token, statement_node.tokens[0])
                r = range_from_token(token)
                value = token.value.strip()
                only_stars = value is not None and "*" in value and all(v == "*" for v in value)
                if (
                    r.start.character == 0
                    and (position.is_in_range(r) or position == r.end)
                    and (only_stars or value.startswith("*") or position.character == 0)
                ):
                    return await self.create_section_completion_items(r)
                elif len(statement_node.tokens) > 1 and only_stars:
                    r1 = range_from_token(statement_node.tokens[1])
                    ws = whitespace_at_begin_of_token(statement_node.tokens[1])
                    if ws > 0:
                        r1.end.character = r1.start.character + ws
                        if position.is_in_range(r1) or position == r1.end:
                            r.end = r1.end
                            return await self.create_section_completion_items(r)

        elif position.character == 0:
            return await self.create_section_completion_items(None)

        return None

    async def complete_SettingSection(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        from robot.parsing.model.statements import SectionHeader, Statement

        if nodes_at_position.index(node) > 0 and not isinstance(nodes_at_position[0], SectionHeader):
            statement_node = cast(Statement, nodes_at_position[0])
            if len(statement_node.tokens) > 0:
                token = cast(Token, statement_node.tokens[0])
                r = range_from_token(token)
                if position.is_in_range(r) or r.end == position:
                    return await self.create_settings_completion_items(r)

        return None

    async def _complete_TestCase_or_Keyword(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
        in_template: bool,
        create_items: Callable[
            [bool, bool, Optional[Range], Optional[Token], Position],
            Awaitable[Union[List[CompletionItem], CompletionList, None]],
        ],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import KeywordName, Statement, TestCaseName

        index = 0
        in_assign = False

        statement_node = cast(Statement, nodes_at_position[0])
        if isinstance(statement_node, (TestCaseName, KeywordName)):
            index += 1

        while index < len(statement_node.tokens):
            if len(statement_node.tokens) > index:
                token = cast(Token, statement_node.tokens[index])
                if token.type == RobotToken.ASSIGN:
                    index += 1
                    in_assign = True
                    r = range_from_token(token)
                    if position.is_in_range(r) or r.end == position:
                        break

            if len(statement_node.tokens) > index:
                token = cast(Token, statement_node.tokens[index])
                r = range_from_token(token)
                ws = whitespace_at_begin_of_token(token)
                if ws < 2:
                    return None

                ws_b = whitespace_from_begin_of_token(token)
                r.start.character += 2 if ws_b and ws_b[0] != "\t" else 1

                if position.is_in_range(r) or r.end == position:
                    return await create_items(
                        in_assign,
                        in_template,
                        range_from_token(statement_node.tokens[index + 1])
                        if r.end == position and len(statement_node.tokens) > index + 1
                        else None,
                        statement_node.tokens[index + 1]
                        if r.end == position and len(statement_node.tokens) > index + 1
                        else None,
                        position,
                    )

            index += 1

            if len(statement_node.tokens) > index:
                token = cast(Token, statement_node.tokens[index])
                if token.type == RobotToken.ASSIGN:
                    continue

            if len(statement_node.tokens) > index:
                token = cast(Token, statement_node.tokens[index])
                r = range_from_token(token)
                if position.is_in_range(r) or r.end == position:
                    return await create_items(in_assign, in_template, r, token, position)

                if len(statement_node.tokens) > index + 1:
                    second_token = cast(Token, statement_node.tokens[index + 1])
                    ws = whitespace_at_begin_of_token(second_token)
                    if ws < 1:
                        return None

                    r.end.character += 1
                    if position.is_in_range(r) or r.end == position:
                        return await create_items(in_assign, in_template, r, token, position)

        return None

    async def complete_TestCase(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        from robot.parsing.model.blocks import File, SettingSection, TestCase
        from robot.parsing.model.statements import Template, TestTemplate

        async def create_items(
            in_assign: bool, in_template: bool, r: Optional[Range], token: Optional[Token], pos: Position
        ) -> Union[List[CompletionItem], CompletionList, None]:
            return [
                e
                async for e in async_chain(
                    [] if in_assign else await self.create_keyword_snippet_completion_items(r),
                    [] if in_assign else await self.create_testcase_settings_completion_items(r),
                    [] if in_template else await self.create_keyword_completion_items(token, pos),
                )
            ]

        def check_in_template() -> bool:
            testcase_node = cast(TestCase, node)
            if any(
                template
                for template in testcase_node.body
                if isinstance(template, Template) and cast(Template, template).value is not None
            ):
                return True

            if any(
                file
                for file in nodes_at_position
                if isinstance(file, File)
                and any(
                    section
                    for section in cast(File, file).sections
                    if isinstance(section, SettingSection)
                    and any(
                        template
                        for template in cast(SettingSection, section).body
                        if isinstance(template, TestTemplate) and cast(TestTemplate, template).value is not None
                    )
                )
            ):
                return True

            return False

        in_template = check_in_template()

        return await self._complete_TestCase_or_Keyword(
            node, nodes_at_position, position, context, in_template, create_items
        )

    async def complete_Keyword(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        async def create_items(
            in_assign: bool, in_template: bool, r: Optional[Range], token: Optional[Token], pos: Position
        ) -> Union[List[CompletionItem], CompletionList, None]:
            return [
                e
                async for e in async_chain(
                    [] if in_assign else await self.create_keyword_snippet_completion_items(r),
                    [] if in_assign else await self.create_keyword_settings_completion_items(r),
                    [] if in_template else await self.create_keyword_completion_items(token, pos),
                )
            ]

        return await self._complete_TestCase_or_Keyword(node, nodes_at_position, position, context, False, create_items)

    async def _complete_SuiteSetup_or_SuiteTeardown_or_TestTemplate(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        from robot.parsing.model.statements import Statement

        statement_node = cast(Statement, node)
        if len(statement_node.tokens) > 1:
            token = cast(Token, statement_node.tokens[1])
            r = range_from_token(token)
            ws = whitespace_at_begin_of_token(token)
            if ws < 2:
                return None

            ws_b = whitespace_from_begin_of_token(token)
            r.start.character += 2 if ws_b and ws_b[0] != "\t" else 1

            if position.is_in_range(r) or r.end == position:
                return await self.create_keyword_completion_items(
                    statement_node.tokens[2] if r.end == position and len(statement_node.tokens) > 2 else None, position
                )

        if len(statement_node.tokens) > 2:
            token = cast(Token, statement_node.tokens[2])
            r = range_from_token(token)
            if position.is_in_range(r) or r.end == position:
                return await self.create_keyword_completion_items(token, position)

        return None

    async def complete_SuiteSetup(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:

        return await self._complete_SuiteSetup_or_SuiteTeardown_or_TestTemplate(
            node, nodes_at_position, position, context
        )

    async def complete_SuiteTeardown(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:

        return await self._complete_SuiteSetup_or_SuiteTeardown_or_TestTemplate(
            node, nodes_at_position, position, context
        )

    async def complete_TestSetup(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:

        return await self._complete_SuiteSetup_or_SuiteTeardown_or_TestTemplate(
            node, nodes_at_position, position, context
        )

    async def complete_TestTeardown(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:

        return await self._complete_SuiteSetup_or_SuiteTeardown_or_TestTemplate(
            node, nodes_at_position, position, context
        )

    async def complete_TestTemplate(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:

        return await self._complete_SuiteSetup_or_SuiteTeardown_or_TestTemplate(
            node, nodes_at_position, position, context
        )

    async def complete_Setup_or_Teardown_or_Template(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        from robot.parsing.model.statements import Statement

        statement_node = cast(Statement, node)
        if len(statement_node.tokens) > 2:
            token = cast(Token, statement_node.tokens[2])
            r = range_from_token(token)
            ws = whitespace_at_begin_of_token(token)
            if ws < 2:
                return None

            ws_b = whitespace_from_begin_of_token(token)
            r.start.character += 2 if ws_b and ws_b[0] != "\t" else 1

            if position.is_in_range(r) or r.end == position:
                return await self.create_keyword_completion_items(
                    statement_node.tokens[3] if r.end == position and len(statement_node.tokens) > 3 else None, position
                )

        if len(statement_node.tokens) > 3:
            token = cast(Token, statement_node.tokens[3])
            r = range_from_token(token)
            if position.is_in_range(r) or r.end == position:
                return await self.create_keyword_completion_items(token, position)

        return None

    async def complete_Setup(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:

        return await self.complete_Setup_or_Teardown_or_Template(node, nodes_at_position, position, context)

    async def complete_Teardown(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:

        return await self.complete_Setup_or_Teardown_or_Template(node, nodes_at_position, position, context)

    async def complete_Template(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:

        return await self.complete_Setup_or_Teardown_or_Template(node, nodes_at_position, position, context)

    async def complete_LibraryImport(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        from robot.parsing.lexer.tokens import Token
        from robot.parsing.model.statements import LibraryImport

        if self.document is None:
            return []

        import_node = cast(LibraryImport, node)
        import_token = import_node.get_token(Token.LIBRARY)
        if import_token is None:
            return []
        import_token_index = import_node.tokens.index(import_token)

        if len(import_node.tokens) > import_token_index + 2:
            name_token = import_node.tokens[import_token_index + 2]
            if not position.is_in_range(r := range_from_token(name_token)) and r.end != position:
                return None

        elif len(import_node.tokens) > import_token_index + 1:
            name_token = import_node.tokens[import_token_index + 1]
            if position.is_in_range(r := range_from_token(name_token)) or r.end == position:
                if whitespace_at_begin_of_token(name_token) > 1:

                    ws_b = whitespace_from_begin_of_token(name_token)
                    r.start.character += 2 if ws_b and ws_b[0] != "\t" else 1

                    if not position.is_in_range(r) and r.end != position:
                        return None
        else:
            return None

        pos = position.character - r.start.character
        text_before_position = str(name_token.value)[:pos].lstrip()

        if text_before_position != "" and all(c == "." for c in text_before_position):
            return None

        last_separator_index = (
            len(text_before_position)
            - next((i for i, c in enumerate(reversed(text_before_position)) if c in [".", "/", os.sep]), -1)
            - 1
        )

        first_part = (
            text_before_position[
                : last_separator_index + (1 if text_before_position[last_separator_index] in [".", "/", os.sep] else 0)
            ]
            if last_separator_index < len(text_before_position)
            else None
        )

        sep = text_before_position[last_separator_index] if last_separator_index < len(text_before_position) else ""

        imports_manger = await self.parent.documents_cache.get_imports_manager(self.document)

        try:
            list = await imports_manger.complete_library_import(
                first_part if first_part else None, str(self.document.uri.to_path().parent)
            )
            if not list:
                return None
        except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
            raise
        except BaseException:
            return None

        if text_before_position == "":
            r.start.character = position.character
        else:
            r.start.character += last_separator_index + 1 if last_separator_index < len(text_before_position) else 0

        return [
            CompletionItem(
                label=e.label,
                kind=CompletionItemKind.MODULE
                if e.kind in [CompleteResultKind.MODULE, CompleteResultKind.MODULE_INTERNAL]
                else CompletionItemKind.FILE
                if e.kind in [CompleteResultKind.FILE]
                else CompletionItemKind.FOLDER
                if e.kind in [CompleteResultKind.FOLDER]
                else None,
                detail=e.kind.value,
                sort_text=f"030_{e}",
                insert_text_format=InsertTextFormat.PLAINTEXT,
                text_edit=TextEdit(range=r, new_text=e.label) if r is not None else None,
                data={
                    "document_uri": str(self.document.uri),
                    "type": e.kind.name,
                    "name": ((first_part + sep) if first_part is not None else "") + e.label,
                },
            )
            for e in list
        ]

    async def complete_ResourceImport(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        from robot.parsing.lexer.tokens import Token
        from robot.parsing.model.statements import ResourceImport

        if self.document is None:
            return []

        import_node = cast(ResourceImport, node)
        import_token = import_node.get_token(Token.RESOURCE)
        if import_token is None:
            return []
        import_token_index = import_node.tokens.index(import_token)

        if len(import_node.tokens) > import_token_index + 2:
            name_token = import_node.tokens[import_token_index + 2]
            if not position.is_in_range(r := range_from_token(name_token)) and r.end != position:
                return None

        elif len(import_node.tokens) > import_token_index + 1:
            name_token = import_node.tokens[import_token_index + 1]
            if position.is_in_range(r := range_from_token(name_token)) or r.end == position:
                if whitespace_at_begin_of_token(name_token) > 1:

                    ws_b = whitespace_from_begin_of_token(name_token)
                    r.start.character += 2 if ws_b and ws_b[0] != "\t" else 1

                    if not position.is_in_range(r) and r.end != position:
                        return None
        else:
            return None

        pos = position.character - r.start.character
        text_before_position = str(name_token.value)[:pos].lstrip()

        if text_before_position != "" and all(c == "." for c in text_before_position):
            return None

        last_separator_index = (
            len(text_before_position)
            - next((i for i, c in enumerate(reversed(text_before_position)) if c in ["/", os.sep]), -1)
            - 1
        )

        first_part = (
            text_before_position[
                : last_separator_index + (1 if text_before_position[last_separator_index] in ["/", os.sep] else 0)
            ]
            if last_separator_index < len(text_before_position)
            else None
        )

        imports_manger = await self.parent.documents_cache.get_imports_manager(self.document)

        try:
            list = await imports_manger.complete_resource_import(
                first_part if first_part else None, str(self.document.uri.to_path().parent)
            )
            if not list:
                return None
        except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
            raise
        except BaseException:
            return None

        if text_before_position == "":
            r.start.character = position.character
        else:
            r.start.character += last_separator_index + 1 if last_separator_index < len(text_before_position) else 0

        return [
            CompletionItem(
                label=e.label,
                kind=CompletionItemKind.FILE
                if e.kind in [CompleteResultKind.RESOURCE]
                else CompletionItemKind.FILE
                if e.kind in [CompleteResultKind.FILE]
                else CompletionItemKind.FOLDER
                if e.kind in [CompleteResultKind.FOLDER]
                else None,
                detail=e.kind.value,
                sort_text=f"030_{e}",
                insert_text_format=InsertTextFormat.PLAINTEXT,
                text_edit=TextEdit(range=r, new_text=e.label) if r is not None else None,
                data={
                    "document_uri": str(self.document.uri),
                    "type": e.kind.name,
                    "name": ((first_part) if first_part is not None else "") + e.label,
                },
            )
            for e in list
        ]

    async def _complete_KeywordCall_or_Fixture(  # noqa: N802
        self,
        keyword_name_token_type: str,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Statement

        if context is None or context.trigger_kind != CompletionTriggerKind.INVOKED:
            return []

        if self.document is None:
            return []

        namespace = await self.parent.documents_cache.get_namespace(self.document)
        if namespace is None:
            return []

        kw_node = cast(Statement, node)

        tokens_at_position = get_tokens_at_position(kw_node, position)

        if not tokens_at_position:
            return None

        token_at_position = tokens_at_position[-1]

        if token_at_position.type not in [RobotToken.ARGUMENT, RobotToken.EOL, RobotToken.SEPARATOR]:
            return None

        token_at_position_index = kw_node.tokens.index(token_at_position)

        argument_token_index = token_at_position_index
        while argument_token_index >= 0 and kw_node.tokens[argument_token_index].type != RobotToken.ARGUMENT:
            argument_token_index -= 1

        arguments = kw_node.get_tokens(RobotToken.ARGUMENT)

        if argument_token_index >= 0:
            argument_token = kw_node.tokens[argument_token_index]
            if argument_token.type == RobotToken.ARGUMENT:
                argument_index = arguments.index(argument_token)
            else:
                argument_index = 0
        else:
            argument_index = -1

        if whitespace_at_begin_of_token(token_at_position) > 1:
            r = range_from_token(token_at_position)

            ws_b = whitespace_from_begin_of_token(token_at_position)
            r.start.character += 2 if ws_b and ws_b[0] != "\t" else 1

            if position.is_in_range(r) or r.end == position:
                argument_index += 1

        if argument_index < 0:
            return None

        result: Optional[Tuple[Optional[KeywordDoc], Token]]

        keyword_token = kw_node.get_token(keyword_name_token_type)
        if keyword_token is None:
            return None

        result = await self.get_keyworddoc_and_token_from_position(
            keyword_token.value,
            keyword_token,
            [cast(Token, t) for t in kw_node.get_tokens(RobotToken.ARGUMENT)],
            namespace,
            range_from_token(keyword_token).start,
            analyse_run_keywords=False,
        )

        if result is None or result[0] is None:
            return None

        if result[0].is_any_run_keyword():
            # TODO: complete run keyword
            # ks = await self.get_keyworddoc_and_token_from_position(
            #     keyword_token.value,
            #     keyword_token,
            #     [cast(Token, t) for t in kw_node.get_tokens(RobotToken.ARGUMENT)],
            #     namespace,
            #     position,
            #     analyse_run_keywords=True,
            # )
            pass
        r = range_from_token(token_at_position)
        r.start = position
        return [
            CompletionItem(
                label=f"{e.name}=",
                kind=CompletionItemKind.VARIABLE,
                # detail=e.detail,
                sort_text=f"02{i}_{e.name}=",
                insert_text_format=InsertTextFormat.PLAINTEXT,
                text_edit=TextEdit(range=r, new_text=f"{e.name}="),
                data={
                    "document_uri": str(self.document.uri),
                    "type": "Argument",
                    "name": e,
                },
            )
            for i, e in enumerate(result[0].args)
            if e.kind
            not in [
                KeywordArgumentKind.VAR_POSITIONAL,
                KeywordArgumentKind.VAR_NAMED,
                KeywordArgumentKind.NAMED_ONLY_MARKER,
                KeywordArgumentKind.POSITIONAL_ONLY_MARKER,
            ]
        ]

    async def complete_KeywordCall(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        from robot.parsing.lexer.tokens import Token as RobotToken

        return await self._complete_KeywordCall_or_Fixture(
            RobotToken.KEYWORD, node, nodes_at_position, position, context
        )

    async def complete_Fixture(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        from robot.parsing.lexer.tokens import Token as RobotToken

        return await self._complete_KeywordCall_or_Fixture(RobotToken.NAME, node, nodes_at_position, position, context)
