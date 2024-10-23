import ast
import builtins
import itertools
import os
import time
from concurrent.futures import CancelledError
from itertools import chain
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
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

from robot.parsing.lexer.settings import (
    InitFileSettings,
    KeywordSettings,
    ResourceFileSettings,
    Settings,
    TestCaseSettings,
)
from robot.parsing.lexer.tokens import Token
from robot.parsing.model.blocks import File, SettingSection, TestCase
from robot.parsing.model.statements import (
    Arguments,
    Fixture,
    KeywordName,
    LibraryImport,
    ResourceImport,
    SectionHeader,
    Statement,
    Template,
    TestCaseName,
    TestTemplate,
    VariablesImport,
)
from robot.utils.escaping import split_from_equals

from robotcode.core.language import language_id
from robotcode.core.lsp.types import (
    Command,
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
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.robot.diagnostics.entities import VariableDefinitionType
from robotcode.robot.diagnostics.library_doc import (
    CompleteResultKind,
    KeywordArgumentKind,
    KeywordDoc,
    KeywordMatcher,
)
from robotcode.robot.diagnostics.model_helper import ModelHelper
from robotcode.robot.diagnostics.namespace import DocumentType, Namespace
from robotcode.robot.utils import get_robot_version
from robotcode.robot.utils.ast import (
    get_nodes_at_position,
    get_tokens_at_position,
    range_from_token,
    tokenize_variables,
    whitespace_at_begin_of_token,
    whitespace_from_begin_of_token,
)

from ...common.decorators import trigger_characters
from ..configuration import CompletionConfig
from .protocol_part import RobotLanguageServerProtocolPart

if get_robot_version() >= (6, 1):
    from robot.parsing.lexer.settings import SuiteFileSettings
else:
    from robot.parsing.lexer.settings import (
        TestCaseFileSettings as SuiteFileSettings,
    )

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

if get_robot_version() < (7, 0):
    from robot.variables.search import VariableIterator
else:
    from robot.variables.search import VariableMatches


if get_robot_version() < (5, 0):
    ALLOWED_VARIABLE_TOKENS = [
        Token.NAME,
        Token.ARGUMENT,
        Token.KEYWORD,
        Token.ASSIGN,
    ]
else:
    ALLOWED_VARIABLE_TOKENS = [
        Token.NAME,
        Token.ARGUMENT,
        Token.KEYWORD,
        Token.ASSIGN,
        Token.OPTION,
    ]


DEFAULT_HEADER_STYLE = "*** {name}s ***"
DEFAULT_HEADER_STYLE_51 = "*** {name} ***"


class RobotCompletionProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

        parent.completion.collect.add(self.collect)
        parent.completion.resolve.add(self.resolve)

    def get_config(self, document: TextDocument) -> CompletionConfig:
        if (folder := self.parent.workspace.get_workspace_folder(document.uri)) is not None:
            return self.parent.workspace.get_configuration(CompletionConfig, folder.uri)

        return CompletionConfig()

    def get_header_style(self, config: CompletionConfig) -> str:
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
            "=",
            os.sep,
        ]
    )
    # @all_commit_characters(['\n'])
    @language_id("robotframework")
    @_logger.call
    def collect(
        self,
        sender: Any,
        document: TextDocument,
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        namespace = self.parent.documents_cache.get_initialized_namespace(document)
        model = self.parent.documents_cache.get_model(document, False)

        config = self.get_config(document)

        return CompletionCollector(
            self.parent,
            document,
            model,
            namespace,
            self.get_header_style(config),
            config,
        ).collect(position, context)

    @language_id("robotframework")
    @_logger.call
    def resolve(self, sender: Any, completion_item: CompletionItem) -> CompletionItem:
        if completion_item.data is not None:
            document_uri = completion_item.data.get("document_uri", None)
            if document_uri is not None:
                document = self.parent.documents.get(document_uri)
                if document is not None:
                    namespace = self.parent.documents_cache.get_initialized_namespace(document)
                    model = self.parent.documents_cache.get_model(document, False)
                    if namespace is not None:
                        config = self.get_config(document)

                        return CompletionCollector(
                            self.parent,
                            document,
                            model,
                            namespace,
                            self.get_header_style(config),
                            config,
                        ).resolve(completion_item)

        return completion_item


_CompleteMethod = Callable[
    [Any, ast.AST, List[ast.AST], Position, Optional[CompletionContext]],
    Optional[List[CompletionItem]],
]

HEADERS = ["Test Case", "Setting", "Variable", "Keyword", "Comment", "Task"]
RESOURCE_HEADERS = ["Setting", "Variable", "Keyword", "Comment"]


__snippets: Optional[Dict[str, List[str]]] = None


def get_snippets() -> Dict[str, List[str]]:
    global __snippets
    if __snippets is None:
        __snippets = {
            "FOR": [
                r"FOR  \${${1}}  ${2|IN,IN ENUMERATE,IN RANGE,IN ZIP|}  ${3:arg}",
                "$0",
                "END",
                "",
            ],
            "IF": [r"IF  \${${1}}", "    $0", "END", ""],
        }

        if get_robot_version() >= (5, 0):
            __snippets.update(
                {
                    "TRYEX": [
                        "TRY",
                        "    $0",
                        r"EXCEPT  message",
                        "    ",
                        "END",
                        "",
                    ],
                    "TRYEXAS": [
                        "TRY",
                        "    $0",
                        r"EXCEPT  message    AS    \${ex}",
                        "    ",
                        "END",
                        "",
                    ],
                    "WHILE": [r"WHILE  ${1:expression}", "    $0", "END", ""],
                }
            )
        if get_robot_version() >= (7, 0):
            __snippets.update(
                {
                    "VAR ${}": [r"VAR    \${${1}}    ${0}"],
                    "VAR @{}": [r"VAR    @{${1}}    ${0}"],
                    "VAR &{}": [r"VAR    &{${1}}    ${0}"],
                }
            )
    return __snippets


__reserved_keywords: Optional[List[str]] = None


def get_reserved_keywords() -> List[str]:
    global __reserved_keywords

    if __reserved_keywords is None:
        __reserved_keywords = ["FOR", "END", "IF", "ELSE", "ELSE IF"]

        if get_robot_version() >= (5, 0):
            __reserved_keywords += [
                "TRY",
                "EXCEPT",
                "FINALLY",
                "WHILE",
                "BREAK",
                "CONTINUE",
                "RETURN",
            ]
        if get_robot_version() >= (7, 0):
            __reserved_keywords += ["VAR"]
        else:
            __reserved_keywords += ["ELIF"]

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


class CompletionCollector(ModelHelper):
    _logger = LoggingDescriptor()

    def __init__(
        self,
        parent: "RobotLanguageServerProtocol",
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

    _method_cache: Dict[Type[Any], List[_CompleteMethod]] = {}

    @classmethod
    def _find_methods(cls, visitor_cls: Type[Any]) -> Iterator[_CompleteMethod]:
        if visitor_cls in cls._method_cache:
            for m in cls._method_cache[visitor_cls]:
                yield m
            return

        methods = []
        if visitor_cls is ast.AST:
            return

        method_name = "complete_" + visitor_cls.__name__
        if hasattr(cls, method_name):
            method = getattr(cls, method_name)
            if callable(method):
                methods.append(method)
                yield cast(_CompleteMethod, method)
        for base in visitor_cls.__bases__:
            for m in cls._find_methods(base):
                methods.append(m)
                yield m

        cls._method_cache[visitor_cls] = methods

    def collect(
        self, position: Position, context: Optional[CompletionContext]
    ) -> Union[List[CompletionItem], CompletionList, None]:
        start = time.monotonic()
        try:
            result_nodes = get_nodes_at_position(self.model, position, include_end=True)

            result_nodes.reverse()

            def iter_results() -> Iterator[List[CompletionItem]]:
                for result_node in result_nodes:
                    for method in self._find_methods(type(result_node)):
                        r = method(self, result_node, result_nodes, position, context)
                        if r is not None:
                            yield r

                r = self.complete_default(result_nodes, position, context)
                if r is not None:
                    yield r

            items = [e for e in chain(*iter_results())]
            result = CompletionList(is_incomplete=False, items=items)
            if not result.items:
                return None
            return result
        finally:
            self._logger.trace(
                lambda: f"Collect completion for {self.document.uri} took {time.monotonic() - start:.2f} seconds"
            )

    def resolve(self, completion_item: CompletionItem) -> CompletionItem:
        data = cast(CompletionItemData, completion_item.data)

        if data is not None:
            document_uri = data.get("document_uri", None)
            if document_uri is not None:
                document = self.parent.documents.get(document_uri)
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
                                        for ld in (self.namespace.get_libraries()).values()
                                        if str(id(ld.library_doc)) == lib_id
                                    ),
                                    None,
                                )
                                if lib_doc is not None:
                                    completion_item.documentation = MarkupContent(
                                        kind=MarkupKind.MARKDOWN,
                                        value=lib_doc.to_markdown(False),
                                    )

                            except (
                                SystemExit,
                                KeyboardInterrupt,
                                CancelledError,
                            ):
                                raise
                            except BaseException as e:
                                completion_item.documentation = MarkupContent(
                                    kind=MarkupKind.MARKDOWN,
                                    value=f"Error:\n{e}",
                                )
                        elif (name := data.get("name", None)) is not None:
                            try:
                                lib_doc = self.namespace.imports_manager.get_libdoc_for_library_import(
                                    name,
                                    (),
                                    str(document.uri.to_path().parent),
                                    variables=self.namespace.get_resolvable_variables(),
                                )

                                if lib_doc is not None:
                                    completion_item.documentation = MarkupContent(
                                        kind=MarkupKind.MARKDOWN,
                                        value=lib_doc.to_markdown(False),
                                    )

                            except (SystemExit, KeyboardInterrupt):
                                raise
                            except BaseException:
                                pass

                    elif comp_type == CompleteResultKind.RESOURCE.name:
                        if (res_id := data.get("id", None)) is not None:
                            try:
                                lib_doc = next(
                                    (
                                        ld.library_doc
                                        for ld in (self.namespace.get_resources()).values()
                                        if str(id(ld.library_doc)) == res_id
                                    ),
                                    None,
                                )

                                if lib_doc is not None:
                                    completion_item.documentation = MarkupContent(
                                        kind=MarkupKind.MARKDOWN,
                                        value=lib_doc.to_markdown(False),
                                    )

                            except (
                                SystemExit,
                                KeyboardInterrupt,
                                CancelledError,
                            ):
                                raise
                            except BaseException as e:
                                completion_item.documentation = MarkupContent(
                                    kind=MarkupKind.MARKDOWN,
                                    value=f"Error:\n{e}",
                                )

                        elif (name := data.get("name", None)) is not None:
                            try:
                                lib_doc = self.namespace.imports_manager.get_libdoc_for_resource_import(
                                    name,
                                    str(document.uri.to_path().parent),
                                    variables=self.namespace.get_resolvable_variables(),
                                )

                                if lib_doc is not None:
                                    completion_item.documentation = MarkupContent(
                                        kind=MarkupKind.MARKDOWN,
                                        value=lib_doc.to_markdown(False),
                                    )

                            except (SystemExit, KeyboardInterrupt):
                                raise
                            except BaseException:
                                pass
                    elif comp_type == CompleteResultKind.KEYWORD.name:
                        kw_id = data.get("id", None)
                        if kw_id is not None:
                            try:
                                kw_doc = next(
                                    (kw for kw in self.namespace.get_keywords() if str(id(kw)) == kw_id),
                                    None,
                                )

                                if kw_doc is not None:
                                    completion_item.documentation = MarkupContent(
                                        kind=MarkupKind.MARKDOWN,
                                        value=kw_doc.to_markdown(),
                                    )

                            except (
                                SystemExit,
                                KeyboardInterrupt,
                                CancelledError,
                            ):
                                raise
                            except BaseException:
                                pass

        return completion_item

    def create_headers_completion_items(self, range: Optional[Range]) -> List[CompletionItem]:
        doc_type = self.parent.documents_cache.get_document_type(self.document)

        if self.namespace.languages is None:
            if doc_type in [DocumentType.RESOURCE, DocumentType.INIT]:
                headers: Iterable[str] = RESOURCE_HEADERS
            else:
                headers = HEADERS
        else:
            languages = self.namespace.languages.languages

            if (
                self.config.filter_default_language
                and len(self.namespace.languages.languages) > 1
                and self.config.filter_default_language
            ):
                languages = [v for v in languages if v.code != "en"]

            headers = set(
                itertools.chain(
                    *(
                        [
                            k
                            for k, v in lang.headers.items()
                            if doc_type not in [DocumentType.RESOURCE, DocumentType.INIT]
                            or v not in ("Test Cases", "Tasks")
                        ]
                        for lang in languages
                    )
                )
            )

        return [
            CompletionItem(
                label=s[0],
                kind=CompletionItemKind.CLASS,
                detail="Header",
                # this is to get the english version in the documentation
                documentation=(
                    self.namespace.languages.headers.get(s[1]) if self.namespace.languages is not None else None
                ),
                sort_text=f"100_{s[1]}",
                insert_text_format=InsertTextFormat.PLAIN_TEXT,
                text_edit=TextEdit(range=range, new_text=s[0]) if range is not None else None,
            )
            for s in ((self.header_style.format(name=k), k) for k in (v.title() for v in headers))
        ]

    def create_environment_variables_completion_items(self, range: Optional[Range]) -> List[CompletionItem]:
        return [
            CompletionItem(
                label=s,
                kind=CompletionItemKind.VARIABLE,
                detail="Variable",
                sort_text=f"035_{s}",
                insert_text_format=InsertTextFormat.PLAIN_TEXT,
                text_edit=TextEdit(range=range, new_text=s) if range is not None else None,
            )
            for s in self.namespace.imports_manager.environment.keys()
        ]

    _VARIABLE_COMPLETION_SORT_TEXT_PREFIX: ClassVar[Dict[VariableDefinitionType, str]] = {
        VariableDefinitionType.LOCAL_VARIABLE: "033",
        VariableDefinitionType.ARGUMENT: "034",
        VariableDefinitionType.VARIABLE: "035",
        VariableDefinitionType.IMPORTED_VARIABLE: "036",
        VariableDefinitionType.COMMAND_LINE_VARIABLE: "037",
        VariableDefinitionType.BUILTIN_VARIABLE: "038",
        VariableDefinitionType.ENVIRONMENT_VARIABLE: "039",
    }

    def create_variables_completion_items(
        self, range: Range, nodes: List[ast.AST], position: Position
    ) -> List[CompletionItem]:
        return [
            CompletionItem(
                label=s.name,
                kind=CompletionItemKind.VARIABLE,
                detail=f"{s.type.value}",
                sort_text=f"{self._VARIABLE_COMPLETION_SORT_TEXT_PREFIX.get(s.type, '035')}_{s.name[2:-1]}",
                insert_text_format=InsertTextFormat.PLAIN_TEXT,
                text_edit=TextEdit(range=range, new_text=s.name[2:-1]),
                filter_text=s.name[2:-1] if range is not None else None,
            )
            for s in (self.namespace.get_variable_matchers(list(reversed(nodes)), position)).values()
            if s.name is not None and (s.name_token is None or not position.is_in_range(range_from_token(s.name_token)))
        ]

    def create_settings_completion_items(self, range: Optional[Range]) -> List[CompletionItem]:
        doc_type = self.parent.documents_cache.get_document_type(self.document)

        settings_class: Type[Settings] = SuiteFileSettings
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
                documentation=(
                    self.namespace.languages.settings.get(setting) if self.namespace.languages is not None else None
                ),
                sort_text=f"090_{setting}",
                insert_text_format=InsertTextFormat.PLAIN_TEXT,
                text_edit=TextEdit(range=range, new_text=setting) if range is not None else None,
            )
            for setting in settings
        ]

    def create_keyword_snippet_completion_items(self, range: Optional[Range]) -> List[CompletionItem]:
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

    def create_testcase_settings_completion_items(self, range: Optional[Range]) -> List[CompletionItem]:
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
                documentation=(
                    self.namespace.languages.settings.get(setting) if self.namespace.languages is not None else None
                ),
                detail="Setting",
                sort_text=f"070_{setting}",
                insert_text_format=InsertTextFormat.PLAIN_TEXT,
                text_edit=TextEdit(range=range, new_text=f"[{setting}]") if range is not None else None,
            )
            for setting in settings
        ]

    def create_bdd_prefix_completion_items(
        self,
        range: Optional[Range],
        at_top: bool = False,
        with_space: bool = True,
    ) -> List[CompletionItem]:
        prefixes = {"Given", "When", "Then", "And", "But"}

        if self.namespace.languages is not None:
            prefixes.update(self.namespace.languages.bdd_prefixes)

        return [
            CompletionItem(
                label=prefix,
                kind=CompletionItemKind.UNIT,
                detail="BDD Prefix",
                sort_text=f"000_{prefix}" if at_top else f"080_{prefix}",
                insert_text_format=InsertTextFormat.PLAIN_TEXT,
                text_edit=(
                    TextEdit(range=range, new_text=prefix + (" " if with_space else "")) if range is not None else None
                ),
            )
            for prefix in prefixes
        ]

    def create_keyword_settings_completion_items(self, range: Optional[Range]) -> List[CompletionItem]:
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
                documentation=(
                    self.namespace.languages.settings.get(setting) if self.namespace.languages is not None else None
                ),
                detail="Setting",
                sort_text=f"070_{setting}",
                insert_text_format=InsertTextFormat.PLAIN_TEXT,
                text_edit=TextEdit(range=range, new_text=f"[{setting}]") if range is not None else None,
            )
            for setting in settings
        ]

    def get_keyword_snipped_text(self, kw: KeywordDoc, in_template: bool) -> str:
        result = ""
        after: Optional[str] = None

        if not kw.is_embedded:
            return kw.name

        if get_robot_version() < (7, 0):
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

        else:
            for index, match in enumerate(VariableMatches(kw.name, identifiers="$", ignore_errors=True)):
                var_name = match.base.split(":", 1)[0] if match.base else ""
                result += match.before
                result += "${" + str(index + 1)

                if var_name:
                    result += ":"
                    if in_template:
                        result += "\\${"

                    result += var_name

                    if in_template:
                        result += "\\}"

                result += "}"

            if match.after:
                result += match.after

        return result

    def create_keyword_completion_items(
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

        r: Optional[Range] = None

        has_bdd = False
        bdd_token = None
        only_bdd = False

        if token is not None:
            old_token = token
            bdd_token, token = self.split_bdd_prefix(self.namespace, token)

            if (
                bdd_token is None
                and token is not None
                and self.is_bdd_token(self.namespace, token)
                and position.character > range_from_token(token).end.character
            ):
                bdd_token = token
                token = None
                only_bdd = True

            if token is not None and token.value == "":
                token = None

            if bdd_token is not None and position.character > range_from_token(bdd_token).end.character:
                has_bdd = True

            if not has_bdd and token is not None:
                token = old_token

        namespace_name = None
        namespace_matcher = None
        valid_namespace = False

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
                    namespace_name = token.value[0 : lib_name_index - r.start.character]

                    libraries = self.namespace.get_libraries()

                    namespace_matcher = KeywordMatcher(namespace_name, is_namespace=True)
                    namespace_name = next(
                        (e for e in libraries.keys() if namespace_matcher == KeywordMatcher(e, is_namespace=True)),
                        namespace_name,
                    )

                    if namespace_name in libraries:
                        valid_namespace = True

                        r.start.character = lib_name_index + 1
                        for kw in libraries[namespace_name].library_doc.keywords.values():
                            if kw.is_error_handler:
                                continue
                            result.append(
                                CompletionItem(
                                    label=kw.name,
                                    kind=CompletionItemKind.FUNCTION,
                                    detail=f"{CompleteResultKind.KEYWORD.value} "
                                    f"{f'({kw.libname})' if kw.libname is not None else ''}",
                                    sort_text=f"019_{kw.name}",
                                    insert_text_format=(
                                        InsertTextFormat.PLAIN_TEXT if not kw.is_embedded else InsertTextFormat.SNIPPET
                                    ),
                                    text_edit=(
                                        TextEdit(
                                            range=r,
                                            new_text=(
                                                kw.name
                                                if not kw.is_embedded
                                                else self.get_keyword_snipped_text(kw, in_template)
                                            ),
                                        )
                                        if r is not None
                                        else None
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

                    resources = {
                        k: v
                        for k, v in self.namespace.get_resources().items()
                        if namespace_matcher == KeywordMatcher(v.name, is_namespace=True)
                    }

                    if resources:
                        valid_namespace = True
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
                                        sort_text=f"019_{kw.name}",
                                        insert_text_format=(
                                            InsertTextFormat.PLAIN_TEXT
                                            if not kw.is_embedded
                                            else InsertTextFormat.SNIPPET
                                        ),
                                        text_edit=TextEdit(
                                            range=r,
                                            new_text=(
                                                kw.name
                                                if not kw.is_embedded
                                                else self.get_keyword_snipped_text(kw, in_template)
                                            ),
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

        if token is not None:
            r = range_from_token(token)

        if r is None:
            r = Range(position, position)

        if namespace_matcher is not None:
            namespace_matcher = KeywordMatcher(namespace_matcher.name)

        for kw in self.namespace.get_keywords():
            if kw.is_error_handler:
                continue
            if (
                valid_namespace
                and namespace_matcher is not None
                and not kw.matcher.normalized_name.startswith(namespace_matcher.normalized_name)
            ):
                continue

            result.append(
                CompletionItem(
                    label=kw.name,
                    kind=CompletionItemKind.FUNCTION,
                    detail=f"{CompleteResultKind.KEYWORD.value} {f'({kw.libname})' if kw.libname is not None else ''}",
                    deprecated=kw.is_deprecated,
                    sort_text=f"020_{kw.name}",
                    insert_text_format=InsertTextFormat.PLAIN_TEXT if not kw.is_embedded else InsertTextFormat.SNIPPET,
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

        if valid_namespace and namespace_matcher is not None:
            return result

        for k, v in (self.namespace.get_libraries()).items():
            result.append(
                CompletionItem(
                    label=k,
                    kind=CompletionItemKind.MODULE,
                    detail="Library",
                    sort_text=f"030_{v.name}",
                    deprecated=v.library_doc.is_deprecated,
                    insert_text_format=InsertTextFormat.PLAIN_TEXT,
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

        for k, v in self.namespace.get_resources().items():
            result.append(
                CompletionItem(
                    label=v.name,
                    kind=CompletionItemKind.MODULE,
                    detail="Resource",
                    deprecated=v.library_doc.is_deprecated,
                    sort_text=f"030_{v.name}",
                    insert_text_format=InsertTextFormat.PLAIN_TEXT,
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
                    insert_text_format=InsertTextFormat.PLAIN_TEXT,
                    text_edit=TextEdit(range=r, new_text="NONE"),
                )
            )

        if add_bdd_prefixes and not (has_bdd or only_bdd):
            bdd_range = r
            at_top = False
            with_space = True
            if bdd_token is not None and (
                position in range_from_token(bdd_token) or position == range_from_token(bdd_token).end.character
            ):
                at_top = True
                with_space = False
                bdd_range = range_from_token(bdd_token)

            result += self.create_bdd_prefix_completion_items(bdd_range, at_top, with_space)

        if add_reserverd and not (has_bdd or only_bdd):
            for k in get_reserved_keywords():
                result.append(
                    CompletionItem(
                        label=k,
                        kind=CompletionItemKind.KEYWORD,
                        sort_text=f"999_{k}",
                        insert_text_format=InsertTextFormat.PLAIN_TEXT,
                        text_edit=TextEdit(range=r, new_text=k),
                    )
                )

        return result

    def get_variable_token(self, token: Token) -> Optional[Token]:
        return next(
            (
                v
                for v in itertools.dropwhile(
                    lambda t: t.type in Token.NON_DATA_TOKENS,
                    tokenize_variables(token, ignore_errors=True),
                )
                if v.type == Token.VARIABLE
            ),
            None,
        )

    def complete_default(
        self,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Optional[List[CompletionItem]]:
        if len(nodes_at_position) > 1 and isinstance(nodes_at_position[0], Statement):
            statement_node = nodes_at_position[0]
            if len(statement_node.tokens) > 0:
                token = statement_node.tokens[0]
                r = range_from_token(token)
                value = token.value.strip()
                only_stars = value is not None and "*" in value and all(v == "*" for v in value)
                if (
                    r.start.character == 0
                    and (position.is_in_range(r))
                    and (only_stars or value.startswith("*") or position.character == 0)
                ):
                    return self.create_headers_completion_items(r)
                if len(statement_node.tokens) > 1 and only_stars:
                    r1 = range_from_token(statement_node.tokens[1])
                    ws = whitespace_at_begin_of_token(statement_node.tokens[1])
                    if ws > 0:
                        r1.end.character = r1.start.character + ws
                        if position.is_in_range(r1):
                            r.end = r1.end
                            return self.create_headers_completion_items(r)

        elif position.character == 0:
            if not nodes_at_position and position.line > 0:
                nodes_at_line_before = get_nodes_at_position(self.model, Position(position.line - 1, 0))
                if nodes_at_line_before and any(isinstance(n, SettingSection) for n in nodes_at_line_before):
                    return [
                        *self.create_settings_completion_items(None),
                        *self.create_headers_completion_items(None),
                    ]

            return self.create_headers_completion_items(None)

        if len(nodes_at_position) > 1 and isinstance(nodes_at_position[0], Statement):
            node = nodes_at_position[0]

            tokens_at_position = get_tokens_at_position(node, position, True)
            if not tokens_at_position:
                return None

            token_at_position = tokens_at_position[-1]

            if isinstance(node, Arguments):
                arg = self.get_variable_token(token_at_position)
                if arg is not None and position <= range_from_token(arg).end:
                    return None

            token_at_position_index = tokens_at_position.index(token_at_position)
            while token_at_position.type == Token.EOL:
                token_at_position_index -= 1
                if token_at_position_index < 0:
                    break
                token_at_position = tokens_at_position[token_at_position_index]

            if token_at_position.type not in ALLOWED_VARIABLE_TOKENS:
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
                    for a in itertools.takewhile(
                        lambda b: b != "}",
                        token_at_position.value[open_brace_index + 1 :],
                    )
                    if a in "+-*/"
                )
                range = Range(
                    start=Position(
                        line=position.line,
                        character=token_at_position.col_offset + open_brace_index + 1,
                    ),
                    end=(
                        position
                        if contains_spezial or variable_end < 0
                        else Position(
                            line=position.line,
                            character=(
                                (token_at_position.col_offset + variable_end)
                                if not contains_spezial
                                else token_at_position.end_col_offset
                            ),
                        )
                    ),
                )
                if token_at_position.value[open_brace_index - 1] == "%":
                    return self.create_environment_variables_completion_items(range)
                return self.create_variables_completion_items(range, nodes_at_position, position)

        return None

    def complete_SettingSection(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        if nodes_at_position.index(node) > 0 and not isinstance(nodes_at_position[0], SectionHeader):
            node_at_pos = nodes_at_position[0]
            if (
                position.character > 0
                and isinstance(node_at_pos, Statement)
                and node_at_pos.tokens
                and node_at_pos.tokens[0].value
                and whitespace_at_begin_of_token(node_at_pos.tokens[0]) > 0
            ):
                return None

            statement_node = cast(Statement, nodes_at_position[0])
            if len(statement_node.tokens) > 0:
                token = statement_node.tokens[0]
                r = range_from_token(token)
                if position.is_in_range(r):
                    return self.create_settings_completion_items(r)

        return None

    def _complete_TestCase_or_Keyword(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
        in_template: bool,
        create_items: Callable[
            [bool, bool, Optional[Range], Optional[Token], Position],
            Union[List[CompletionItem], CompletionList, None],
        ],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        index = 0
        in_assign = False

        if not isinstance(nodes_at_position[0], Statement):
            return None

        statement_node = nodes_at_position[0]

        if isinstance(statement_node, (TestCaseName, KeywordName)):
            index += 1

        while index < len(statement_node.tokens):
            if len(statement_node.tokens) > index:
                token = statement_node.tokens[index]
                if token.type == Token.ASSIGN:
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
                    return create_items(
                        in_assign,
                        in_template,
                        (
                            range_from_token(statement_node.tokens[index + 1])
                            if r.end == position and len(statement_node.tokens) > index + 1
                            else None
                        ),
                        (
                            statement_node.tokens[index + 1]
                            if r.end == position and len(statement_node.tokens) > index + 1
                            else None
                        ),
                        position,
                    )

            index += 1

            if len(statement_node.tokens) > index:
                token = statement_node.tokens[index]
                if token.type == Token.ASSIGN:
                    continue

            if len(statement_node.tokens) > index:
                token = statement_node.tokens[index]

                r = range_from_token(token)
                if position.is_in_range(r):
                    return create_items(in_assign, in_template, r, token, position)

                if len(statement_node.tokens) > index + 1:
                    second_token = statement_node.tokens[index + 1]
                    ws = whitespace_at_begin_of_token(second_token)
                    if ws < 1:
                        return None

                    r.end.character += 1
                    if position.is_in_range(r):
                        return create_items(in_assign, in_template, r, token, position)

        return None

    def complete_TestCase(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        def create_items(
            in_assign: bool,
            in_template: bool,
            r: Optional[Range],
            token: Optional[Token],
            pos: Position,
        ) -> Union[List[CompletionItem], CompletionList, None]:
            return [
                e
                for e in chain(
                    [] if in_assign else self.create_keyword_snippet_completion_items(r),
                    [] if in_assign else self.create_testcase_settings_completion_items(r),
                    [] if in_template else self.create_keyword_completion_items(token, pos),
                )
            ]

        def check_in_template() -> bool:
            testcase_node = cast(TestCase, node)
            if any(
                template
                for template in testcase_node.body
                if isinstance(template, Template) and template.value is not None
            ):
                return True

            if any(
                template
                for template in testcase_node.body
                if isinstance(template, Template) and template.get_value(Token.NAME) == "NONE"
            ):
                return False

            if any(
                file
                for file in nodes_at_position
                if isinstance(file, File)
                and any(
                    section
                    for section in file.sections
                    if isinstance(section, SettingSection)
                    and any(
                        template
                        for template in section.body
                        if isinstance(template, TestTemplate) and template.value is not None
                    )
                )
            ):
                return True

            return False

        in_template = check_in_template()

        return self._complete_TestCase_or_Keyword(
            node,
            nodes_at_position,
            position,
            context,
            in_template,
            create_items,
        )

    def complete_Keyword(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        def create_items(
            in_assign: bool,
            in_template: bool,
            r: Optional[Range],
            token: Optional[Token],
            pos: Position,
        ) -> Union[List[CompletionItem], CompletionList, None]:
            return [
                e
                for e in chain(
                    [] if in_assign else self.create_keyword_snippet_completion_items(r),
                    [] if in_assign else self.create_keyword_settings_completion_items(r),
                    [] if in_template else self.create_keyword_completion_items(token, pos),
                )
            ]

        return self._complete_TestCase_or_Keyword(node, nodes_at_position, position, context, False, create_items)

    def _complete_SuiteSetup_or_SuiteTeardown_or_TestTemplate(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        statement_node = cast(Statement, node)
        if len(statement_node.tokens) > 1:
            token = statement_node.tokens[1]
            r = range_from_token(token)
            ws = whitespace_at_begin_of_token(token)
            if ws < 2:
                return None

            ws_b = whitespace_from_begin_of_token(token)
            r.start.character += 2 if ws_b and ws_b[0] != "\t" else 1

            if position.is_in_range(r):
                return self.create_keyword_completion_items(
                    statement_node.tokens[2] if r.end == position and len(statement_node.tokens) > 2 else None,
                    position,
                    add_reserverd=False,
                    add_none=True,
                    in_template=isinstance(node, TestTemplate),
                )

        if len(statement_node.tokens) > 2:
            token = statement_node.tokens[2]

            token = self.strip_bdd_prefix(self.namespace, token)

            r = range_from_token(token)
            if position.is_in_range(r):
                return self.create_keyword_completion_items(
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
                return self.create_keyword_completion_items(
                    token,
                    position,
                    add_reserverd=False,
                    add_none=True,
                    in_template=isinstance(node, TestTemplate),
                )

        return None

    def complete_SuiteSetup(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        return self._complete_SuiteSetup_or_SuiteTeardown_or_TestTemplate(node, nodes_at_position, position, context)

    def complete_SuiteTeardown(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        return self._complete_SuiteSetup_or_SuiteTeardown_or_TestTemplate(node, nodes_at_position, position, context)

    def complete_TestSetup(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        return self._complete_SuiteSetup_or_SuiteTeardown_or_TestTemplate(node, nodes_at_position, position, context)

    def complete_TestTeardown(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        return self._complete_SuiteSetup_or_SuiteTeardown_or_TestTemplate(node, nodes_at_position, position, context)

    def complete_TestTemplate(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        return self._complete_SuiteSetup_or_SuiteTeardown_or_TestTemplate(node, nodes_at_position, position, context)

    def complete_Setup_or_Teardown_or_Template(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        statement_node = cast(Statement, node)
        if len(statement_node.tokens) > 2:
            token = statement_node.tokens[2]

            r = range_from_token(token)
            ws = whitespace_at_begin_of_token(token)
            if ws < 2:
                return None

            ws_b = whitespace_from_begin_of_token(token)
            r.start.character += 2 if ws_b and ws_b[0] != "\t" else 1

            if position.is_in_range(r):
                return self.create_keyword_completion_items(
                    statement_node.tokens[3] if r.end == position and len(statement_node.tokens) > 3 else None,
                    position,
                    add_reserverd=False,
                    add_none=True,
                    in_template=isinstance(node, Template),
                )

        if len(statement_node.tokens) > 3:
            token = statement_node.tokens[3]

            token = self.strip_bdd_prefix(self.namespace, token)

            r = range_from_token(token)
            if position.is_in_range(r):
                return self.create_keyword_completion_items(
                    token,
                    position,
                    add_reserverd=False,
                    add_none=True,
                    in_template=isinstance(node, Template),
                )

        if len(statement_node.tokens) > 4:
            second_token = statement_node.tokens[4]
            ws = whitespace_at_begin_of_token(second_token)
            if ws < 1:
                return None

            r.end.character += 1
            if position.is_in_range(r):
                return self.create_keyword_completion_items(
                    token,
                    position,
                    add_reserverd=False,
                    add_none=True,
                    in_template=isinstance(node, Template),
                )

        return None

    def complete_Setup(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        return self.complete_Setup_or_Teardown_or_Template(node, nodes_at_position, position, context)

    def complete_Teardown(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        return self.complete_Setup_or_Teardown_or_Template(node, nodes_at_position, position, context)

    def complete_Template(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        return self.complete_Setup_or_Teardown_or_Template(node, nodes_at_position, position, context)

    def complete_LibraryImport(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        import_node = cast(LibraryImport, node)
        import_token = import_node.get_token(Token.LIBRARY)
        if import_token is None:
            return []

        if position.is_in_range(range_from_token(import_token)):
            return []

        import_token_index = import_node.tokens.index(import_token)

        def complete_import() -> Optional[List[CompletionItem]]:
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

            if "/" in name_token.value or os.sep in name_token.value:
                part_splitter = ["/", os.sep]
            else:
                part_splitter = ["."]

            reversed_text_before_position = list(reversed(text_before_position))
            last_separator_index = (
                len(text_before_position)
                - next(
                    (
                        i
                        for i, c in enumerate(reversed_text_before_position)
                        if c in part_splitter
                        and (
                            c != "\\"
                            or (
                                c == "\\"
                                and len(reversed_text_before_position) > i + 1
                                and reversed_text_before_position[i + 1] == "\\"
                            )
                        )
                    ),
                    -1,
                )
                - 1
            )

            first_part = (
                text_before_position[
                    : last_separator_index + (1 if text_before_position[last_separator_index] in part_splitter else 0)
                ]
                if last_separator_index < len(text_before_position)
                else None
            )

            try:
                complete_list = self.namespace.imports_manager.complete_library_import(
                    first_part if first_part else None,
                    str(self.document.uri.to_path().parent),
                    self.namespace.get_resolvable_variables(nodes_at_position, position),
                )
                if not complete_list:
                    return None
            except (SystemExit, KeyboardInterrupt, CancelledError):
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
                    kind=(
                        CompletionItemKind.MODULE
                        if e.kind
                        in [
                            CompleteResultKind.MODULE,
                            CompleteResultKind.MODULE_INTERNAL,
                        ]
                        else (
                            CompletionItemKind.FILE
                            if e.kind == CompleteResultKind.FILE
                            else CompletionItemKind.FOLDER if e.kind == CompleteResultKind.FOLDER else None
                        )
                    ),
                    detail=e.kind.value,
                    sort_text=f"030_{e}",
                    insert_text_format=InsertTextFormat.PLAIN_TEXT,
                    text_edit=TextEdit(range=r, new_text=e.label) if r is not None else None,
                    data=CompletionItemData(
                        document_uri=str(self.document.uri),
                        type=e.kind.name,
                        name=((first_part) if first_part is not None else "") + e.label,
                    ),
                )
                for e in complete_list
            ]

        def complete_arguments() -> Optional[List[CompletionItem]]:
            if (t := import_node.get_token(Token.NAME)) is None or position <= range_from_token(t).extend(
                end_character=1
            ).end:
                return None

            with_name_token = next(
                (v for v in import_node.tokens if v.type == Token.WITH_NAME),
                None,
            )
            if with_name_token is not None and position >= range_from_token(with_name_token).start:
                return None

            kw_node = cast(Statement, node)

            tokens_at_position = get_tokens_at_position(kw_node, position, True)

            if not tokens_at_position:
                return None

            token_at_position = tokens_at_position[-1]

            name_token = import_node.get_token(Token.NAME)
            if name_token is None or position.character < range_from_token(name_token).end.character:
                return None

            try:
                libdoc = self.namespace.get_imported_library_libdoc(
                    import_node.name, import_node.args, import_node.alias
                )
                if libdoc is not None:
                    init = next((v for v in libdoc.inits.values()), None)
                    if init:
                        name_token_index = import_node.tokens.index(name_token)
                        return self._complete_keyword_arguments_at_position(
                            init,
                            kw_node.tokens[name_token_index:],
                            token_at_position,
                            position,
                        )

            except (SystemExit, KeyboardInterrupt, CancelledError):
                raise
            except BaseException as e:
                self._logger.exception(e)

            return None

        def complete_with_name() -> Optional[List[CompletionItem]]:
            with_name_token = next(
                (v for v in import_node.tokens if v.type == Token.WITH_NAME),
                None,
            )
            if with_name_token is not None and position < range_from_token(with_name_token).start:
                return None

            if (name_token := import_node.get_token(Token.NAME)) is not None and not any(
                v for v in import_node.tokens if v.type == Token.WITH_NAME
            ):
                arg_tokens = import_node.get_tokens(Token.ARGUMENT)
                if position >= range_from_token(name_token).extend(end_character=2).end and (
                    not arg_tokens or position >= range_from_token(arg_tokens[-1]).extend(end_character=2).end
                ):
                    return [
                        CompletionItem(
                            label="AS" if get_robot_version() >= (6, 0) else "WITH NAME",
                            kind=CompletionItemKind.KEYWORD,
                            # detail=e.detail,
                            sort_text="99_NAMESPACE_MARKER",
                            insert_text_format=InsertTextFormat.PLAIN_TEXT,
                        )
                    ]
            return []

        result = complete_import() or []
        result.extend(complete_arguments() or [])
        result.extend(complete_with_name() or [])

        return result

    def complete_ResourceImport(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
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

        reversed_text_before_position = list(reversed(text_before_position))
        last_separator_index = (
            len(text_before_position)
            - next(
                (
                    i
                    for i, c in enumerate(reversed_text_before_position)
                    if c in ["/", os.sep]
                    and (
                        c != "\\"
                        or (
                            c == "\\"
                            and len(reversed_text_before_position) > i + 1
                            and reversed_text_before_position[i + 1] == "\\"
                        )
                    )
                ),
                -1,
            )
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
            complete_list = self.namespace.imports_manager.complete_resource_import(
                first_part if first_part else None,
                str(self.document.uri.to_path().parent),
                self.namespace.get_resolvable_variables(nodes_at_position, position),
            )
            if not complete_list:
                return None
        except (SystemExit, KeyboardInterrupt, CancelledError):
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
                kind=(
                    CompletionItemKind.FILE
                    if e.kind == CompleteResultKind.RESOURCE
                    else (
                        CompletionItemKind.FILE
                        if e.kind == CompleteResultKind.FILE
                        else CompletionItemKind.FOLDER if e.kind == CompleteResultKind.FOLDER else None
                    )
                ),
                detail=e.kind.value,
                sort_text=f"030_{e}",
                insert_text_format=InsertTextFormat.PLAIN_TEXT,
                text_edit=TextEdit(range=r, new_text=e.label) if r is not None else None,
                data=CompletionItemData(
                    document_uri=str(self.document.uri),
                    type=e.kind.name,
                    name=((first_part) if first_part is not None else "") + e.label,
                ),
            )
            for e in complete_list
        ]

    def complete_VariablesImport(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        import_node = cast(VariablesImport, node)
        import_token = import_node.get_token(Token.VARIABLES)

        if import_token is None:
            return []

        if position.is_in_range(range_from_token(import_token)):
            return []

        import_token_index = import_node.tokens.index(import_token)

        def complete_import() -> Optional[List[CompletionItem]]:
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

            if "/" in name_token.value or os.sep in name_token.value:
                part_splitter = ["/", os.sep]
            else:
                part_splitter = ["."]

            reversed_text_before_position = list(reversed(text_before_position))
            last_separator_index = (
                len(text_before_position)
                - next(
                    (
                        i
                        for i, c in enumerate(reversed_text_before_position)
                        if c in part_splitter
                        and (
                            c != "\\"
                            or (
                                c == "\\"
                                and len(reversed_text_before_position) > i + 1
                                and reversed_text_before_position[i + 1] == "\\"
                            )
                        )
                    ),
                    -1,
                )
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
                complete_list = self.namespace.imports_manager.complete_variables_import(
                    first_part if first_part else None,
                    str(self.document.uri.to_path().parent),
                    self.namespace.get_resolvable_variables(nodes_at_position, position),
                )
                if not complete_list:
                    return None
            except (SystemExit, KeyboardInterrupt, CancelledError):
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
                    kind=(
                        CompletionItemKind.FILE
                        if e.kind == CompleteResultKind.VARIABLES
                        else (
                            CompletionItemKind.FILE
                            if e.kind == CompleteResultKind.FILE
                            else CompletionItemKind.FOLDER if e.kind == CompleteResultKind.FOLDER else None
                        )
                    ),
                    detail=e.kind.value,
                    sort_text=f"030_{e}",
                    insert_text_format=InsertTextFormat.PLAIN_TEXT,
                    text_edit=TextEdit(range=r, new_text=e.label) if r is not None else None,
                    data=CompletionItemData(
                        document_uri=str(self.document.uri),
                        type=e.kind.name,
                        name=((first_part) if first_part is not None else "") + e.label,
                    ),
                )
                for e in complete_list
            ]

        def complete_arguments() -> Optional[List[CompletionItem]]:
            if (t := import_node.get_token(Token.NAME)) is None or position <= range_from_token(t).extend(
                end_character=1
            ).end:
                return None

            kw_node = cast(Statement, node)

            tokens_at_position = get_tokens_at_position(kw_node, position, True)

            if not tokens_at_position:
                return None

            token_at_position = tokens_at_position[-1]

            name_token = import_node.get_token(Token.NAME)
            if name_token is None or position.character < range_from_token(name_token).end.character:
                return None

            try:
                libdoc = self.namespace.get_variables_import_libdoc(import_node.name, import_node.args)
                if libdoc is not None:
                    init = next((v for v in libdoc.inits.values()), None)
                    if init:
                        name_token_index = import_node.tokens.index(name_token)
                        return self._complete_keyword_arguments_at_position(
                            init,
                            kw_node.tokens[name_token_index:],
                            token_at_position,
                            position,
                        )

            except (SystemExit, KeyboardInterrupt, CancelledError):
                raise
            except BaseException as e:
                self._logger.exception(e)

            return None

        result = complete_import() or []
        # TODO this is not supported in robotframework, but it would be nice to have
        result.extend(complete_arguments() or [])

        return result

    def _complete_KeywordCall_or_Fixture(  # noqa: N802
        self,
        keyword_name_token_type: str,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        kw_node = cast(Statement, node)

        keyword_token = kw_node.get_token(keyword_name_token_type)
        if keyword_token is None:
            return None

        tokens_at_position = get_tokens_at_position(kw_node, position, include_end=True)

        if not tokens_at_position:
            return None

        token_at_position = tokens_at_position[-1]

        if token_at_position.type not in [
            Token.ARGUMENT,
            Token.EOL,
            Token.SEPARATOR,
        ]:
            return None

        if len(tokens_at_position) > 1 and tokens_at_position[-2].type == Token.KEYWORD:
            return None

        keyword_doc_and_token: Optional[Tuple[Optional[KeywordDoc], Token]] = None

        keyword_token = kw_node.get_token(keyword_name_token_type)
        if keyword_token is None or position <= range_from_token(keyword_token).end:
            return None

        if (
            position == range_from_token(token_at_position).start
            and len(tokens_at_position) >= 3
            and tokens_at_position[-2].type == Token.ARGUMENT
            and not tokens_at_position[-2].value
            and tokens_at_position[-3].type == Token.CONTINUATION
        ):
            return None

        keyword_doc_and_token = self.get_keyworddoc_and_token_from_position(
            keyword_token.value,
            keyword_token,
            [t for t in kw_node.get_tokens(Token.ARGUMENT)],
            self.namespace,
            range_from_token(keyword_token).end,
            analyse_run_keywords=False,
        )

        if keyword_doc_and_token is None or keyword_doc_and_token[0] is None:
            return None

        keyword_doc = keyword_doc_and_token[0]

        if keyword_doc.is_any_run_keyword():
            return None

        keyword_token_index = kw_node.tokens.index(keyword_token)

        return self._complete_keyword_arguments_at_position(
            keyword_doc,
            kw_node.tokens[keyword_token_index:],
            token_at_position,
            position,
        )

    TRUE_STRINGS = {"TRUE", "YES", "ON", "1"}
    FALSE_STRINGS = {"FALSE", "NO", "OFF", "0", "NONE", ""}

    def _complete_keyword_arguments_at_position(
        self,
        keyword_doc: KeywordDoc,
        tokens: Tuple[Token, ...],
        token_at_position: Token,
        position: Position,
    ) -> Optional[List[CompletionItem]]:
        if keyword_doc.is_any_run_keyword():
            return None

        (
            argument_index,
            kw_arguments,
            argument_token,
        ) = self.get_argument_info_at_position(keyword_doc, tokens, token_at_position, position)

        complete_argument_names = True
        complete_argument_values = True
        if kw_arguments is None:
            return None

        completion_range = range_from_token(argument_token or token_at_position)
        completion_range.end = range_from_token(token_at_position).end
        has_name = False
        if (w := whitespace_at_begin_of_token(token_at_position)) > 0:
            if w > 1 and range_from_token(token_at_position).start.character + 1 < position.character:
                completion_range.start = position
                if token_at_position.type == Token.SEPARATOR:
                    completion_range.end = position
            elif completion_range.start != position:
                return None
        else:
            name_or_value, value = split_from_equals((argument_token or token_at_position).value)
            if value is not None and name_or_value and any(k for k in kw_arguments if k.name == name_or_value):
                has_name = True
                equal_index = (argument_token or token_at_position).value.index("=")
                if position.character <= completion_range.start.character + equal_index:
                    complete_argument_values = False
                    completion_range.end.character = completion_range.start.character + equal_index + 1
                else:
                    complete_argument_names = False
                    completion_range.start.character = completion_range.start.character + equal_index + 1

        result = []

        arg_index_before = tokens.index(argument_token or token_at_position) - 1
        if arg_index_before >= 0:
            while arg_index_before >= 0 and tokens[arg_index_before].type != Token.ARGUMENT:
                arg_index_before -= 1

        before_is_named = False
        if arg_index_before >= 0 and tokens[arg_index_before].type == Token.ARGUMENT:
            name_or_value, value = split_from_equals((tokens[arg_index_before]).value)
            before_is_named = (
                value is not None and name_or_value and any(k for k in kw_arguments if k.name == name_or_value)
            )

        if before_is_named and not has_name:
            complete_argument_values = False

        if (
            complete_argument_values
            and argument_index >= 0
            and keyword_doc.parent is not None
            and argument_index < len(kw_arguments)
            and (
                kw_arguments[argument_index].kind
                in [
                    KeywordArgumentKind.POSITIONAL_ONLY,
                    KeywordArgumentKind.POSITIONAL_OR_NAMED,
                    KeywordArgumentKind.VAR_POSITIONAL,
                ]
                or has_name
            )
        ):
            type_infos = keyword_doc.parent.get_types(kw_arguments[argument_index].types)
            for i, type_info in enumerate(type_infos):
                if type_info.name == "boolean":
                    if get_robot_version() >= (6, 0) and self.namespace.languages:
                        languages = self.namespace.languages.languages

                        if self.config.filter_default_language:
                            languages = [v for v in languages if v.code != "en"]

                        bool_snippets = [
                            *((s, True) for s in itertools.chain(*(lang.true_strings for lang in languages))),
                            *((s, False) for s in itertools.chain(*(lang.false_strings for lang in languages))),
                        ]
                    else:
                        bool_snippets = [
                            *((s, True) for s in self.TRUE_STRINGS),
                            *((s, False) for s in self.FALSE_STRINGS),
                        ]

                    if ("1", True) not in bool_snippets:
                        bool_snippets.append(("1", True))
                    if ("0", False) not in bool_snippets:
                        bool_snippets.append(("0", False))

                    for i, b_snippet in enumerate(bool_snippets):
                        if b_snippet[0]:
                            result.append(
                                CompletionItem(
                                    label=b_snippet[0],
                                    kind=CompletionItemKind.CONSTANT,
                                    detail=f"{type_info.name}({b_snippet[1]})",
                                    documentation=MarkupContent(
                                        MarkupKind.MARKDOWN,
                                        type_info.to_markdown(),
                                    ),
                                    sort_text=f"01_000_{int(not b_snippet[1])}_{b_snippet[0]}",
                                    insert_text_format=InsertTextFormat.PLAIN_TEXT,
                                    text_edit=TextEdit(
                                        range=completion_range,
                                        new_text=b_snippet[0],
                                    ),
                                )
                            )
                elif type_info.name == "None":
                    result.append(
                        CompletionItem(
                            label="None",
                            kind=CompletionItemKind.CONSTANT,
                            detail=f"{type_info.name}",
                            documentation=MarkupContent(MarkupKind.MARKDOWN, type_info.to_markdown()),
                            sort_text="50_000_None",
                            insert_text_format=InsertTextFormat.PLAIN_TEXT,
                            text_edit=TextEdit(range=completion_range, new_text="None"),
                        )
                    )
                    result.append(
                        CompletionItem(
                            label="${None}",
                            kind=CompletionItemKind.VARIABLE,
                            detail=f"{type_info.name}",
                            documentation=MarkupContent(MarkupKind.MARKDOWN, type_info.to_markdown()),
                            sort_text="50_001_None",
                            insert_text_format=InsertTextFormat.PLAIN_TEXT,
                            text_edit=TextEdit(range=completion_range, new_text="${None}"),
                        )
                    )
                if type_info.members:
                    for member_index, member in enumerate(type_info.members):
                        result.append(
                            CompletionItem(
                                label=member.name,
                                kind=CompletionItemKind.ENUM_MEMBER,
                                detail=type_info.name,
                                documentation=MarkupContent(
                                    MarkupKind.MARKDOWN,
                                    f"```python\n{member.name} = {member.value}\n```\n\n{type_info.to_markdown()}",
                                ),
                                sort_text=f"09_{i:03}_{member_index:03}_{member.name}",
                                insert_text_format=InsertTextFormat.PLAIN_TEXT,
                                text_edit=TextEdit(range=completion_range, new_text=member.name),
                            )
                        )
                if type_info.items:
                    snippets = [
                        (
                            "{"
                            + ", ".join(
                                (f'"{m.key}"' + ": ${" + str(i + 1) + "}")
                                for i, m in enumerate(type_info.items)
                                if m.required
                            )
                            + "}"
                            if any(m.required for m in type_info.items) and any(not m.required for m in type_info.items)
                            else ""
                        ),
                        "{"
                        + ", ".join((f'"{m.key}"' + ": ${" + str(i + 1) + "}") for i, m in enumerate(type_info.items))
                        + "}",
                    ]
                    for i, snippet in enumerate(snippets):
                        if snippet:
                            result.append(
                                CompletionItem(
                                    label=snippet,
                                    kind=CompletionItemKind.STRUCT,
                                    detail=type_info.name,
                                    documentation=MarkupContent(
                                        MarkupKind.MARKDOWN,
                                        type_info.to_markdown(),
                                    ),
                                    sort_text=f"08_{i:03}_{snippet}",
                                    insert_text_format=InsertTextFormat.SNIPPET,
                                    text_edit=TextEdit(range=completion_range, new_text=snippet),
                                )
                            )

        if complete_argument_names:
            known_names = []

            if (argument_token or token_at_position).type == Token.ARGUMENT and position == range_from_token(
                argument_token or token_at_position
            ).start:
                completion_range = Range(position, position)

            elif keyword_doc.arguments_spec is not None:
                positional, named = keyword_doc.arguments_spec.resolve(
                    [a.value for a in [t for t in tokens if t.type == Token.ARGUMENT]],
                    None,
                    resolve_variables_until=keyword_doc.args_to_process,
                    resolve_named=not keyword_doc.is_any_run_keyword(),
                    validate=False,
                )

                for i in range(len(positional)):
                    if i != argument_index and i < len(kw_arguments):
                        known_names.append(kw_arguments[i].name)
                for n, _ in named:
                    known_names.append(n)

            preselected = -1
            if known_names and before_is_named:
                n = known_names[-1]
                preselected = (
                    next(
                        (i for i, e in enumerate(kw_arguments) if e.name == n),
                        -1,
                    )
                    + 1
                )
                if preselected >= len(kw_arguments):
                    preselected = (
                        next(
                            (i for i, e in enumerate(kw_arguments) if e.name == n),
                            -1,
                        )
                        - 1
                    )

            result += [
                CompletionItem(
                    label=f"{e.signature(False)}=",
                    kind=CompletionItemKind.VARIABLE,
                    detail="Argument",
                    filter_text=e.name,
                    sort_text=f"80_{i:03}_{e.name}=",
                    insert_text_format=InsertTextFormat.PLAIN_TEXT,
                    text_edit=TextEdit(range=completion_range, new_text=f"{e.name}="),
                    command=Command("", "editor.action.triggerSuggest", []),
                    preselect=True if i == preselected else None,
                )
                for i, e in enumerate(kw_arguments)
                if e.name not in known_names
                and e.kind
                not in [
                    KeywordArgumentKind.VAR_POSITIONAL,
                    KeywordArgumentKind.VAR_NAMED,
                    KeywordArgumentKind.NAMED_ONLY_MARKER,
                    KeywordArgumentKind.POSITIONAL_ONLY_MARKER,
                ]
            ]

        return result

    def complete_KeywordCall(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        return self._complete_KeywordCall_or_Fixture(Token.KEYWORD, node, nodes_at_position, position, context)

    def complete_Fixture(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        name_token = cast(Fixture, node).get_token(Token.NAME)
        if name_token is None or name_token.value is None or name_token.value.upper() in ("", "NONE"):
            return None

        return self._complete_KeywordCall_or_Fixture(Token.NAME, node, nodes_at_position, position, context)

    def create_tags_completion_items(self, range: Optional[Range]) -> List[CompletionItem]:
        built_in_tags = {
            "robot:continue-on-failure",
            "robot:stop-on-failure",
            "robot:no-dry-run",
            "robot:exit",
        }

        if get_robot_version() >= (5, 0):
            built_in_tags.add("robot:skip")
            built_in_tags.add("robot:skip-on-failure")
            built_in_tags.add("robot:exclude")
            built_in_tags.add("robot:recursive-continue-on-failure")

        if get_robot_version() >= (6, 0):
            built_in_tags.add("robot:recursive-stop-on-failure")
            built_in_tags.add("robot:private")

        if get_robot_version() >= (6, 1):
            built_in_tags.add("robot:flatten")

        return [
            CompletionItem(
                label=tag,
                kind=CompletionItemKind.ENUM_MEMBER,
                detail="Reserved Tag",
                sort_text=f"080_{tag}",
                insert_text_format=InsertTextFormat.PLAIN_TEXT,
                text_edit=TextEdit(range=range, new_text=f"{tag}") if range is not None else None,
            )
            for tag in built_in_tags
        ]

    def _complete_ForceTags_or_KeywordTags_or_DefaultTags_Tags(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        statement = cast(Statement, node)
        tokens = get_tokens_at_position(statement, position, True)

        if not tokens:
            return None

        if tokens[-1].type == Token.ARGUMENT:
            return self.create_tags_completion_items(range_from_token(tokens[-1]))

        if len(tokens) > 1 and tokens[-2].type == Token.ARGUMENT:
            return self.create_tags_completion_items(range_from_token(tokens[-2]))

        if whitespace_at_begin_of_token(tokens[-1]) >= 2:
            return self.create_tags_completion_items(None)

        return None

    def complete_ForceTags(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        return self._complete_ForceTags_or_KeywordTags_or_DefaultTags_Tags(node, nodes_at_position, position, context)

    def complete_KeywordTags(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        return self._complete_ForceTags_or_KeywordTags_or_DefaultTags_Tags(node, nodes_at_position, position, context)

    def complete_DefaultTags(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        return self._complete_ForceTags_or_KeywordTags_or_DefaultTags_Tags(node, nodes_at_position, position, context)

    def complete_Tags(  # noqa: N802
        self,
        node: ast.AST,
        nodes_at_position: List[ast.AST],
        position: Position,
        context: Optional[CompletionContext],
    ) -> Union[List[CompletionItem], CompletionList, None]:
        return self._complete_ForceTags_or_KeywordTags_or_DefaultTags_Tags(node, nodes_at_position, position, context)
