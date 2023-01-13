from __future__ import annotations

import ast
import operator
import re
from dataclasses import dataclass
from enum import Enum
from functools import reduce
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Dict,
    FrozenSet,
    List,
    Optional,
    Set,
    Tuple,
    Union,
    cast,
)

from ....utils.async_itertools import async_dropwhile, async_takewhile
from ....utils.logging import LoggingDescriptor
from ...common.decorators import language_id
from ...common.lsp_types import (
    Range,
    SemanticTokenModifiers,
    SemanticTokens,
    SemanticTokensDelta,
    SemanticTokensDeltaPartialResult,
    SemanticTokensPartialResult,
    SemanticTokenTypes,
)
from ...common.text_document import TextDocument
from ..diagnostics.library_doc import (
    ALL_RUN_KEYWORDS_MATCHERS,
    BUILTIN_LIBRARY_NAME,
    KeywordArgumentKind,
    KeywordDoc,
    KeywordMatcher,
    LibraryDoc,
)
from ..diagnostics.namespace import (
    DEFAULT_BDD_PREFIXES,
    LibraryEntry,
    Namespace,
    ResourceEntry,
)
from ..utils import async_ast
from ..utils.ast_utils import (
    HasTokens,
    Token,
    iter_over_keyword_names_and_owners,
    token_in_range,
)
from ..utils.version import get_robot_version
from .model_helper import ModelHelperMixin

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .protocol_part import RobotLanguageServerProtocolPart

ROBOT_KEYWORD_INNER = "KEYWORD_INNER"
ROBOT_NAMED_ARGUMENT = "NAMED_ARGUMENT"
ROBOT_OPERATOR = "OPERATOR"


class RobotSemTokenTypes(Enum):
    SECTION = "section"
    SETTING_IMPORT = "settingImport"
    SETTING = "setting"
    HEADER = "header"
    HEADER_SETTINGS = "headerSettings"
    HEADER_VARIABLE = "headerVariable"
    HEADER_TESTCASE = "headerTestcase"
    HEADER_COMMENT = "headerComment"
    HEADER_KEYWORD = "headerKeyword"
    TESTCASE_NAME = "testcaseName"
    KEYWORD_NAME = "keywordName"
    CONTROL_FLOW = "controlFlow"
    ARGUMENT = "argument"
    EMBEDDED_ARGUMENT = "embeddedArgument"
    VARIABLE = "variable"
    KEYWORD = "keywordCall"
    KEYWORD_INNER = "keywordCallInner"
    BDD_PREFIX = "bddPrefix"
    NAME = "nameCall"
    CONTINUATION = "continuation"
    SEPARATOR = "separator"
    TERMINATOR = "terminator"
    FOR_SEPARATOR = "forSeparator"
    VARIABLE_BEGIN = "variableBegin"
    VARIABLE_END = "variableEnd"
    ESCAPE = "escape"
    NAMESPACE = "namespace"
    ERROR = "error"
    CONFIG = "config"
    NAMED_ARGUMENT = "namedArgument"


class RobotSemTokenModifiers(Enum):
    BUILTIN = "builtin"


@dataclass
class SemTokenInfo:
    lineno: int
    col_offset: int
    length: int
    sem_token_type: Enum
    sem_modifiers: Optional[Set[Enum]] = None

    @classmethod
    def from_token(
        cls,
        token: Token,
        sem_token_type: Enum,
        sem_modifiers: Optional[Set[Enum]] = None,
        col_offset: Optional[int] = None,
        length: Optional[int] = None,
    ) -> SemTokenInfo:
        return cls(
            token.lineno,
            col_offset if col_offset is not None else token.col_offset,
            length if length is not None else token.end_col_offset - token.col_offset,
            sem_token_type,
            sem_modifiers,
        )


