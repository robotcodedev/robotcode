from __future__ import annotations

import ast
import asyncio
import builtins
import itertools
import os
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    TypedDict,
    Union,
    cast,
)

from ....utils.async_itertools import async_chain, async_chain_iterator
from ....utils.logging import LoggingDescriptor
from ...common.decorators import language_id, trigger_characters
from ...common.lsp_types import (
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
from ...common.text_document import TextDocument
from ..configuration import CompletionConfig
from ..diagnostics.entities import VariableDefinitionType
from ..diagnostics.library_doc import (
    CompleteResultKind,
    KeywordArgumentKind,
    KeywordDoc,
    KeywordMatcher,
)
from ..diagnostics.namespace import DocumentType, Namespace
from ..utils.ast_utils import (
    HasTokens,
    Token,
    get_nodes_at_position,
    get_tokens_at_position,
    range_from_token,
    tokenize_variables,
    whitespace_at_begin_of_token,
    whitespace_from_begin_of_token,
)
from ..utils.version import get_robot_version
from .model_helper import ModelHelperMixin

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .protocol_part import RobotLanguageServerProtocolPart

DEFAULT_HEADER_STYLE = "*** {name}s ***"
DEFAULT_HEADER_STYLE_51 = "*** {name} ***"


class RobotCompletionProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.completion.collect.add(self.collect)
        parent.completion.resolve.add(self.resolve)

    async def get_config(self, document: TextDocument) -> CompletionConfig:
        if (folder := self.parent.workspace.get_workspace_folder(document.uri)) is not None:
            return await self.parent.workspace.get_configuration(CompletionConfig, folder.uri)

        return CompletionConfig()

    async def get_header_style(self, config: CompletionConfig) -> str:
        if config.header_style is not None:
            return config.header_style

        return DEFAULT_HEADER_STYLE if get_robot_version() < (6, 0) else DEFAULT_HEADER_STYLE_51

    @language_id("robotframework")
    @trigger_characters(
        [
            " ",
            "*",
            # "\n",
            "\t",
            ".",
            "/",
            "{",
            os.sep,
        ],
    )
    # @all_commit_characters(['\n'])
    @language_id("robotframework")
    @_logger.call
    async def collect(
        self, sender: Any, document: TextDocument, position: Position, context: Optional[CompletionContext]
    ) -> Union[List[CompletionItem], CompletionList, None]:

        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return None

        model = await self.parent.documents_cache.get_model(document, False)

        config = await self.get_config(document)

        return await CompletionCollector(
            self.parent, document, model, namespace, await self.get_header_style(config), config
        ).collect(
            position,
            context,
        )

    @language_id("robotframework")
    @_logger.call
    async def resolve(self, sender: Any, completion_item: CompletionItem) -> CompletionItem:
        if completion_item.data is not None:
            document_uri = completion_item.data.get("document_uri", None)
            if document_uri is not None:
                document = await self.parent.documents.get(document_uri)
                if document is not None:
                    namespace = await self.parent.documents_cache.get_namespace(document)
                    model = await self.parent.documents_cache.get_model(document, False)
                    if namespace is not None:
                        config = await self.get_config(document)

                        return await CompletionCollector(
                            self.parent, document, model, namespace, await self.get_header_style(config), config
                        ).resolve(completion_item)

        return completion_item


_CompleteMethod = Callable[
    [ast.AST, List[ast.AST], Position, Optional[CompletionContext]],
    Awaitable[Optional[Optional[List[CompletionItem]]]],
]

HEADERS = ["Test Case", "Setting", "Variable", "Keyword", "Comment", "Task"]


__snippets: Optional[Dict[str, List[str]]] = None


def get_snippets() -> Dict[str, List[str]]:
    global __snippets
    if __snippets is None:
        __snippets = {
            "FOR": [r"FOR  \${${1}}  ${2|IN,IN ENUMERATE,IN RANGE,IN ZIP|}  ${3:arg}", "$0", "END", ""],
            "IF": [r"IF  \${${1}}", "    $0", "END", ""],
        }

        if get_robot_version() >= (5, 0):
            __snippets.update(
                {
                    "TRYEX": ["TRY", "    $0", r"EXCEPT  message", "    ", "END", ""],
                    "TRYEXAS": ["TRY", "    $0", r"EXCEPT  message    AS    \${ex}", "    ", "END", ""],
                    "WHILE": [r"WHILE  ${1:expression}", "    $0", "END", ""],
                }
            )
    return __snippets


__reserved_keywords: Optional[List[str]] = None


def get_reserved_keywords() -> List[str]:
    global __reserved_keywords

    if __reserved_keywords is None:
        __reserved_keywords = [
            "FOR",
            "END",
            "IF",
            "ELSE",
            "ELIF",
            "ELSE IF",
        ]
        if get_robot_version() >= (5, 0):
            __reserved_keywords += [
                "TRY",
                "EXCEPT",
                "WHILE",
                "BREAK",
                "CONTINUE",
                "RETURN",
            ]

        __reserved_keywords = sorted(__reserved_keywords)
    return __reserved_keywords


class CompletionItemData(TypedDict):
    document_uri: str
    type: str
    name: str


class CompletionKeywordData(CompletionItemData):
    libname: Optional[str]
    hash: str
    id: str


class CompletionItemImportData(CompletionItemData):
    import_name: str
    args: Tuple[Any, ...]
    alias: Optional[str]
    hash: str
    id: str


class CompletionCollector(ModelHelperMixin):
    _logger = LoggingDescriptor()

    def __init__(
        self,
        parent: RobotLanguageServerProtocol,
        document: TextDocument,
        model: ast.AST,
        namespace: Namespace,
        header_style: str,
        config: CompletionConfig,
    ) -> None:
        self.parent = parent
        self.header_style = header_style
        self.document = document
        self.model = model
        self.namespace = namespace
        self.config = config

    async def _find_methods(self, cls: Type[Any]) -> AsyncGenerator[_CompleteMethod, None]:
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

        result_nodes = await get_nodes_at_position(self.model, position)

        result_nodes.reverse()

        async def iter_results() -> AsyncGenerator[List[CompletionItem], None]:
            for result_node in result_nodes:
                async for method in self._find_methods(type(result_node)):
                    r = await method(result_node, result_nodes, position, context)
                    if r is not None:
                        yield r

            r = await self.complete_default(result_nodes, position, context)
            if r is not None:
                yield r

        items = [e async for e in async_chain_iterator(iter_results())]
        result = CompletionList(is_incomplete=False, items=items)
        if not result.items:
            return None
        return result

    async def resolve(self, completion_item: CompletionItem) -> CompletionItem:
        data = cast(CompletionItemData, completion_item.data)

        if data is not None:
            document_uri = data.get("document_uri", None)
            if document_uri is not None:
                document = await self.parent.documents.get(document_uri)
                if document is not None and (comp_type := data.get("type", None)) is not None:
                    if comp_type in [
                        CompleteResultKind.MODULE.name,
                        CompleteResultKind.MODULE_INTERNAL.name,
                        CompleteResultKind.FILE.name,
                    ]:
                        if (lib_id := data.get("id", None)) is not None:
                            try:
                                lib_doc = next(
                                    (
                                        ld.library_doc
                                        for ld in (await self.namespace.get_libraries()).values()
                                        if str(id(ld.library_doc)) == lib_id
                                    ),
                                    None,
                                )
                                if lib_doc is not None:
                                    completion_item.documentation = MarkupContent(
                                        kind=MarkupKind.MARKDOWN, value=lib_doc.to_markdown(False)
                                    )

                            except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
                                raise
                            except BaseException as e:
                                completion_item.documentation = MarkupContent(
                                    kind=MarkupKind.MARKDOWN, value=f"Error:\n{e}"
                                )
                        elif (name := data.get("name", None)) is not None:
                            try:
                                lib_doc = await self.namespace.imports_manager.get_libdoc_for_library_import(
                                    name,
                                    (),
                                    str(document.uri.to_path().parent),
                                    variables=await self.namespace.get_resolvable_variables(),
                                )

                                if lib_doc is not None:
                                    completion_item.documentation = MarkupContent(
                                        kind=MarkupKind.MARKDOWN, value=lib_doc.to_markdown(False)
                                    )

                            except (SystemExit, KeyboardInterrupt):
                                raise
                            except BaseException:
                                pass

                    elif comp_type in [CompleteResultKind.RESOURCE.name]:

                        if (res_id := data.get("id", None)) is not None:
                            try:
                                lib_doc = next(
                                    (
                                        ld.library_doc
                                        for ld in (await self.namespace.get_resources()).values()
                                        if str(id(ld.library_doc)) == res_id
                                    ),
                                    None,
                                )

                                if lib_doc is not None:
                                    completion_item.documentation = MarkupContent(
                                        kind=MarkupKind.MARKDOWN, value=lib_doc.to_markdown(False)
                                    )

                            except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
                                raise
                            except BaseException as e:
                                completion_item.documentation = MarkupContent(
                                    kind=MarkupKind.MARKDOWN, value=f"Error:\n{e}"
                                )

                        elif (name := data.get("name", None)) is not None:
                            try:
                                lib_doc = await self.namespace.imports_manager.get_libdoc_for_resource_import(
                                    name,
                                    str(document.uri.to_path().parent),
                                    variables=await self.namespace.get_resolvable_variables(),
                                )

                                if lib_doc is not None:
                                    completion_item.documentation = MarkupContent(
                                        kind=MarkupKind.MARKDOWN, value=lib_doc.to_markdown(False)
                                    )

                            except (SystemExit, KeyboardInterrupt):
                                raise
                            except BaseException:
                                pass
                    elif comp_type in [CompleteResultKind.KEYWORD.name]:
                        kw_id = data.get("id", None)
                        if kw_id is not None:
                            try:
                                kw_doc = next(
                                    (kw for kw in await self.namespace.get_keywords() if str(id(kw)) == kw_id),
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

    async def create_headers_completion_items(self, range: Optional[Range]) -> List[CompletionItem]:
        if self.namespace.languages is None:
            headers: Iterable[str] = HEADERS
        else:
            languages = self.namespace.languages.languages

            if (
                self.config.filter_default_language
                and len(self.namespace.languages.languages) > 1
                and self.config.filter_default_language
            ):
                languages = [v for v in languages if v.code != "en"]

            headers = itertools.chain(*(lang.headers.keys() for lang in languages))

        return [
            CompletionItem(
                label=s[0],
                kind=CompletionItemKind.CLASS,
                detail="Header",
                # this is to get the english version in the documentation
                documentation=self.namespace.languages.headers.get(s[1])
                if self.namespace.languages is not None
                else None,
                sort_text=f"100_{s[1]}",
                insert_text_format=InsertTextFormat.PLAINTEXT,
                text_edit=TextEdit(
                    range=range,
                    new_text=s[0],
                )
                if range is not None
                else None,
            )
            for s in ((self.header_style.format(name=k), k) for k in (v.title() for v in headers))
        ]

    async def create_environment_variables_completion_items(self, range: Optional[Range]) -> List[CompletionItem]:
        return [
            CompletionItem(
                label=s,
                kind=CompletionItemKind.VARIABLE,
                detail="Variable",
                sort_text=f"035_{s}",
                insert_text_format=InsertTextFormat.PLAINTEXT,
                text_edit=TextEdit(
                    range=range,
                    new_text=s,
                )
                if range is not None
                else None,
            )
            for s in self.namespace.imports_manager.environment.keys()
        ]

    _VARIABLE_COMPLETION_SORT_TEXT_PREFIX = {
        VariableDefinitionType.LOCAL_VARIABLE: "033",
        VariableDefinitionType.ARGUMENT: "034",
        VariableDefinitionType.VARIABLE: "035",
        VariableDefinitionType.IMPORTED_VARIABLE: "036",
        VariableDefinitionType.COMMAND_LINE_VARIABLE: "037",
        VariableDefinitionType.BUILTIN_VARIABLE: "038",
        VariableDefinitionType.ENVIRONMENT_VARIABLE: "039",
    }

    async def create_variables_completion_items(
        self, range: Range, nodes: List[ast.AST], position: Position
    ) -> List[CompletionItem]:
        if self.document is None:
            return []

        return [
            CompletionItem(
                label=s.name,
                kind=CompletionItemKind.VARIABLE,
                detail=f"{s.type.value}",
                sort_text=f"{self._VARIABLE_COMPLETION_SORT_TEXT_PREFIX.get(s.type, '035')}_{s.name[2:-1]}",
                insert_text_format=InsertTextFormat.PLAINTEXT,
                text_edit=TextEdit(
                    range=range,
                    new_text=s.name[2:-1],
                ),
                filter_text=s.name[2:-1] if range is not None else None,
            )
            for s in (await self.namespace.get_variable_matchers(list(reversed(nodes)), position)).values()
            if s.name is not None and (s.name_token is None or not position.is_in_range(range_from_token(s.name_token)))
        ]

    async def create_settings_completion_items(self, range: Optional[Range]) -> List[CompletionItem]:
        from robot.parsing.lexer.settings import (
            InitFileSettings,
            ResourceFileSettings,
            TestCaseFileSettings,
        )

        doc_type = await self.parent.documents_cache.get_document_type(self.document)

        settings_class = TestCaseFileSettings
        if doc_type == DocumentType.RESOURCE:
            settings_class = ResourceFileSettings
        elif doc_type == DocumentType.INIT:
            settings_class = InitFileSettings

        settings = {*settings_class.names, *settings_class.aliases.keys()}

        if self.namespace.languages is not None:

            if self.config.filter_default_language and len(self.namespace.languages.languages) > 1:
                languages = self.namespace.languages.languages

                if self.config.filter_default_language:
                    languages = [v for v in languages if v.code != "en"]

                items: Iterable[Tuple[str, str]] = itertools.chain(*(lang.settings.items() for lang in languages))
            else:
                items = self.namespace.languages.settings.items()

            settings = {k.title() for k, v in items if v in settings}

        return [
            CompletionItem(
                label=setting,
                kind=CompletionItemKind.KEYWORD,
                detail="Setting",
                documentation=self.namespace.languages.settings.get(setting)
                if self.namespace.languages is not None
                else None,
                sort_text=f"090_{setting}",
                insert_text_format=InsertTextFormat.PLAINTEXT,
                text_edit=TextEdit(range=range, new_text=setting) if range is not None else None,
            )
            for setting in settings
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
            for snippet_name, snippet_value in get_snippets().items()
        ]

    async def create_testcase_settings_completion_items(self, range: Optional[Range]) -> List[CompletionItem]:
        from robot.parsing.lexer.settings import TestCaseSettings

        settings = {*TestCaseSettings.names, *TestCaseSettings.aliases.keys()}

        if self.namespace.languages is not None:

            if self.config.filter_default_language and len(self.namespace.languages.languages) > 1:
                languages = self.namespace.languages.languages

                if self.config.filter_default_language:
                    languages = [v for v in languages if v.code != "en"]

                items: Iterable[Tuple[str, str]] = itertools.chain(*(lang.settings.items() for lang in languages))
            else:
                items = self.namespace.languages.settings.items()

            settings = {k.title() for k, v in items if v in settings}

        return [
            CompletionItem(
                label=f"[{setting}]",
                kind=CompletionItemKind.KEYWORD,
                documentation=self.namespace.languages.settings.get(setting)
                if self.namespace.languages is not None
                else None,
                detail="Setting",
                sort_text=f"070_{setting}",
                insert_text_format=InsertTextFormat.PLAINTEXT,
                text_edit=TextEdit(range=range, new_text=f"[{setting}]") if range is not None else None,
            )
            for setting in settings
        ]

    async def create_bdd_prefix_completion_items(self, range: Optional[Range]) -> List[CompletionItem]:
        prefixes = {"Given", "When", "Then", "And", "But"}

        if self.namespace.languages is not None:
            prefixes.update(self.namespace.languages.bdd_prefixes)

        return [
            CompletionItem(
                label=prefix,
                kind=CompletionItemKind.UNIT,
                detail="BDD Prefix",
                sort_text=f"080_{prefix}",
                insert_text_format=InsertTextFormat.PLAINTEXT,
                text_edit=TextEdit(range=range, new_text=f"{prefix} ") if range is not None else None,
            )
            for prefix in prefixes
        ]

    async def create_keyword_settings_completion_items(self, range: Optional[Range]) -> List[CompletionItem]:
        from robot.parsing.lexer.settings import KeywordSettings

        settings = {*KeywordSettings.names, *KeywordSettings.aliases.keys()}

        if self.namespace.languages is not None:

            if self.config.filter_default_language and len(self.namespace.languages.languages) > 1:
                languages = self.namespace.languages.languages

                if self.config.filter_default_language:
                    languages = [v for v in languages if v.code != "en"]

                items: Iterable[Tuple[str, str]] = itertools.chain(*(lang.settings.items() for lang in languages))
            else:
                items = self.namespace.languages.settings.items()

            settings = {k.title() for k, v in items if v in settings}

        return [
            CompletionItem(
                label=f"[{setting}]",
                kind=CompletionItemKind.KEYWORD,
                documentation=self.namespace.languages.settings.get(setting)
                if self.namespace.languages is not None
                else None,
                detail="Setting",
                sort_text=f"070_{setting}",
                insert_text_format=InsertTextFormat.PLAINTEXT,
                text_edit=TextEdit(range=range, new_text=f"[{setting}]") if range is not None else None,
            )
            for setting in settings
        ]

    def get_keyword_snipped_text(self, kw: KeywordDoc, in_template: bool) -> str:
        from robot.variables.search import VariableIterator

        if not kw.is_embedded:
            return kw.name

        result = ""
        after: Optional[str] = None
        for index, (before, variable, after) in enumerate(
            VariableIterator(kw.name, identifiers="$", ignore_errors=True)
        ):
            var_name = variable[2:-1].split(":", 1)[0]
            result += before
            result += "${" + str(index + 1) + ":"
            if in_template:
                result += "\\${"

            result += var_name

            if in_template:
                result += "\\}"

            result += "}"

        if after:
            result += after

        return result

    async def create_keyword_completion_items(
        self,
        token: Optional[Token],
        position: Position,
        *,
        add_reserverd: bool = True,
        add_none: bool = False,
        in_template: bool = False,
        add_bdd_prefixes: bool = True,
    ) -> List[CompletionItem]:
        result: List[CompletionItem] = []
        if self.document is None:
            return []

        r: Optional[Range] = None

        has_bdd = False
        bdd_token = None

        if token is not None:
            old_token = token
            bdd_token, token = self.split_bdd_prefix(self.namespace, token)

            if token is not None and token.value == "":
                token = None

            if bdd_token is not None and position.character > range_from_token(bdd_token).end.character:
                has_bdd = True

            if not has_bdd and token is None:
                token = old_token

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

                    libraries = await self.namespace.get_libraries()

                    library_name_matcher = KeywordMatcher(library_name)
                    library_name = next(
                        (e for e in libraries.keys() if library_name_matcher == KeywordMatcher(e)), library_name
                    )

                    if library_name in libraries:
                        r.start.character = lib_name_index + 1
                        for kw in libraries[library_name].library_doc.keywords.values():
                            if kw.is_error_handler:
                                continue
                            result.append(
                                CompletionItem(
                                    label=kw.name,
                                    kind=CompletionItemKind.FUNCTION,
                                    detail=f"{CompleteResultKind.KEYWORD.value} "
                                    f"{f'({kw.libname})' if kw.libname is not None else ''}",
                                    sort_text=f"020_{kw.name}",
                                    insert_text_format=InsertTextFormat.PLAINTEXT
                                    if not kw.is_embedded
                                    else InsertTextFormat.SNIPPET,
                                    text_edit=TextEdit(
                                        range=r,
                                        new_text=kw.name
                                        if not kw.is_embedded
                                        else self.get_keyword_snipped_text(kw, in_template),
                                    )
                                    if r is not None
                                    else None,
                                    data=CompletionKeywordData(
                                        document_uri=str(self.document.uri),
                                        type=CompleteResultKind.KEYWORD.name,
                                        libname=kw.libname,
                                        name=kw.name,
                                        hash=str(hash(kw)),
                                        id=str(id(kw)),
                                    ),
                                )
                            )

                    resources = {
                        k: v
                        for k, v in (await self.namespace.get_resources()).items()
                        if library_name_matcher == KeywordMatcher(v.name)
                    }

                    if resources:
                        r.start.character = lib_name_index + 1
                        for res in resources.values():
                            for kw in res.library_doc.keywords.values():
                                if kw.is_error_handler:
                                    continue

                                result.append(
                                    CompletionItem(
                                        label=kw.name,
                                        kind=CompletionItemKind.FUNCTION,
                                        detail=f"{CompleteResultKind.KEYWORD.value} "
                                        f"{f'({kw.libname})' if kw.libname is not None else ''}",
                                        sort_text=f"020_{kw.name}",
                                        insert_text_format=InsertTextFormat.PLAINTEXT
                                        if not kw.is_embedded
                                        else InsertTextFormat.SNIPPET,
                                        text_edit=TextEdit(
                                            range=r,
                                            new_text=kw.name
                                            if not kw.is_embedded
                                            else self.get_keyword_snipped_text(kw, in_template),
                                        ),
                                        data=CompletionKeywordData(
                                            document_uri=str(self.document.uri),
                                            type=CompleteResultKind.KEYWORD.name,
                                            libname=kw.libname,
                                            name=kw.name,
                                            hash=str(hash(kw)),
                                            id=str(id(kw)),
                                        ),
                                    )
                                )

                    return result

        if r is None:
            r = Range(position, position)

        for kw in await self.namespace.get_keywords():
            if kw.is_error_handler:
                continue

            result.append(
                CompletionItem(
                    label=kw.name,
                    kind=CompletionItemKind.FUNCTION,
                    detail=f"{CompleteResultKind.KEYWORD.value} {f'({kw.libname})' if kw.libname is not None else ''}",
                    deprecated=kw.is_deprecated,
                    sort_text=f"020_{kw.name}",
                    insert_text_format=InsertTextFormat.PLAINTEXT if not kw.is_embedded else InsertTextFormat.SNIPPET,
                    text_edit=TextEdit(
                        range=r,
                        new_text=kw.name if not kw.is_embedded else self.get_keyword_snipped_text(kw, in_template),
                    ),
                    data=CompletionKeywordData(
                        document_uri=str(self.document.uri),
                        type=CompleteResultKind.KEYWORD.name,
                        libname=kw.libname,
                        name=kw.name,
                        hash=str(hash(kw)),
                        id=str(id(kw)),
                    ),
                )
            )

        for k, v in (await self.namespace.get_libraries()).items():
            result.append(
                CompletionItem(
                    label=k,
                    kind=CompletionItemKind.MODULE,
                    detail="Library",
                    sort_text=f"030_{v.name}",
                    deprecated=v.library_doc.is_deprecated,
                    insert_text_format=InsertTextFormat.PLAINTEXT,
                    text_edit=TextEdit(range=r, new_text=k),
                    data=CompletionItemImportData(
                        document_uri=str(self.document.uri),
                        type=CompleteResultKind.MODULE.name,
                        name=v.name,
                        import_name=v.import_name,
                        args=v.args,
                        alias=v.alias,
                        id=str(id(v.library_doc)),
                        hash=str(hash(v.library_doc)),
                    ),
                )
            )

        for k, v in (await self.namespace.get_resources()).items():
            result.append(
                CompletionItem(
                    label=v.name,
                    kind=CompletionItemKind.MODULE,
                    detail="Resource",
                    deprecated=v.library_doc.is_deprecated,
                    sort_text=f"030_{v.name}",
                    insert_text_format=InsertTextFormat.PLAINTEXT,
                    text_edit=TextEdit(range=r, new_text=v.name),
                    data=CompletionItemImportData(
                        document_uri=str(self.document.uri),
                        type=CompleteResultKind.RESOURCE.name,
                        name=k,
                        import_name=v.import_name,
                        args=(),
                        alias=None,
                        id=str(id(v.library_doc)),
                        hash=str(hash(v.library_doc)),
                    ),
                )
            )

        if add_none:
            result.append(
                CompletionItem(
                    label="NONE",
                    kind=CompletionItemKind.KEYWORD,
                    sort_text="998_NONE",
                    insert_text_format=InsertTextFormat.PLAINTEXT,
                    text_edit=TextEdit(range=r, new_text="NONE"),
                )
            )

        if add_bdd_prefixes and not has_bdd:
            result += await self.create_bdd_prefix_completion_items(
                range_from_token(token) if token is not None else None
            )

        if add_reserverd:
            for k in get_reserved_keywords():
                result.append(
                    CompletionItem(
                        label=k,
                        kind=CompletionItemKind.KEYWORD,
                        sort_text=f"999_{k}",
                        insert_text_format=InsertTextFormat.PLAINTEXT,
                        text_edit=TextEdit(range=r, new_text=k),
                    )
                )

        return result

    def get_variable_token(self, token: Token) -> Optional[Token]:
        from robot.parsing.lexer.tokens import Token as RobotToken

        return next(
            (
                v
                for v in itertools.dropwhile(
                    lambda t: t.type in RobotToken.NON_DATA_TOKENS,
                    tokenize_variables(token, ignore_errors=True),
                )
                if v.type == RobotToken.VARIABLE
            ),
            None,
        )

    async def complete_default(
        self,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Optional[List[CompletionItem]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Arguments, Statement

        if len(nodes_at_position) > 1 and isinstance(nodes_at_position[0], Statement):
            statement_node = cast(Statement, nodes_at_position[0])
            if len(statement_node.tokens) > 0:
                token = cast(Token, statement_node.tokens[0])
                r = range_from_token(token)
                value = token.value.strip()
                only_stars = value is not None and "*" in value and all(v == "*" for v in value)
                if (
                    r.start.character == 0
                    and (position.is_in_range(r))
                    and (only_stars or value.startswith("*") or position.character == 0)
                ):
                    return await self.create_headers_completion_items(r)
                elif len(statement_node.tokens) > 1 and only_stars:
                    r1 = range_from_token(statement_node.tokens[1])
                    ws = whitespace_at_begin_of_token(statement_node.tokens[1])
                    if ws > 0:
                        r1.end.character = r1.start.character + ws
                        if position.is_in_range(r1):
                            r.end = r1.end
                            return await self.create_headers_completion_items(r)

        elif position.character == 0:
            return await self.create_headers_completion_items(None)

        if len(nodes_at_position) > 1 and isinstance(nodes_at_position[0], HasTokens):
            node = nodes_at_position[0]
            tokens_at_position = get_tokens_at_position(node, position)
            token_at_position = tokens_at_position[-1]

            if isinstance(node, Arguments):
                arg = self.get_variable_token(token_at_position)
                if arg is not None and position <= range_from_token(arg).end:
                    return None

            token_at_position_index = tokens_at_position.index(token_at_position)
            while token_at_position.type in [RobotToken.EOL]:
                token_at_position_index -= 1
                if token_at_position_index < 0:
                    break
                token_at_position = tokens_at_position[token_at_position_index]

            if token_at_position.type not in [
                RobotToken.NAME,
                RobotToken.ARGUMENT,
                RobotToken.KEYWORD,
                RobotToken.ASSIGN,
            ]:
                return None

            close_brace_index_before = token_at_position.value.rfind(
                "}", 0, position.character - token_at_position.col_offset
            )

            open_brace_index = token_at_position.value.rfind("{", 0, position.character - token_at_position.col_offset)
            if (
                open_brace_index > close_brace_index_before
                and open_brace_index >= 1
                and token_at_position.value[open_brace_index - 1] in "$@&%"
            ):
                variable_end = token_at_position.value.find("}", open_brace_index + 1)
                contains_spezial = any(
                    a
                    for a in itertools.takewhile(lambda b: b != "}", token_at_position.value[open_brace_index + 1 :])
                    if a in "+-*/"
                )
                range = Range(
                    start=Position(
                        line=position.line,
                        character=token_at_position.col_offset + open_brace_index + 1,
                    ),
                    end=position
                    if contains_spezial or variable_end < 0
                    else Position(
                        line=position.line,
                        character=(token_at_position.col_offset + variable_end)
                        if not contains_spezial
                        else token_at_position.end_col_offset,
                    ),
                )
                if token_at_position.value[open_brace_index - 1] == "%":
                    return await self.create_environment_variables_completion_items(range)
                return await self.create_variables_completion_items(range, nodes_at_position, position)

        return None

    async def complete_SettingSection(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        from robot.parsing.model.statements import SectionHeader, Statement

        # TODO should this be configurable?
        if (
            context is not None
            and context.trigger_kind == CompletionTriggerKind.TRIGGERCHARACTER
            and context.trigger_character in [" ", "\t"]
        ):
            return None

        if nodes_at_position.index(node) > 0 and not isinstance(nodes_at_position[0], SectionHeader):
            statement_node = cast(Statement, nodes_at_position[0])
            if len(statement_node.tokens) > 0:
                token = cast(Token, statement_node.tokens[0])
                r = range_from_token(token)
                if position.is_in_range(r):
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

        # TODO should this be configurable?
        if (
            context is not None
            and context.trigger_kind == CompletionTriggerKind.TRIGGERCHARACTER
            and context.trigger_character in [" ", "\t"]
        ):
            return None

        index = 0
        in_assign = False

        statement_node = cast(Statement, nodes_at_position[0])
        if isinstance(statement_node, (TestCaseName, KeywordName)):
            index += 1
        if not isinstance(statement_node, HasTokens):
            return None

        while index < len(statement_node.tokens):
            if len(statement_node.tokens) > index:
                token = statement_node.tokens[index]
                if token.type == RobotToken.ASSIGN:
                    index += 1
                    in_assign = True
                    r = range_from_token(token)
                    if position.is_in_range(r):
                        break

            if len(statement_node.tokens) > index:
                token = statement_node.tokens[index]
                r = range_from_token(token)
                ws = whitespace_at_begin_of_token(token)
                if ws < 2:
                    return None

                ws_b = whitespace_from_begin_of_token(token)
                r.start.character += 2 if ws_b and ws_b[0] != "\t" else 1

                if position.is_in_range(r):
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
                token = statement_node.tokens[index]
                if token.type == RobotToken.ASSIGN:
                    continue

            if len(statement_node.tokens) > index:
                token = statement_node.tokens[index]

                r = range_from_token(token)
                if position.is_in_range(r):
                    return await create_items(in_assign, in_template, r, token, position)

                if len(statement_node.tokens) > index + 1:
                    second_token = statement_node.tokens[index + 1]
                    ws = whitespace_at_begin_of_token(second_token)
                    if ws < 1:
                        return None

                    r.end.character += 1
                    if position.is_in_range(r):
                        return await create_items(
                            in_assign,
                            in_template,
                            r,
                            token,
                            position,
                        )

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
        from robot.parsing.model.statements import Statement, TestTemplate

        # TODO should this be configurable?
        if (
            context is not None
            and context.trigger_kind == CompletionTriggerKind.TRIGGERCHARACTER
            and context.trigger_character in [" ", "\t"]
        ):
            return None

        statement_node = cast(Statement, node)
        if len(statement_node.tokens) > 1:
            token = cast(Token, statement_node.tokens[1])
            r = range_from_token(token)
            ws = whitespace_at_begin_of_token(token)
            if ws < 2:
                return None

            ws_b = whitespace_from_begin_of_token(token)
            r.start.character += 2 if ws_b and ws_b[0] != "\t" else 1

            if position.is_in_range(r):
                return await self.create_keyword_completion_items(
                    statement_node.tokens[2] if r.end == position and len(statement_node.tokens) > 2 else None,
                    position,
                    add_reserverd=False,
                    add_none=True,
                    in_template=isinstance(node, TestTemplate),
                )

        if len(statement_node.tokens) > 2:
            token = cast(Token, statement_node.tokens[2])

            token = self.strip_bdd_prefix(self.namespace, token)

            r = range_from_token(token)
            if position.is_in_range(r):
                return await self.create_keyword_completion_items(
                    token,
                    position,
                    add_reserverd=False,
                    add_none=True,
                    in_template=isinstance(node, TestTemplate),
                )

        if len(statement_node.tokens) > 3:
            second_token = statement_node.tokens[3]
            ws = whitespace_at_begin_of_token(second_token)
            if ws < 1:
                return None

            r.end.character += 1
            if position.is_in_range(r):
                return await self.create_keyword_completion_items(
                    token,
                    position,
                    add_reserverd=False,
                    add_none=True,
                    in_template=isinstance(node, TestTemplate),
                )

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
        from robot.parsing.model.statements import Statement, Template

        # TODO should this be configurable?
        if (
            context is not None
            and context.trigger_kind == CompletionTriggerKind.TRIGGERCHARACTER
            and context.trigger_character in [" ", "\t"]
        ):
            return None

        statement_node = cast(Statement, node)
        if len(statement_node.tokens) > 2:
            token = cast(Token, statement_node.tokens[2])

            r = range_from_token(token)
            ws = whitespace_at_begin_of_token(token)
            if ws < 2:
                return None

            ws_b = whitespace_from_begin_of_token(token)
            r.start.character += 2 if ws_b and ws_b[0] != "\t" else 1

            if position.is_in_range(r):
                return await self.create_keyword_completion_items(
                    statement_node.tokens[3] if r.end == position and len(statement_node.tokens) > 3 else None,
                    position,
                    add_reserverd=False,
                    add_none=True,
                    in_template=isinstance(node, Template),
                )

        if len(statement_node.tokens) > 3:
            token = cast(Token, statement_node.tokens[3])

            token = self.strip_bdd_prefix(self.namespace, token)

            r = range_from_token(token)
            if position.is_in_range(r):
                return await self.create_keyword_completion_items(
                    token, position, add_reserverd=False, add_none=True, in_template=isinstance(node, Template)
                )

        if len(statement_node.tokens) > 4:
            second_token = statement_node.tokens[4]
            ws = whitespace_at_begin_of_token(second_token)
            if ws < 1:
                return None

            r.end.character += 1
            if position.is_in_range(r):
                return await self.create_keyword_completion_items(
                    token,
                    position,
                    add_reserverd=False,
                    add_none=True,
                    in_template=isinstance(node, Template),
                )

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

        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import LibraryImport, Statement

        if self.document is None:
            return []

        import_node = cast(LibraryImport, node)
        import_token = import_node.get_token(RobotToken.LIBRARY)
        if import_token is None:
            return []

        if position.is_in_range(range_from_token(import_token)):
            return []

        import_token_index = import_node.tokens.index(import_token)

        async def complete_import() -> Optional[List[CompletionItem]]:
            if self.document is None:
                return None

            if len(import_node.tokens) > import_token_index + 2:
                name_token = import_node.tokens[import_token_index + 2]
                if not position.is_in_range(r := range_from_token(name_token)):
                    return None

            elif len(import_node.tokens) > import_token_index + 1:
                name_token = import_node.tokens[import_token_index + 1]
                if position.is_in_range(r := range_from_token(name_token)):
                    if whitespace_at_begin_of_token(name_token) > 1:

                        ws_b = whitespace_from_begin_of_token(name_token)
                        r.start.character += 2 if ws_b and ws_b[0] != "\t" else 1

                        if not position.is_in_range(r):
                            return None
                    else:
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
                    : last_separator_index
                    + (1 if text_before_position[last_separator_index] in [".", "/", os.sep] else 0)
                ]
                if last_separator_index < len(text_before_position)
                else None
            )

            try:
                complete_list = await self.namespace.imports_manager.complete_library_import(
                    first_part if first_part else None,
                    str(self.document.uri.to_path().parent),
                    await self.namespace.get_resolvable_variables(nodes_at_position, position),
                )
                if not complete_list:
                    return None
            except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
                raise
            except BaseException as e:
                self._logger.exception(e)
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
                    data=CompletionItemData(
                        document_uri=str(self.document.uri),
                        type=e.kind.name,
                        name=((first_part) if first_part is not None else "") + e.label,
                    ),
                )
                for e in complete_list
            ]

        async def complete_arguments() -> Optional[List[CompletionItem]]:
            if self.document is None:
                return None

            if (
                import_node.name is None
                or position <= range_from_token(import_node.get_token(RobotToken.NAME)).extend(end_character=1).end
            ):
                return None

            with_name_token = next((v for v in import_node.tokens if v.value == "WITH NAME"), None)
            if with_name_token is not None and position >= range_from_token(with_name_token).start:
                return None

            if context is None or context.trigger_kind != CompletionTriggerKind.INVOKED:
                return []

            kw_node = cast(Statement, node)

            tokens_at_position = get_tokens_at_position(kw_node, position)

            if not tokens_at_position:
                return None

            token_at_position = tokens_at_position[-1]

            if token_at_position.type not in [RobotToken.ARGUMENT, RobotToken.EOL, RobotToken.SEPARATOR]:
                return None

            if (
                token_at_position.type == RobotToken.EOL
                and len(tokens_at_position) > 1
                and tokens_at_position[-2].type == RobotToken.KEYWORD
            ):
                return None

            token_at_position_index = kw_node.tokens.index(token_at_position)

            argument_token_index = token_at_position_index
            while argument_token_index >= 0 and kw_node.tokens[argument_token_index].type != RobotToken.ARGUMENT:
                argument_token_index -= 1

            argument_token: Optional[RobotToken] = None
            if argument_token_index >= 0:
                argument_token = kw_node.tokens[argument_token_index]

            completion_range = range_from_token(argument_token or token_at_position)
            completion_range.end = range_from_token(token_at_position).end
            if (w := whitespace_at_begin_of_token(token_at_position)) > 0:
                if w > 1 and range_from_token(token_at_position).start.character + 1 < position.character:
                    completion_range.start = position
                elif completion_range.start != position:
                    return None
            else:
                if "=" in (argument_token or token_at_position).value:
                    equal_index = (argument_token or token_at_position).value.index("=")
                    if completion_range.start.character + equal_index < position.character:
                        return None
                    else:
                        completion_range.end.character = completion_range.start.character + equal_index + 1
                else:
                    completion_range.end = position

            try:
                libdoc = await self.namespace.get_imported_library_libdoc(
                    import_node.name, import_node.args, import_node.alias
                )

            except (SystemExit, KeyboardInterrupt, asyncio.CancelledError):
                raise
            except BaseException as e:
                self._logger.exception(e)
                return None

            if libdoc is not None:
                init = next((v for v in libdoc.inits.values()), None)

                if init:
                    return [
                        CompletionItem(
                            label=f"{e.name}=",
                            kind=CompletionItemKind.VARIABLE,
                            sort_text=f"010{i}_{e.name}",
                            filter_text=e.name,
                            insert_text_format=InsertTextFormat.PLAINTEXT,
                            text_edit=TextEdit(range=completion_range, new_text=f"{e.name}="),
                            data=CompletionItemData(
                                document_uri=str(self.document.uri),
                                type="Argument",
                                name=e.name,
                            ),
                        )
                        for i, e in enumerate(init.args)
                        if e.kind
                        not in [
                            KeywordArgumentKind.VAR_POSITIONAL,
                            KeywordArgumentKind.VAR_NAMED,
                            KeywordArgumentKind.NAMED_ONLY_MARKER,
                            KeywordArgumentKind.POSITIONAL_ONLY_MARKER,
                        ]
                    ]

            return None

        async def complete_with_name() -> Optional[List[CompletionItem]]:
            if self.document is None:
                return None

            if context is None or context.trigger_kind != CompletionTriggerKind.INVOKED:
                return []

            if get_robot_version() >= (6, 0):
                namespace_marker = ["AS", "WITH NAME"]
            else:
                namespace_marker = ["WITH NAME"]

            if import_node.name and not any(v for v in import_node.tokens if v.value in namespace_marker):
                name_token = import_node.get_token(RobotToken.NAME)
                if position >= range_from_token(name_token).extend(end_character=2).end:
                    return [
                        CompletionItem(
                            label="AS" if get_robot_version() >= (6, 0) else "WITH NAME",
                            kind=CompletionItemKind.KEYWORD,
                            # detail=e.detail,
                            sort_text="03_NAMESPACE_MARKER",
                            insert_text_format=InsertTextFormat.PLAINTEXT,
                        )
                    ]
            return []

        result = await complete_import() or []
        result.extend(await complete_arguments() or [])
        result.extend(await complete_with_name() or [])

        return result

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

        if position.is_in_range(range_from_token(import_token)):
            return []

        import_token_index = import_node.tokens.index(import_token)

        if len(import_node.tokens) > import_token_index + 2:
            name_token = import_node.tokens[import_token_index + 2]
            if not position.is_in_range(r := range_from_token(name_token)):
                return None

        elif len(import_node.tokens) > import_token_index + 1:
            name_token = import_node.tokens[import_token_index + 1]
            if position.is_in_range(r := range_from_token(name_token)):
                if whitespace_at_begin_of_token(name_token) > 1:

                    ws_b = whitespace_from_begin_of_token(name_token)
                    r.start.character += 2 if ws_b and ws_b[0] != "\t" else 1

                    if not position.is_in_range(r):
                        return None
                else:
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

        try:
            complete_list = await self.namespace.imports_manager.complete_resource_import(
                first_part if first_part else None,
                str(self.document.uri.to_path().parent),
                await self.namespace.get_resolvable_variables(nodes_at_position, position),
            )
            if not complete_list:
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
                data=CompletionItemData(
                    document_uri=str(self.document.uri),
                    type=e.kind.name,
                    name=((first_part) if first_part is not None else "") + e.label,
                ),
            )
            for e in complete_list
        ]

    async def complete_VariablesImport(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:

        from robot.parsing.lexer.tokens import Token
        from robot.parsing.model.statements import VariablesImport

        if self.document is None:
            return []

        import_node = cast(VariablesImport, node)
        import_token = import_node.get_token(Token.VARIABLES)

        if import_token is None:
            return []

        if position.is_in_range(range_from_token(import_token)):
            return []

        import_token_index = import_node.tokens.index(import_token)

        if len(import_node.tokens) > import_token_index + 2:
            name_token = import_node.tokens[import_token_index + 2]
            if not position.is_in_range(r := range_from_token(name_token)):
                return None

        elif len(import_node.tokens) > import_token_index + 1:
            name_token = import_node.tokens[import_token_index + 1]
            if position.is_in_range(r := range_from_token(name_token)):
                if whitespace_at_begin_of_token(name_token) > 1:

                    ws_b = whitespace_from_begin_of_token(name_token)
                    r.start.character += 2 if ws_b and ws_b[0] != "\t" else 1

                    if not position.is_in_range(r):
                        return None
                else:
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

        try:
            complete_list = await self.namespace.imports_manager.complete_variables_import(
                first_part if first_part else None,
                str(self.document.uri.to_path().parent),
                await self.namespace.get_resolvable_variables(nodes_at_position, position),
            )
            if not complete_list:
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
                if e.kind in [CompleteResultKind.VARIABLES]
                else CompletionItemKind.FILE
                if e.kind in [CompleteResultKind.FILE]
                else CompletionItemKind.FOLDER
                if e.kind in [CompleteResultKind.FOLDER]
                else None,
                detail=e.kind.value,
                sort_text=f"030_{e}",
                insert_text_format=InsertTextFormat.PLAINTEXT,
                text_edit=TextEdit(range=r, new_text=e.label) if r is not None else None,
                data=CompletionItemData(
                    document_uri=str(self.document.uri),
                    type=e.kind.name,
                    name=((first_part) if first_part is not None else "") + e.label,
                ),
            )
            for e in complete_list
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

        kw_node = cast(Statement, node)

        keyword_token = kw_node.get_token(keyword_name_token_type)
        if keyword_token is None:
            return None

        tokens_at_position = get_tokens_at_position(kw_node, position)

        if not tokens_at_position:
            return None

        token_at_position = tokens_at_position[-1]

        if token_at_position.type not in [RobotToken.ARGUMENT, RobotToken.EOL, RobotToken.SEPARATOR]:
            return None

        if (
            token_at_position.type in [RobotToken.EOL, RobotToken.SEPARATOR]
            and len(tokens_at_position) > 1
            and tokens_at_position[-2].type == RobotToken.KEYWORD
        ):
            return None

        token_at_position_index = kw_node.tokens.index(token_at_position)

        argument_token_index = token_at_position_index
        while argument_token_index >= 0 and kw_node.tokens[argument_token_index].type != RobotToken.ARGUMENT:
            argument_token_index -= 1

        argument_token: Optional[RobotToken] = None
        if argument_token_index >= 0:
            argument_token = kw_node.tokens[argument_token_index]

        result: Optional[Tuple[Optional[KeywordDoc], Token]]

        completion_range = range_from_token(argument_token or token_at_position)
        completion_range.end = range_from_token(token_at_position).end
        if (w := whitespace_at_begin_of_token(token_at_position)) > 0:
            if w > 1 and range_from_token(token_at_position).start.character + 1 < position.character:
                completion_range.start = position
            elif completion_range.start != position:
                return None
        else:
            if "=" in (argument_token or token_at_position).value:
                equal_index = (argument_token or token_at_position).value.index("=")
                if completion_range.start.character + equal_index < position.character:
                    return None
                else:
                    completion_range.end.character = completion_range.start.character + equal_index + 1
            else:
                completion_range.end = position

        result = await self.get_keyworddoc_and_token_from_position(
            keyword_token.value,
            keyword_token,
            [cast(Token, t) for t in kw_node.get_tokens(RobotToken.ARGUMENT)],
            self.namespace,
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

        return [
            CompletionItem(
                label=f"{e.name}=",
                kind=CompletionItemKind.VARIABLE,
                detail="Argument",
                filter_text=e.name,
                sort_text=f"02{i}_{e.name}=",
                insert_text_format=InsertTextFormat.PLAINTEXT,
                text_edit=TextEdit(range=completion_range, new_text=f"{e.name}="),
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
        from robot.parsing.model.statements import Fixture

        name_token = cast(Fixture, node).get_token(RobotToken.NAME)
        if name_token is None or name_token.value is None or name_token.value.upper() in ("", "NONE"):
            return None

        return await self._complete_KeywordCall_or_Fixture(RobotToken.NAME, node, nodes_at_position, position, context)