class RobotSemanticTokenProtocolPart(RobotLanguageServerProtocolPart, ModelHelperMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)
        parent.semantic_tokens.token_types += [e for e in RobotSemTokenTypes]
        parent.semantic_tokens.token_modifiers += [e for e in RobotSemTokenModifiers]

        parent.semantic_tokens.collect_full.add(self.collect_full)
        # parent.semantic_tokens.collect_range.add(self.collect_range)
        # parent.semantic_tokens.collect_full_delta.add(self.collect_full_delta)

        parent.documents_cache.namespace_invalidated.add(self.namespace_invalidated)

    @language_id("robotframework")
    @_logger.call
    async def namespace_invalidated(self, sender: Any, namespace: Namespace) -> None:
        await self.parent.semantic_tokens.refresh()

    @classmethod
    def generate_mapping(cls) -> Dict[str, Tuple[Enum, Optional[Set[Enum]]]]:
        from robot.parsing.lexer.tokens import Token as RobotToken

        definition: Dict[FrozenSet[str], Tuple[Enum, Optional[Set[Enum]]]] = {
            frozenset(RobotToken.HEADER_TOKENS): (RobotSemTokenTypes.HEADER, None),
            frozenset({RobotToken.SETTING_HEADER}): (RobotSemTokenTypes.HEADER_SETTINGS, None),
            frozenset({RobotToken.VARIABLE_HEADER}): (RobotSemTokenTypes.HEADER_VARIABLE, None),
            frozenset({RobotToken.TESTCASE_HEADER}): (RobotSemTokenTypes.HEADER_TESTCASE, None),
            frozenset({RobotToken.KEYWORD_HEADER}): (RobotSemTokenTypes.HEADER_KEYWORD, None),
            frozenset({RobotToken.COMMENT_HEADER}): (RobotSemTokenTypes.HEADER_COMMENT, None),
            frozenset({RobotToken.COMMENT}): (SemanticTokenTypes.COMMENT, None),
            frozenset(RobotToken.SETTING_TOKENS): (RobotSemTokenTypes.SETTING, None),
            frozenset({RobotToken.LIBRARY, RobotToken.RESOURCE, RobotToken.VARIABLES, RobotToken.WITH_NAME}): (
                RobotSemTokenTypes.SETTING_IMPORT,
                None,
            ),
            frozenset({RobotToken.TESTCASE_NAME}): (
                RobotSemTokenTypes.TESTCASE_NAME,
                {SemanticTokenModifiers.DECLARATION},
            ),
            frozenset({RobotToken.KEYWORD_NAME}): (
                RobotSemTokenTypes.KEYWORD_NAME,
                {SemanticTokenModifiers.DECLARATION},
            ),
            frozenset(
                {
                    RobotToken.RETURN,
                    RobotToken.FOR,
                    RobotToken.FOR_SEPARATOR,
                    RobotToken.END,
                    RobotToken.IF,
                    RobotToken.ELSE_IF,
                    RobotToken.ELSE,
                }
            ): (RobotSemTokenTypes.CONTROL_FLOW, None),
            frozenset({RobotToken.FOR_SEPARATOR}): (RobotSemTokenTypes.FOR_SEPARATOR, None),
            frozenset({RobotToken.ARGUMENT}): (RobotSemTokenTypes.ARGUMENT, None),
            frozenset({RobotToken.VARIABLE, RobotToken.ASSIGN}): (RobotSemTokenTypes.VARIABLE, None),
            frozenset({RobotToken.KEYWORD}): (RobotSemTokenTypes.KEYWORD, None),
            frozenset({ROBOT_KEYWORD_INNER}): (RobotSemTokenTypes.KEYWORD_INNER, None),
            frozenset({ROBOT_NAMED_ARGUMENT}): (RobotSemTokenTypes.NAMED_ARGUMENT, None),
            frozenset({ROBOT_OPERATOR}): (SemanticTokenTypes.OPERATOR, None),
            frozenset({RobotToken.NAME}): (RobotSemTokenTypes.NAME, None),
            frozenset({RobotToken.CONTINUATION}): (RobotSemTokenTypes.CONTINUATION, None),
            frozenset({RobotToken.SEPARATOR}): (RobotSemTokenTypes.SEPARATOR, None),
            frozenset({RobotToken.EOL, RobotToken.EOS}): (RobotSemTokenTypes.TERMINATOR, None),
            frozenset({RobotToken.ERROR, RobotToken.FATAL_ERROR}): (RobotSemTokenTypes.ERROR, None),
        }

        if get_robot_version() >= (5, 0):
            definition.update(
                {
                    frozenset(
                        {
                            RobotToken.INLINE_IF,
                            RobotToken.TRY,
                            RobotToken.EXCEPT,
                            RobotToken.FINALLY,
                            RobotToken.AS,
                            RobotToken.WHILE,
                            RobotToken.RETURN_STATEMENT,
                            RobotToken.CONTINUE,
                            RobotToken.BREAK,
                            RobotToken.OPTION,
                        }
                    ): (RobotSemTokenTypes.CONTROL_FLOW, None),
                }
            )

        if get_robot_version() >= (6, 0):
            definition.update(
                {
                    frozenset(
                        {
                            RobotToken.CONFIG,
                        }
                    ): (RobotSemTokenTypes.CONFIG, None),
                }
            )

        result: Dict[str, Tuple[Enum, Optional[Set[Enum]]]] = {}
        for k, v in definition.items():
            for e in k:
                result[e] = v

        return result

    __mapping: Optional[Dict[str, Tuple[Enum, Optional[Set[Enum]]]]] = None

    @classmethod
    def mapping(cls) -> Dict[str, Tuple[Enum, Optional[Set[Enum]]]]:
        if cls.__mapping is None:
            cls.__mapping = cls.generate_mapping()
        return cls.__mapping

    ESCAPE_REGEX = re.compile(
        r"(?P<t>[^\\]+)|(?P<x>\\([^xuU]|x[0-0a-f]{2}|u[0-9a-f]{4}|U[0-9a-f]{8}){0,1})", re.MULTILINE | re.DOTALL
    )
    BDD_TOKEN_REGEX = re.compile(r"^(Given|When|Then|And|But)\s", flags=re.IGNORECASE)

    BUILTIN_MATCHER = KeywordMatcher("BuiltIn")

    @classmethod
    async def generate_sem_sub_tokens(
        cls,
        namespace: Namespace,
        builtin_library_doc: Optional[LibraryDoc],
        libraries_matchers: Dict[KeywordMatcher, LibraryEntry],
        resources_matchers: Dict[KeywordMatcher, ResourceEntry],
        token: Token,
        node: ast.AST,
        col_offset: Optional[int] = None,
        length: Optional[int] = None,
    ) -> AsyncGenerator[SemTokenInfo, None]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import (
            Arguments,
            Documentation,
            Fixture,
            LibraryImport,
            Metadata,
            ResourceImport,
            Template,
            TestTemplate,
            VariablesImport,
        )
        from robot.variables.search import is_variable

        sem_info = cls.mapping().get(token.type, None) if token.type is not None else None
        if sem_info is not None:
            sem_type, sem_mod = sem_info

            if isinstance(node, (Documentation, Metadata)):
                sem_mod = {SemanticTokenModifiers.DOCUMENTATION}

            if token.type == RobotToken.VARIABLE:
                if is_variable(token.value, "$@&%"):
                    if col_offset is None:
                        col_offset = token.col_offset
                    if length is None:
                        length = token.end_col_offset - token.col_offset

                    last_index = token.value.rfind("}")
                    if last_index >= 0:
                        yield SemTokenInfo(token.lineno, col_offset, 2, RobotSemTokenTypes.VARIABLE_BEGIN, sem_mod)

                        yield SemTokenInfo.from_token(
                            token,
                            SemanticTokenTypes.PARAMETER if isinstance(node, Arguments) else sem_type,
                            sem_mod,
                            col_offset + 2,
                            last_index - 2,
                        )

                        yield SemTokenInfo(
                            token.lineno, col_offset + last_index, 1, RobotSemTokenTypes.VARIABLE_END, sem_mod
                        )

                        if length - last_index > 0:
                            yield SemTokenInfo.from_token(
                                token, sem_type, sem_mod, col_offset + last_index + 1, length - last_index - 1
                            )
                    else:
                        yield SemTokenInfo.from_token(token, sem_type, sem_mod)

                else:
                    yield SemTokenInfo.from_token(token, sem_type, sem_mod)

            elif token.type == RobotToken.ARGUMENT and "\\" in token.value:
                if col_offset is None:
                    col_offset = token.col_offset

                for g in cls.ESCAPE_REGEX.finditer(token.value):
                    yield SemTokenInfo.from_token(
                        token,
                        sem_type if g.group("x") is None or g.end() - g.start() == 1 else RobotSemTokenTypes.ESCAPE,
                        sem_mod,
                        col_offset + g.start(),
                        g.end() - g.start(),
                    )
            elif token.type in [RobotToken.KEYWORD, ROBOT_KEYWORD_INNER] or (
                token.type == RobotToken.NAME and isinstance(node, (Fixture, Template, TestTemplate))
            ):
                if await namespace.find_keyword(token.value, raise_keyword_error=False, handle_bdd_style=False) is None:
                    bdd_len = 0

                    if get_robot_version() < (6, 0):
                        bdd_match = cls.BDD_TOKEN_REGEX.match(token.value)
                        if bdd_match:
                            bdd_len = len(bdd_match.group(1))
                    else:
                        parts = token.value.split()
                        if len(parts) > 1:
                            for index in range(1, len(parts)):
                                prefix = " ".join(parts[:index]).title()
                                if prefix.title() in (
                                    namespace.languages.bdd_prefixes
                                    if namespace.languages is not None
                                    else DEFAULT_BDD_PREFIXES
                                ):
                                    bdd_len = len(prefix)
                                    break

                    if bdd_len > 0:
                        yield SemTokenInfo.from_token(
                            token, RobotSemTokenTypes.BDD_PREFIX, sem_mod, token.col_offset, bdd_len
                        )
                        yield SemTokenInfo.from_token(token, sem_type, sem_mod, token.col_offset + bdd_len, 1)

                        token = RobotToken(
                            token.type,
                            token.value[bdd_len + 1 :],
                            token.lineno,
                            token.col_offset + bdd_len + 1,
                            token.error,
                        )

                if col_offset is None:
                    col_offset = token.col_offset

                kw_namespace: Optional[str] = None
                kw: str = token.value

                for lib, name in iter_over_keyword_names_and_owners(token.value):

                    if lib is not None and (
                        any(k for k in libraries_matchers.keys() if k == lib)
                        or any(k for k in resources_matchers.keys() if k == lib)
                    ):
                        kw_namespace = lib
                        if name:
                            kw = name
                        break

                kw_index = token.value.index(kw)

                if kw_namespace:
                    yield SemTokenInfo(
                        token.lineno,
                        col_offset,
                        len(kw_namespace),
                        RobotSemTokenTypes.NAMESPACE,
                        {RobotSemTokenModifiers.BUILTIN} if cls.BUILTIN_MATCHER == kw_namespace else None,
                    )
                    yield SemTokenInfo(
                        token.lineno,
                        col_offset + len(kw_namespace),
                        1,
                        SemanticTokenTypes.OPERATOR,
                    )

                if builtin_library_doc is not None and kw in builtin_library_doc.keywords:
                    doc = await namespace.find_keyword(token.value)
                    if doc is not None and doc.libname == cls.BUILTIN_MATCHER and doc.matcher == kw:
                        if not sem_mod:
                            sem_mod = set()
                        sem_mod.add(RobotSemTokenModifiers.BUILTIN)

                kw_doc = await namespace.find_keyword(token.value, raise_keyword_error=False)
                if kw_doc is not None and kw_doc.is_embedded:
                    if get_robot_version() >= (6, 0):
                        m = kw_doc.matcher.embedded_arguments.match(kw)
                    else:
                        m = kw_doc.matcher.embedded_arguments.name.match(kw)

                    if m and m.lastindex is not None:
                        start, end = m.span(0)
                        for i in range(1, m.lastindex + 1):
                            arg_start, arg_end = m.span(i)
                            yield SemTokenInfo.from_token(
                                token, sem_type, sem_mod, col_offset + kw_index + start, arg_start - start
                            )
                            yield SemTokenInfo.from_token(
                                token,
                                RobotSemTokenTypes.EMBEDDED_ARGUMENT,
                                sem_mod,
                                col_offset + kw_index + arg_start,
                                arg_end - arg_start,
                            )
                            start = arg_end + 1

                        if start < end:
                            yield SemTokenInfo.from_token(
                                token, sem_type, sem_mod, col_offset + kw_index + start, end - start
                            )

                else:
                    yield SemTokenInfo.from_token(token, sem_type, sem_mod, col_offset + kw_index, len(kw))
            elif token.type == RobotToken.NAME and isinstance(node, (LibraryImport, ResourceImport, VariablesImport)):
                yield SemTokenInfo.from_token(token, RobotSemTokenTypes.NAMESPACE, sem_mod, col_offset, length)
            elif get_robot_version() >= (5, 0) and token.type == RobotToken.OPTION:
                from robot.parsing.model.statements import ExceptHeader, WhileHeader

                if (
                    isinstance(node, ExceptHeader)
                    and token.value.startswith("type=")
                    or isinstance(node, WhileHeader)
                    and token.value.startswith("limit=")
                ):
                    if col_offset is None:
                        col_offset = token.col_offset

                    name, value = token.value.split("=", 1)
                    yield SemTokenInfo.from_token(token, RobotSemTokenTypes.VARIABLE, sem_mod, col_offset, len(name))
                    yield SemTokenInfo.from_token(
                        token, SemanticTokenTypes.OPERATOR, sem_mod, col_offset + len(name), 1
                    )
                    yield SemTokenInfo.from_token(token, sem_type, sem_mod, col_offset + len(name) + 1, len(value))
                else:
                    yield SemTokenInfo.from_token(token, sem_type, sem_mod, col_offset, length)
            elif (
                token.type in RobotToken.SETTING_TOKENS
                and token.value
                and token.value[0] == "["
                and token.value[-1] == "]"
            ):
                if col_offset is None:
                    col_offset = token.col_offset
                if length is None:
                    length = token.end_col_offset - token.col_offset

                yield SemTokenInfo.from_token(token, SemanticTokenTypes.OPERATOR, sem_mod, col_offset, 1)
                yield SemTokenInfo.from_token(token, sem_type, sem_mod, col_offset + 1, length - 2)
                yield SemTokenInfo.from_token(token, SemanticTokenTypes.OPERATOR, sem_mod, col_offset + length - 1, 1)
            else:
                yield SemTokenInfo.from_token(token, sem_type, sem_mod, col_offset, length)

    async def generate_sem_tokens(
        self,
        token: Token,
        node: ast.AST,
        namespace: Namespace,
        builtin_library_doc: Optional[LibraryDoc],
        libraries_matchers: Dict[KeywordMatcher, LibraryEntry],
        resources_matchers: Dict[KeywordMatcher, ResourceEntry],
    ) -> AsyncGenerator[SemTokenInfo, None]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Variable
        from robot.utils.escaping import split_from_equals

        if token.type in {RobotToken.ARGUMENT, RobotToken.TESTCASE_NAME, RobotToken.KEYWORD_NAME}:

            if isinstance(node, Variable) and token.type == RobotToken.ARGUMENT and node.name and node.name[0] == "&":
                name, value = split_from_equals(token.value)
                if value is not None:
                    length = len(name)

                    yield SemTokenInfo.from_token(
                        RobotToken(ROBOT_NAMED_ARGUMENT, name, token.lineno, token.col_offset),
                        RobotSemTokenTypes.NAMED_ARGUMENT,
                    )
                    yield SemTokenInfo.from_token(
                        RobotToken(ROBOT_OPERATOR, "=", token.lineno, token.col_offset + length),
                        SemanticTokenTypes.OPERATOR,
                    )
                    token = RobotToken(token.type, value, token.lineno, token.col_offset + length + 1, token.error)

            for sub_token in self._tokenize_variables(
                token,
                ignore_errors=True,
                identifiers="$" if token.type == RobotToken.KEYWORD_NAME else "$@&%",
            ):
                async for e in self.generate_sem_sub_tokens(
                    namespace, builtin_library_doc, libraries_matchers, resources_matchers, sub_token, node
                ):
                    yield e

        else:
            async for e in self.generate_sem_sub_tokens(
                namespace, builtin_library_doc, libraries_matchers, resources_matchers, token, node
            ):
                yield e

    async def generate_run_kw_tokens(
        self,
        namespace: Namespace,
        builtin_library_doc: Optional[LibraryDoc],
        libraries_matchers: Dict[KeywordMatcher, LibraryEntry],
        resources_matchers: Dict[KeywordMatcher, ResourceEntry],
        kw_doc: Optional[KeywordDoc],
        kw_token: Token,
        arguments: List[Token],
        node: ast.AST,
    ) -> AsyncGenerator[Tuple[Token, ast.AST], None]:
        from robot.parsing.lexer import Token as RobotToken
        from robot.utils.escaping import unescape

        async def skip_non_data_tokens() -> AsyncGenerator[Tuple[Token, ast.AST], None]:
            nonlocal arguments
            while arguments and arguments[0] and arguments[0].type in RobotToken.NON_DATA_TOKENS:

                yield arguments[0], node,
                arguments = arguments[1:]

        if kw_doc is not None and kw_doc.is_any_run_keyword():
            yield kw_token, node

            async for b in skip_non_data_tokens():
                yield b

            if kw_doc.is_run_keyword() and len(arguments) > 0:
                token = arguments[0]
                async for b in self.generate_run_kw_tokens(
                    namespace,
                    builtin_library_doc,
                    libraries_matchers,
                    resources_matchers,
                    await namespace.find_keyword(unescape(token.value), raise_keyword_error=False),
                    RobotToken(ROBOT_KEYWORD_INNER, token.value, token.lineno, token.col_offset, token.error),
                    arguments[1:],
                    node,
                ):
                    yield b
            elif kw_doc.is_run_keyword_with_condition() and len(arguments) > 0:
                cond_count = kw_doc.run_keyword_condition_count()
                for _ in range(cond_count):
                    yield arguments[0], node,
                    arguments = arguments[1:]

                    async for b in skip_non_data_tokens():
                        yield b

                if len(arguments) > 0:
                    token = arguments[0]
                    async for b in self.generate_run_kw_tokens(
                        namespace,
                        builtin_library_doc,
                        libraries_matchers,
                        resources_matchers,
                        await namespace.find_keyword(unescape(token.value), raise_keyword_error=False),
                        RobotToken(ROBOT_KEYWORD_INNER, token.value, token.lineno, token.col_offset, token.error),
                        arguments[1:],
                        node,
                    ):
                        yield b
            elif kw_doc.is_run_keywords() and len(arguments) > 0:
                has_separator = False
                while arguments:
                    async for b in skip_non_data_tokens():
                        yield b

                    if not arguments:
                        break

                    token = arguments[0]
                    arguments = arguments[1:]

                    if token.value == "AND":
                        yield RobotToken(
                            RobotToken.ELSE, token.value, token.lineno, token.col_offset, token.error
                        ), node
                        continue

                    separator_token = next((e for e in arguments if e.value == "AND"), None)
                    args = []
                    if separator_token is not None:
                        args = arguments[: arguments.index(separator_token)]
                        arguments = arguments[arguments.index(separator_token) :]
                        has_separator = True
                    else:
                        if has_separator:
                            args = arguments
                            arguments = []

                    async for e in self.generate_run_kw_tokens(
                        namespace,
                        builtin_library_doc,
                        libraries_matchers,
                        resources_matchers,
                        await namespace.find_keyword(unescape(token.value), raise_keyword_error=False),
                        RobotToken(ROBOT_KEYWORD_INNER, token.value, token.lineno, token.col_offset, token.error),
                        args,
                        node,
                    ):
                        yield e
            elif kw_doc.is_run_keyword_if() and len(arguments) > 0:

                async def generate_run_kw_if() -> AsyncGenerator[Tuple[Token, ast.AST], None]:
                    nonlocal arguments

                    yield arguments[0], node,
                    arguments = arguments[1:]

                    while arguments:
                        async for b in skip_non_data_tokens():
                            yield b

                        if not arguments:
                            break

                        token = arguments[0]
                        arguments = arguments[1:]

                        if token.value in ["ELSE", "ELSE IF"]:
                            yield RobotToken(
                                RobotToken.ELSE, token.value, token.lineno, token.col_offset, token.error
                            ), node

                            if token.value == "ELSE IF":
                                async for b in skip_non_data_tokens():
                                    yield b

                                if not arguments:
                                    break

                                yield arguments[0], node
                                arguments = arguments[1:]
                            continue

                        inner_kw_doc = await namespace.find_keyword(unescape(token.value), raise_keyword_error=False)

                        if inner_kw_doc is not None and inner_kw_doc.is_run_keyword_if():
                            yield RobotToken(
                                ROBOT_KEYWORD_INNER, token.value, token.lineno, token.col_offset, token.error
                            ), node

                            arguments = arguments[1:]

                            async for b in skip_non_data_tokens():
                                yield b

                            async for e in generate_run_kw_if():
                                yield e

                            continue

                        separator_token = next((e for e in arguments if e.value in ["ELSE", "ELSE IF"]), None)
                        args = []

                        if separator_token is not None:
                            args = arguments[: arguments.index(separator_token)]
                            arguments = arguments[arguments.index(separator_token) :]
                        else:
                            args = arguments
                            arguments = []

                        async for e in self.generate_run_kw_tokens(
                            namespace,
                            builtin_library_doc,
                            libraries_matchers,
                            resources_matchers,
                            inner_kw_doc,
                            RobotToken(ROBOT_KEYWORD_INNER, token.value, token.lineno, token.col_offset, token.error),
                            args,
                            node,
                        ):
                            yield e

                async for e in generate_run_kw_if():
                    yield e
        else:
            async for a in self.generate_keyword_tokens(namespace, kw_token, arguments, node, kw_doc):
                yield a

    async def generate_keyword_tokens(
        self,
        namespace: Namespace,
        kw_token: Token,
        arguments: List[Token],
        node: ast.AST,
        kw_doc: Optional[KeywordDoc] = None,
    ) -> AsyncGenerator[Tuple[Token, ast.AST], None]:
        from robot.parsing.lexer import Token as RobotToken
        from robot.utils.escaping import split_from_equals

        yield kw_token, node

        for token in arguments:
            if token.type in [RobotToken.ARGUMENT]:
                name, value = split_from_equals(token.value)
                if value is not None:
                    if kw_doc is None:
                        kw_doc = await namespace.find_keyword(kw_token.value)

                    if kw_doc and any(
                        v for v in kw_doc.args if v.kind == KeywordArgumentKind.VAR_NAMED or v.name == name
                    ):
                        length = len(name)
                        yield RobotToken(ROBOT_NAMED_ARGUMENT, name, token.lineno, token.col_offset), node

                        yield RobotToken(ROBOT_OPERATOR, "=", token.lineno, token.col_offset + length), node
                        yield RobotToken(
                            token.type, value, token.lineno, token.col_offset + length + 1, token.error
                        ), node

                        continue

            yield token, node

    @_logger.call
    async def _collect_internal(
        self,
        model: ast.AST,
        range: Optional[Range],
        namespace: Namespace,
        builtin_library_doc: Optional[LibraryDoc],
        libraries_matchers: Dict[KeywordMatcher, LibraryEntry],
        resources_matchers: Dict[KeywordMatcher, ResourceEntry],
    ) -> Union[SemanticTokens, SemanticTokensPartialResult, None]:

        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Fixture, KeywordCall, LibraryImport
        from robot.utils.escaping import split_from_equals

        data = []
        last_line = 0
        last_col = 0

        async def get_tokens() -> AsyncGenerator[Tuple[Token, ast.AST], None]:
            async for node in async_ast.iter_nodes(model):
                if isinstance(node, HasTokens):
                    if isinstance(node, LibraryImport):
                        lib_doc = await namespace.get_imported_library_libdoc(node.name, node.args, node.alias)
                        kw_doc = lib_doc.inits.keywords[0] if lib_doc and lib_doc.inits else None
                        if lib_doc is not None:

                            for token in node.tokens:
                                if token.type == RobotToken.ARGUMENT:
                                    name, value = split_from_equals(token.value)
                                    if (
                                        value is not None
                                        and kw_doc is not None
                                        and kw_doc.args
                                        and any(
                                            v
                                            for v in kw_doc.args
                                            if v.kind == KeywordArgumentKind.VAR_NAMED or v.name == name
                                        )
                                    ):
                                        length = len(name)
                                        yield RobotToken(
                                            ROBOT_NAMED_ARGUMENT, name, token.lineno, token.col_offset
                                        ), node

                                        yield RobotToken(
                                            ROBOT_OPERATOR, "=", token.lineno, token.col_offset + length
                                        ), node
                                        yield RobotToken(
                                            token.type,
                                            value,
                                            token.lineno,
                                            token.col_offset + length + 1,
                                            token.error,
                                        ), node

                                        continue

                                yield token, node
                            continue
                    if isinstance(node, (KeywordCall, Fixture)):
                        kw_token = cast(
                            Token,
                            node.get_token(RobotToken.KEYWORD)
                            if isinstance(node, KeywordCall)
                            else node.get_token(RobotToken.NAME),
                        )

                        for kw_res in node.tokens:
                            if kw_res == kw_token:
                                break
                            yield kw_res, node

                        if kw_token is not None:
                            kw: Optional[str] = None

                            for _, name in iter_over_keyword_names_and_owners(
                                self.strip_bdd_prefix(namespace, kw_token).value
                            ):
                                if name is not None:
                                    matcher = KeywordMatcher(name)
                                    if matcher in ALL_RUN_KEYWORDS_MATCHERS:
                                        kw = name
                            if kw:
                                kw_doc = await namespace.find_keyword(kw_token.value)
                                if kw_doc is not None and kw_doc.is_any_run_keyword():
                                    async for kw_res in self.generate_run_kw_tokens(
                                        namespace,
                                        builtin_library_doc,
                                        libraries_matchers,
                                        resources_matchers,
                                        kw_doc,
                                        kw_token,
                                        node.tokens[node.tokens.index(kw_token) + 1 :],
                                        node,
                                    ):
                                        yield kw_res
                                    continue
                            else:
                                async for kw_res in self.generate_keyword_tokens(
                                    namespace,
                                    kw_token,
                                    node.tokens[node.tokens.index(kw_token) + 1 :],
                                    node,
                                ):
                                    yield kw_res

                                continue

                    for token in node.tokens:
                        yield token, node

        async for robot_token, robot_node in async_takewhile(
            lambda t: range is None or token_in_range(t[0], range),
            async_dropwhile(
                lambda t: range is not None and not token_in_range(t[0], range),
                (
                    (t, n)
                    async for t, n in get_tokens()
                    if t.type not in [RobotToken.SEPARATOR, RobotToken.EOL, RobotToken.EOS]
                ),
            ),
        ):
            async for token in self.generate_sem_tokens(
                robot_token, robot_node, namespace, builtin_library_doc, libraries_matchers, resources_matchers
            ):
                current_line = token.lineno - 1

                data.append(current_line - last_line)

                if last_line != current_line:
                    last_col = token.col_offset
                    data.append(last_col)
                else:
                    delta = token.col_offset - last_col
                    data.append(delta)
                    last_col += delta

                last_line = current_line

                data.append(token.length)

                data.append(self.parent.semantic_tokens.token_types.index(token.sem_token_type))

                data.append(
                    reduce(
                        operator.or_,
                        (2 ** self.parent.semantic_tokens.token_modifiers.index(e) for e in token.sem_modifiers),
                    )
                    if token.sem_modifiers
                    else 0
                )

        return SemanticTokens(data=data)

    @_logger.call
    async def _collect(
        self, document: TextDocument, range: Optional[Range]
    ) -> Union[SemanticTokens, SemanticTokensPartialResult, None]:

        model = await self.parent.documents_cache.get_model(document, False)
        namespace = await self.parent.documents_cache.get_namespace(document)

        builtin_library_doc = next(
            (
                library.library_doc
                for library in (await namespace.get_libraries()).values()
                if library.name == BUILTIN_LIBRARY_NAME
                and library.import_name == BUILTIN_LIBRARY_NAME
                and library.import_range == Range.zero()
            ),
            None,
        )

        return await self._collect_internal(
            model,
            range,
            namespace,
            builtin_library_doc,
            await namespace.get_libraries_matchers(),
            await namespace.get_resources_matchers(),
        )

    @language_id("robotframework")
    @_logger.call
    async def collect_full(
        self, sender: Any, document: TextDocument, **kwargs: Any
    ) -> Union[SemanticTokens, SemanticTokensPartialResult, None]:
        return await self._collect(document, None)

    @language_id("robotframework")
    @_logger.call
    async def collect_range(
        self, sender: Any, document: TextDocument, range: Range, **kwargs: Any
    ) -> Union[SemanticTokens, SemanticTokensPartialResult, None]:
        return await self._collect(document, range)

    @language_id("robotframework")
    @_logger.call
    async def collect_full_delta(
        self, sender: Any, document: TextDocument, previous_result_id: str, **kwargs: Any
    ) -> Union[SemanticTokens, SemanticTokensDelta, SemanticTokensDeltaPartialResult, None]:
        return None
