import ast
import operator
import re
from dataclasses import dataclass
from enum import Enum
from functools import reduce
from itertools import dropwhile, takewhile
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    FrozenSet,
    Iterator,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
    cast,
)

from robot.parsing.lexer.tokens import Token
from robot.parsing.model.blocks import Section
from robot.parsing.model.statements import (
    Arguments,
    Documentation,
    Fixture,
    KeywordCall,
    LibraryImport,
    Metadata,
    ResourceImport,
    Statement,
    Template,
    TestTemplate,
    Variable,
    VariablesImport,
)
from robot.utils.escaping import unescape

from robotcode.core.concurrent import check_current_task_canceled
from robotcode.core.language import language_id
from robotcode.core.lsp.types import (
    Position,
    Range,
    SemanticTokenModifiers,
    SemanticTokens,
    SemanticTokensDelta,
    SemanticTokensDeltaPartialResult,
    SemanticTokensPartialResult,
    SemanticTokenTypes,
)
from robotcode.core.text_document import TextDocument, range_to_utf16
from robotcode.robot.diagnostics.keyword_finder import DEFAULT_BDD_PREFIXES
from robotcode.robot.diagnostics.library_doc import (
    ALL_RUN_KEYWORDS_MATCHERS,
    BUILTIN_LIBRARY_NAME,
    KeywordArgumentKind,
    KeywordDoc,
    KeywordMatcher,
    LibraryDoc,
)
from robotcode.robot.diagnostics.model_helper import ModelHelper
from robotcode.robot.diagnostics.namespace import Namespace
from robotcode.robot.utils import get_robot_version
from robotcode.robot.utils.ast import (
    cached_isinstance,
    iter_nodes,
    iter_over_keyword_names_and_owners,
    token_in_range,
)
from robotcode.robot.utils.variables import is_variable, split_from_equals

from .protocol_part import RobotLanguageServerProtocolPart

if get_robot_version() >= (5, 0):
    from robot.parsing.model.statements import ExceptHeader, WhileHeader

if get_robot_version() >= (7, 0):
    from robot.parsing.model.blocks import InvalidSection

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


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
    HEADER_TASK = "headerTask"
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
    VARIABLE_EXPRESSION = "variableExpression"
    ESCAPE = "escape"
    NAMESPACE = "namespace"
    ERROR = "error"
    CONFIG = "config"
    NAMED_ARGUMENT = "namedArgument"
    VAR = "var"
    DOCUMENTATION = "documentation"


class RobotSemTokenModifiers(Enum):
    BUILTIN = "builtin"
    EMBEDDED = "embedded"


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
    ) -> "SemTokenInfo":
        return cls(
            token.lineno,
            col_offset if col_offset is not None else token.col_offset,
            length if length is not None else token.end_col_offset - token.col_offset,
            sem_token_type,
            sem_modifiers,
        )


class RobotSemanticTokenProtocolPart(RobotLanguageServerProtocolPart):
    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)
        parent.semantic_tokens.token_types += list(RobotSemTokenTypes)
        parent.semantic_tokens.token_modifiers += list(RobotSemTokenModifiers)

        parent.semantic_tokens.collect_full.add(self.collect_full)
        # parent.semantic_tokens.collect_range.add(self.collect_range)
        # parent.semantic_tokens.collect_full_delta.add(self.collect_full_delta)

        self.parent.on_initialized.add(self._on_initialized)

    def _on_initialized(self, sender: Any) -> None:
        self.parent.documents_cache.namespace_invalidated.add(self.namespace_invalidated)

    @language_id("robotframework")
    def namespace_invalidated(self, sender: Any, namespace: Namespace) -> None:
        if namespace.document is not None and namespace.document.opened_in_editor:
            self.parent.semantic_tokens.refresh()

    @classmethod
    def generate_mapping(cls) -> Dict[str, Tuple[Enum, Optional[Set[Enum]]]]:
        definition: Dict[FrozenSet[str], Tuple[Enum, Optional[Set[Enum]]]] = {
            frozenset(Token.HEADER_TOKENS): (RobotSemTokenTypes.HEADER, None),
            frozenset({Token.SETTING_HEADER}): (
                RobotSemTokenTypes.HEADER_SETTINGS,
                None,
            ),
            frozenset({Token.VARIABLE_HEADER}): (
                RobotSemTokenTypes.HEADER_VARIABLE,
                None,
            ),
            frozenset({Token.TESTCASE_HEADER}): (
                RobotSemTokenTypes.HEADER_TESTCASE,
                None,
            ),
            frozenset({Token.KEYWORD_HEADER}): (
                RobotSemTokenTypes.HEADER_KEYWORD,
                None,
            ),
            frozenset({Token.COMMENT_HEADER}): (
                RobotSemTokenTypes.HEADER_COMMENT,
                None,
            ),
            frozenset({Token.COMMENT}): (SemanticTokenTypes.COMMENT, None),
            frozenset(Token.SETTING_TOKENS): (RobotSemTokenTypes.SETTING, None),
            frozenset({Token.TESTCASE_NAME}): (
                RobotSemTokenTypes.TESTCASE_NAME,
                {SemanticTokenModifiers.DECLARATION},
            ),
            frozenset({Token.KEYWORD_NAME}): (
                RobotSemTokenTypes.KEYWORD_NAME,
                {SemanticTokenModifiers.DECLARATION},
            ),
            frozenset(
                {
                    Token.RETURN,
                    Token.FOR,
                    Token.FOR_SEPARATOR,
                    Token.END,
                    Token.IF,
                    Token.ELSE_IF,
                    Token.ELSE,
                }
            ): (
                RobotSemTokenTypes.CONTROL_FLOW,
                None,
            ),
            frozenset({Token.FOR_SEPARATOR}): (
                RobotSemTokenTypes.FOR_SEPARATOR,
                None,
            ),
            frozenset({Token.ARGUMENT}): (RobotSemTokenTypes.ARGUMENT, None),
            frozenset({Token.VARIABLE, Token.ASSIGN}): (
                RobotSemTokenTypes.VARIABLE,
                None,
            ),
            frozenset({Token.KEYWORD}): (RobotSemTokenTypes.KEYWORD, None),
            frozenset({ROBOT_KEYWORD_INNER}): (
                RobotSemTokenTypes.KEYWORD_INNER,
                None,
            ),
            frozenset({ROBOT_NAMED_ARGUMENT}): (
                RobotSemTokenTypes.NAMED_ARGUMENT,
                None,
            ),
            frozenset({ROBOT_OPERATOR}): (SemanticTokenTypes.OPERATOR, None),
            frozenset({Token.NAME}): (RobotSemTokenTypes.ARGUMENT, None),
            frozenset({Token.CONTINUATION}): (
                RobotSemTokenTypes.CONTINUATION,
                None,
            ),
            frozenset({Token.SEPARATOR}): (RobotSemTokenTypes.SEPARATOR, None),
            frozenset({Token.EOL, Token.EOS}): (
                RobotSemTokenTypes.TERMINATOR,
                None,
            ),
            frozenset({Token.ERROR, Token.FATAL_ERROR}): (
                RobotSemTokenTypes.ERROR,
                None,
            ),
            frozenset({Token.LIBRARY, Token.RESOURCE, Token.VARIABLES}): (
                RobotSemTokenTypes.SETTING_IMPORT,
                None,
            ),
        }

        if get_robot_version() >= (5, 0):
            definition.update(
                {
                    frozenset(
                        {
                            Token.INLINE_IF,
                            Token.TRY,
                            Token.EXCEPT,
                            Token.FINALLY,
                            Token.AS,
                            Token.WHILE,
                            Token.RETURN_STATEMENT,
                            Token.CONTINUE,
                            Token.BREAK,
                            Token.OPTION,
                        }
                    ): (RobotSemTokenTypes.CONTROL_FLOW, None)
                }
            )

        if get_robot_version() >= (6, 0):
            definition.update(
                {
                    frozenset({Token.CONFIG}): (
                        RobotSemTokenTypes.CONFIG,
                        None,
                    ),
                    frozenset({Token.TASK_HEADER}): (
                        RobotSemTokenTypes.HEADER_TASK,
                        None,
                    ),
                }
            )
        if get_robot_version() >= (7, 0):
            definition.update(
                {
                    frozenset({Token.VAR}): (RobotSemTokenTypes.VAR, None),
                    frozenset({Token.AS}): (
                        RobotSemTokenTypes.SETTING_IMPORT,
                        None,
                    ),
                }
            )
        else:
            definition.update(
                {
                    frozenset({Token.WITH_NAME}): (
                        RobotSemTokenTypes.SETTING_IMPORT,
                        None,
                    )
                }
            )

        result: Dict[str, Tuple[Enum, Optional[Set[Enum]]]] = {}
        for k, v in definition.items():
            for e in k:
                result[e] = v

        return result

    _mapping: ClassVar[Optional[Dict[str, Tuple[Enum, Optional[Set[Enum]]]]]] = None

    @classmethod
    def mapping(cls) -> Dict[str, Tuple[Enum, Optional[Set[Enum]]]]:
        if cls._mapping is None:
            cls._mapping = cls.generate_mapping()
        return cls._mapping

    ESCAPE_REGEX: ClassVar = re.compile(
        r"(?P<t>[^\\]+)|(?P<x>\\(?:[\\nrt]|x[0-9A-Fa-f]{2}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}))|(?P<e>\\(?:[^\\nrt\\xuU]|[\\xuU][^0-9a-fA-F]))",
        re.MULTILINE | re.DOTALL,
    )
    BDD_TOKEN_REGEX: ClassVar = re.compile(r"^(Given|When|Then|And|But)\s", flags=re.IGNORECASE)

    BUILTIN_MATCHER: ClassVar = KeywordMatcher("BuiltIn", is_namespace=True)

    @classmethod
    def generate_sem_sub_tokens(
        cls,
        namespace: Namespace,
        builtin_library_doc: Optional[LibraryDoc],
        token: Token,
        node: ast.AST,
        col_offset: Optional[int] = None,
        length: Optional[int] = None,
        yield_arguments: bool = False,
    ) -> Iterator[SemTokenInfo]:
        sem_info = cls.mapping().get(token.type, None) if token.type is not None else None
        if sem_info is not None:
            sem_type, sem_mod = sem_info

            if token.type in [Token.DOCUMENTATION, Token.METADATA]:
                sem_mod = {SemanticTokenModifiers.DOCUMENTATION}

            if token.type in [Token.VARIABLE, Token.ASSIGN]:
                if is_variable(token.value, "$@&%"):
                    if col_offset is None:
                        col_offset = token.col_offset
                    if length is None:
                        length = token.end_col_offset - token.col_offset

                    last_index = token.value.rfind("}")

                    is_expr = token.value[1:2] == "{" and token.value[last_index - 1 : last_index] == "}"

                    if last_index >= 0:
                        yield SemTokenInfo(
                            token.lineno,
                            col_offset,
                            3 if is_expr else 2,
                            RobotSemTokenTypes.VARIABLE_BEGIN,
                            sem_mod,
                        )

                        yield SemTokenInfo(
                            token.lineno,
                            col_offset + ((last_index - 1) if is_expr else last_index),
                            2 if is_expr else 1,
                            RobotSemTokenTypes.VARIABLE_END,
                            sem_mod,
                        )

                        if length - last_index - 1 > 0:
                            yield SemTokenInfo.from_token(
                                token,
                                sem_type,
                                sem_mod,
                                col_offset + last_index + 1,
                                length - last_index - 1,
                            )
                    else:
                        yield SemTokenInfo.from_token(token, sem_type, sem_mod)

                else:
                    yield SemTokenInfo.from_token(token, sem_type, sem_mod)

            elif token.type in [Token.KEYWORD, ROBOT_KEYWORD_INNER] or (
                token.type == Token.NAME and cached_isinstance(node, Fixture, Template, TestTemplate)
            ):
                if (
                    namespace.find_keyword(
                        token.value,
                        raise_keyword_error=False,
                        handle_bdd_style=False,
                    )
                    is None
                ):
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
                            token,
                            RobotSemTokenTypes.BDD_PREFIX,
                            sem_mod,
                            token.col_offset,
                            bdd_len,
                        )
                        yield SemTokenInfo.from_token(
                            token,
                            sem_type,
                            sem_mod,
                            token.col_offset + bdd_len,
                            1,
                        )

                        token = Token(
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
                kw_doc = namespace.find_keyword(token.value, raise_keyword_error=False)

                (
                    lib_entry,
                    kw_namespace,
                ) = ModelHelper.get_namespace_info_from_keyword_token(namespace, token)
                if lib_entry is not None and kw_doc:
                    if kw_doc.parent != lib_entry.library_doc:
                        kw_namespace = None

                kw_index = len(kw_namespace) + 1 if kw_namespace else 0

                if token.type == Token.NAME and kw_doc is not None:
                    sem_type = RobotSemTokenTypes.KEYWORD

                if kw_namespace:
                    kw = token.value[kw_index:]

                    yield SemTokenInfo(
                        token.lineno,
                        col_offset,
                        len(kw_namespace),
                        RobotSemTokenTypes.NAMESPACE,
                        {RobotSemTokenModifiers.BUILTIN} if kw_namespace == cls.BUILTIN_MATCHER else None,
                    )
                    yield SemTokenInfo(
                        token.lineno,
                        col_offset + len(kw_namespace),
                        1,
                        SemanticTokenTypes.OPERATOR,
                    )

                if builtin_library_doc is not None and kw in builtin_library_doc.keywords:
                    if kw_doc is not None and kw_doc.libname == cls.BUILTIN_MATCHER and kw_doc.matcher == kw:
                        if not sem_mod:
                            sem_mod = set()
                        sem_mod.add(RobotSemTokenModifiers.BUILTIN)

                if kw_doc is not None and kw_doc.is_embedded and kw_doc.matcher.embedded_arguments:
                    if get_robot_version() >= (6, 0):
                        m = kw_doc.matcher.embedded_arguments.match(kw)
                    else:
                        m = kw_doc.matcher.embedded_arguments.name.match(kw)

                    if m and m.lastindex is not None:
                        start, end = m.span(0)
                        for i in range(1, m.lastindex + 1):
                            arg_start, arg_end = m.span(i)
                            yield SemTokenInfo.from_token(
                                token,
                                sem_type,
                                sem_mod,
                                col_offset + kw_index + start,
                                arg_start - start,
                            )

                            embedded_token = Token(
                                Token.ARGUMENT,
                                token.value[arg_start:arg_end],
                                token.lineno,
                                token.col_offset + arg_start,
                            )

                            for sub_token in ModelHelper.tokenize_variables(
                                embedded_token,
                                ignore_errors=True,
                                identifiers="$@&%",
                            ):
                                for e in cls.generate_sem_sub_tokens(
                                    namespace, builtin_library_doc, sub_token, node, yield_arguments=True
                                ):
                                    e.sem_modifiers = {RobotSemTokenModifiers.EMBEDDED}
                                    yield e

                            start = arg_end + 1

                        if start < end:
                            yield SemTokenInfo.from_token(
                                token,
                                sem_type,
                                sem_mod,
                                col_offset + kw_index + start,
                                end - start,
                            )

                else:
                    yield SemTokenInfo.from_token(token, sem_type, sem_mod, col_offset + kw_index, len(kw))
            elif token.type == Token.NAME and cached_isinstance(node, LibraryImport, ResourceImport, VariablesImport):
                if "\\" in token.value:
                    if col_offset is None:
                        col_offset = token.col_offset

                    for g in cls.ESCAPE_REGEX.finditer(token.value):
                        yield SemTokenInfo.from_token(
                            token,
                            RobotSemTokenTypes.NAMESPACE if g.group("x") is None else RobotSemTokenTypes.ESCAPE,
                            sem_mod,
                            col_offset + g.start(),
                            g.end() - g.start(),
                        )
                else:
                    yield SemTokenInfo.from_token(
                        token,
                        RobotSemTokenTypes.NAMESPACE,
                        sem_mod,
                        col_offset,
                        length,
                    )
            elif get_robot_version() >= (5, 0) and token.type == Token.OPTION:
                if (
                    cached_isinstance(node, ExceptHeader) or cached_isinstance(node, WhileHeader)
                ) and "=" in token.value:
                    if col_offset is None:
                        col_offset = token.col_offset

                    name, value = token.value.split("=", 1)
                    yield SemTokenInfo.from_token(
                        token,
                        RobotSemTokenTypes.VARIABLE,
                        sem_mod,
                        col_offset,
                        len(name),
                    )
                    yield SemTokenInfo.from_token(
                        token,
                        SemanticTokenTypes.OPERATOR,
                        sem_mod,
                        col_offset + len(name),
                        1,
                    )
                    yield SemTokenInfo.from_token(
                        token,
                        sem_type,
                        sem_mod,
                        col_offset + len(name) + 1,
                        len(value),
                    )
                else:
                    yield SemTokenInfo.from_token(token, sem_type, sem_mod, col_offset, length)
            elif (
                token.type in Token.SETTING_TOKENS and token.value and token.value[0] == "[" and token.value[-1] == "]"
            ):
                if col_offset is None:
                    col_offset = token.col_offset
                if length is None:
                    length = token.end_col_offset - token.col_offset

                yield SemTokenInfo.from_token(token, SemanticTokenTypes.OPERATOR, sem_mod, col_offset, 1)
                yield SemTokenInfo.from_token(token, sem_type, sem_mod, col_offset + 1, length - 2)
                yield SemTokenInfo.from_token(
                    token,
                    SemanticTokenTypes.OPERATOR,
                    sem_mod,
                    col_offset + length - 1,
                    1,
                )
            else:
                if (
                    yield_arguments
                    or token.type != Token.ARGUMENT
                    or token.type != Token.NAME
                    and cached_isinstance(node, Metadata)
                ):
                    yield SemTokenInfo.from_token(token, sem_type, sem_mod, col_offset, length)

    def generate_sem_tokens(
        self,
        token: Token,
        node: ast.AST,
        namespace: Namespace,
        builtin_library_doc: Optional[LibraryDoc],
    ) -> Iterator[SemTokenInfo]:
        if (
            token.type in {Token.ARGUMENT, Token.TESTCASE_NAME, Token.KEYWORD_NAME}
            or token.type == Token.NAME
            and cached_isinstance(node, VariablesImport, LibraryImport, ResourceImport)
        ):
            if (
                cached_isinstance(node, Variable) and token.type == Token.ARGUMENT and node.name and node.name[0] == "&"
            ) or (cached_isinstance(node, Arguments)):
                name, value = split_from_equals(token.value)
                if value is not None:
                    length = len(name)

                    yield SemTokenInfo.from_token(
                        Token(
                            ROBOT_NAMED_ARGUMENT if cached_isinstance(node, Variable) else SemanticTokenTypes.PARAMETER,
                            name,
                            token.lineno,
                            token.col_offset,
                        ),
                        (
                            RobotSemTokenTypes.NAMED_ARGUMENT
                            if cached_isinstance(node, Variable)
                            else SemanticTokenTypes.PARAMETER
                        ),
                    )
                    yield SemTokenInfo.from_token(
                        Token(
                            ROBOT_OPERATOR,
                            "=",
                            token.lineno,
                            token.col_offset + length,
                        ),
                        SemanticTokenTypes.OPERATOR,
                    )
                    token = Token(
                        token.type,
                        value,
                        token.lineno,
                        token.col_offset + length + 1,
                        token.error,
                    )
                elif cached_isinstance(node, Arguments) and name:
                    yield SemTokenInfo.from_token(
                        Token(
                            ROBOT_NAMED_ARGUMENT,
                            name,
                            token.lineno,
                            token.col_offset,
                        ),
                        RobotSemTokenTypes.NAMED_ARGUMENT,
                    )
                    token = Token(
                        token.type,
                        "",
                        token.lineno,
                        token.col_offset + len(name),
                        token.error,
                    )

            for sub_token in ModelHelper.tokenize_variables(
                token,
                ignore_errors=True,
                identifiers="$" if token.type == Token.KEYWORD_NAME else "$@&%",
            ):
                for e in self.generate_sem_sub_tokens(
                    namespace, builtin_library_doc, sub_token, node, yield_arguments=True
                ):
                    yield e

        else:
            for e in self.generate_sem_sub_tokens(namespace, builtin_library_doc, token, node, yield_arguments=True):
                yield e

    def generate_run_kw_tokens(
        self,
        namespace: Namespace,
        builtin_library_doc: Optional[LibraryDoc],
        kw_doc: Optional[KeywordDoc],
        kw_token: Token,
        arguments: Sequence[Token],
        node: ast.AST,
    ) -> Iterator[Tuple[Token, ast.AST]]:
        def skip_non_data_tokens() -> Iterator[Tuple[Token, ast.AST]]:
            nonlocal arguments
            while arguments and arguments[0] and arguments[0].type in Token.NON_DATA_TOKENS:
                yield (arguments[0], node)
                arguments = arguments[1:]

        if kw_doc is not None and kw_doc.is_any_run_keyword():
            yield kw_token, node

            for b in skip_non_data_tokens():
                yield b

            if kw_doc.is_run_keyword() and len(arguments) > 0:
                token = arguments[0]
                for b in self.generate_run_kw_tokens(
                    namespace,
                    builtin_library_doc,
                    namespace.find_keyword(unescape(token.value), raise_keyword_error=False),
                    Token(
                        ROBOT_KEYWORD_INNER,
                        token.value,
                        token.lineno,
                        token.col_offset,
                        token.error,
                    ),
                    arguments[1:],
                    node,
                ):
                    yield b
            elif kw_doc.is_run_keyword_with_condition() and len(arguments) > 0:
                cond_count = kw_doc.run_keyword_condition_count()
                for _ in range(cond_count):
                    yield (arguments[0], node)
                    arguments = arguments[1:]

                    for b in skip_non_data_tokens():
                        yield b

                if len(arguments) > 0:
                    token = arguments[0]
                    for b in self.generate_run_kw_tokens(
                        namespace,
                        builtin_library_doc,
                        namespace.find_keyword(unescape(token.value), raise_keyword_error=False),
                        Token(
                            ROBOT_KEYWORD_INNER,
                            token.value,
                            token.lineno,
                            token.col_offset,
                            token.error,
                        ),
                        arguments[1:],
                        node,
                    ):
                        yield b
            elif kw_doc.is_run_keywords() and len(arguments) > 0:
                has_separator = False
                while arguments:
                    for b in skip_non_data_tokens():
                        yield b

                    if not arguments:
                        break

                    token = arguments[0]
                    arguments = arguments[1:]

                    if token.value == "AND":
                        yield (
                            Token(
                                Token.ELSE,
                                token.value,
                                token.lineno,
                                token.col_offset,
                                token.error,
                            ),
                            node,
                        )
                        continue

                    separator_token = next((e for e in arguments if e.value == "AND"), None)
                    args: Sequence[Token] = []
                    if separator_token is not None:
                        args = arguments[: arguments.index(separator_token)]
                        arguments = arguments[arguments.index(separator_token) :]
                        has_separator = True
                    else:
                        if has_separator:
                            args = arguments
                            arguments = []

                    for e in self.generate_run_kw_tokens(
                        namespace,
                        builtin_library_doc,
                        namespace.find_keyword(unescape(token.value), raise_keyword_error=False),
                        Token(
                            ROBOT_KEYWORD_INNER,
                            token.value,
                            token.lineno,
                            token.col_offset,
                            token.error,
                        ),
                        args,
                        node,
                    ):
                        yield e
            elif kw_doc.is_run_keyword_if() and len(arguments) > 0:

                def generate_run_kw_if() -> Iterator[Tuple[Token, ast.AST]]:
                    nonlocal arguments

                    yield (arguments[0], node)
                    arguments = arguments[1:]

                    while arguments:
                        for b in skip_non_data_tokens():
                            yield b

                        if not arguments:
                            break

                        token = arguments[0]
                        arguments = arguments[1:]

                        if token.value in ["ELSE", "ELSE IF"]:
                            yield (
                                Token(
                                    Token.ELSE,
                                    token.value,
                                    token.lineno,
                                    token.col_offset,
                                    token.error,
                                ),
                                node,
                            )

                            if token.value == "ELSE IF":
                                for b in skip_non_data_tokens():
                                    yield b

                                if not arguments:
                                    break

                                yield arguments[0], node
                                arguments = arguments[1:]
                            continue

                        inner_kw_doc = namespace.find_keyword(unescape(token.value), raise_keyword_error=False)

                        if inner_kw_doc is not None and inner_kw_doc.is_run_keyword_if():
                            yield (
                                Token(
                                    ROBOT_KEYWORD_INNER,
                                    token.value,
                                    token.lineno,
                                    token.col_offset,
                                    token.error,
                                ),
                                node,
                            )

                            arguments = arguments[1:]

                            for b in skip_non_data_tokens():
                                yield b

                            for e in generate_run_kw_if():
                                yield e

                            continue

                        separator_token = next(
                            (e for e in arguments if e.value in ["ELSE", "ELSE IF"]),
                            None,
                        )
                        args: Sequence[Token] = []

                        if separator_token is not None:
                            args = arguments[: arguments.index(separator_token)]
                            arguments = arguments[arguments.index(separator_token) :]
                        else:
                            args = arguments
                            arguments = []

                        for e in self.generate_run_kw_tokens(
                            namespace,
                            builtin_library_doc,
                            inner_kw_doc,
                            Token(
                                ROBOT_KEYWORD_INNER,
                                token.value,
                                token.lineno,
                                token.col_offset,
                                token.error,
                            ),
                            args,
                            node,
                        ):
                            yield e

                for e in generate_run_kw_if():
                    yield e
        else:
            for a in self.generate_keyword_tokens(namespace, kw_token, arguments, node, kw_doc):
                yield a

    def generate_keyword_tokens(
        self,
        namespace: Namespace,
        kw_token: Token,
        arguments: Sequence[Token],
        node: ast.AST,
        kw_doc: Optional[KeywordDoc] = None,
    ) -> Iterator[Tuple[Token, ast.AST]]:
        yield kw_token, node

        for token in arguments:
            if token.type == Token.ARGUMENT:
                name, value = split_from_equals(token.value)
                if value is not None:
                    if kw_doc is None:
                        kw_doc = namespace.find_keyword(kw_token.value)

                    if kw_doc and any(
                        v for v in kw_doc.arguments if v.kind == KeywordArgumentKind.VAR_NAMED or v.name == name
                    ):
                        length = len(name)
                        yield (
                            Token(
                                ROBOT_NAMED_ARGUMENT,
                                name,
                                token.lineno,
                                token.col_offset,
                            ),
                            node,
                        )

                        yield (
                            Token(
                                ROBOT_OPERATOR,
                                "=",
                                token.lineno,
                                token.col_offset + length,
                            ),
                            node,
                        )
                        yield (
                            Token(
                                token.type,
                                value,
                                token.lineno,
                                token.col_offset + length + 1,
                                token.error,
                            ),
                            node,
                        )

                        continue

            yield token, node

    def _collect_internal(
        self,
        document: TextDocument,
        model: ast.AST,
        range: Optional[Range],
        namespace: Namespace,
        builtin_library_doc: Optional[LibraryDoc],
    ) -> Union[SemanticTokens, SemanticTokensPartialResult, None]:
        data = []
        last_line = 0
        last_col = 0

        def get_tokens() -> Iterator[Tuple[Token, ast.AST]]:
            current_section: Optional[Section] = None
            in_invalid_section = False

            for node in iter_nodes(model):
                if cached_isinstance(node, Section):
                    current_section = node
                    if get_robot_version() >= (7, 0):
                        in_invalid_section = cached_isinstance(current_section, InvalidSection)

                check_current_task_canceled()

                if cached_isinstance(node, Statement):
                    if cached_isinstance(node, LibraryImport) and node.name:
                        lib_doc = namespace.get_imported_library_libdoc(node.name, node.args, node.alias)
                        kw_doc = lib_doc.inits.keywords[0] if lib_doc and lib_doc.inits else None
                        if lib_doc is not None:
                            for token in node.tokens:
                                if token.type == Token.ARGUMENT:
                                    name, value = split_from_equals(token.value)
                                    if (
                                        value is not None
                                        and kw_doc is not None
                                        and kw_doc.arguments
                                        and any(
                                            v
                                            for v in kw_doc.arguments
                                            if v.kind == KeywordArgumentKind.VAR_NAMED or v.name == name
                                        )
                                    ):
                                        length = len(name)
                                        yield (
                                            Token(
                                                ROBOT_NAMED_ARGUMENT,
                                                name,
                                                token.lineno,
                                                token.col_offset,
                                            ),
                                            node,
                                        )

                                        yield (
                                            Token(
                                                ROBOT_OPERATOR,
                                                "=",
                                                token.lineno,
                                                token.col_offset + length,
                                            ),
                                            node,
                                        )
                                        yield (
                                            Token(
                                                token.type,
                                                value,
                                                token.lineno,
                                                token.col_offset + length + 1,
                                                token.error,
                                            ),
                                            node,
                                        )

                                        continue

                                yield token, node
                            continue
                    if cached_isinstance(node, VariablesImport) and node.name:
                        lib_doc = namespace.get_variables_import_libdoc(node.name, node.args)
                        kw_doc = lib_doc.inits.keywords[0] if lib_doc and lib_doc.inits else None
                        if lib_doc is not None:
                            for token in node.tokens:
                                if token.type == Token.ARGUMENT:
                                    name, value = split_from_equals(token.value)
                                    if (
                                        value is not None
                                        and kw_doc is not None
                                        and kw_doc.arguments
                                        and any(
                                            v
                                            for v in kw_doc.arguments
                                            if v.kind == KeywordArgumentKind.VAR_NAMED or v.name == name
                                        )
                                    ):
                                        length = len(name)
                                        yield (
                                            Token(
                                                ROBOT_NAMED_ARGUMENT,
                                                name,
                                                token.lineno,
                                                token.col_offset,
                                            ),
                                            node,
                                        )

                                        yield (
                                            Token(
                                                ROBOT_OPERATOR,
                                                "=",
                                                token.lineno,
                                                token.col_offset + length,
                                            ),
                                            node,
                                        )
                                        yield (
                                            Token(
                                                token.type,
                                                value,
                                                token.lineno,
                                                token.col_offset + length + 1,
                                                token.error,
                                            ),
                                            node,
                                        )

                                        continue

                                yield token, node
                            continue
                    if cached_isinstance(node, KeywordCall, Fixture):
                        kw_token = cast(
                            Token,
                            (
                                node.get_token(Token.KEYWORD)
                                if cached_isinstance(node, KeywordCall)
                                else node.get_token(Token.NAME)
                            ),
                        )

                        for node_token in node.tokens:
                            if node_token == kw_token:
                                break
                            yield node_token, node

                        if kw_token is not None:
                            kw: Optional[str] = None

                            for _, n in iter_over_keyword_names_and_owners(
                                ModelHelper.strip_bdd_prefix(namespace, kw_token).value
                            ):
                                if n is not None:
                                    matcher = KeywordMatcher(n)
                                    if matcher in ALL_RUN_KEYWORDS_MATCHERS:
                                        kw = n
                            if kw:
                                kw_doc = namespace.find_keyword(kw_token.value)
                                if kw_doc is not None and kw_doc.is_any_run_keyword():
                                    for kw_res in self.generate_run_kw_tokens(
                                        namespace,
                                        builtin_library_doc,
                                        kw_doc,
                                        kw_token,
                                        node.tokens[node.tokens.index(kw_token) + 1 :],
                                        node,
                                    ):
                                        yield kw_res
                                    continue
                            else:
                                for kw_res in self.generate_keyword_tokens(
                                    namespace,
                                    kw_token,
                                    node.tokens[node.tokens.index(kw_token) + 1 :],
                                    node,
                                ):
                                    yield kw_res

                                continue
                    if cached_isinstance(node, Documentation):
                        for token in node.tokens:
                            if token.type == Token.ARGUMENT:
                                continue
                            yield token, node
                        continue

                    for token in node.tokens:
                        if not in_invalid_section and token.type == Token.COMMENT:
                            continue
                        yield token, node

        lines = document.get_lines()

        for robot_token, robot_node in takewhile(
            lambda t: range is None or token_in_range(t[0], range),
            dropwhile(
                lambda t: range is not None and not token_in_range(t[0], range),
                [(t, n) for t, n in get_tokens() if t.type not in [Token.SEPARATOR, Token.EOL, Token.EOS]],
            ),
        ):
            for token in self.generate_sem_tokens(robot_token, robot_node, namespace, builtin_library_doc):
                if token.length == 0:
                    continue

                token_range = range_to_utf16(
                    lines,
                    Range(
                        start=Position(line=token.lineno - 1, character=token.col_offset),
                        end=Position(
                            line=token.lineno - 1,
                            character=token.col_offset + token.length,
                        ),
                    ),
                )

                token_col_offset = token_range.start.character
                token_length = token_range.end.character - token_range.start.character

                current_line = token.lineno - 1

                data.append(current_line - last_line)

                if last_line != current_line:
                    last_col = token_col_offset
                    data.append(last_col)
                else:
                    delta = token_col_offset - last_col
                    data.append(delta)
                    last_col += delta

                last_line = current_line

                data.append(token_length)

                data.append(self.parent.semantic_tokens.token_types.index(token.sem_token_type))

                data.append(
                    reduce(
                        operator.or_,
                        [2 ** self.parent.semantic_tokens.token_modifiers.index(e) for e in token.sem_modifiers],
                    )
                    if token.sem_modifiers
                    else 0
                )

        return SemanticTokens(data=data)

    def _collect(
        self, document: TextDocument, range: Optional[Range]
    ) -> Union[SemanticTokens, SemanticTokensPartialResult, None]:
        model = self.parent.documents_cache.get_model(document, False)
        namespace = self.parent.documents_cache.get_namespace(document)

        builtin_library_doc = next(
            (
                library.library_doc
                for library in namespace.get_libraries().values()
                if library.name == BUILTIN_LIBRARY_NAME
                and library.import_name == BUILTIN_LIBRARY_NAME
                and library.import_range == Range.zero()
            ),
            None,
        )

        return self._collect_internal(document, model, range, namespace, builtin_library_doc)

    @language_id("robotframework")
    def collect_full(
        self, sender: Any, document: TextDocument, **kwargs: Any
    ) -> Union[SemanticTokens, SemanticTokensPartialResult, None]:
        return self._collect(document, None)

    @language_id("robotframework")
    def collect_range(
        self, sender: Any, document: TextDocument, range: Range, **kwargs: Any
    ) -> Union[SemanticTokens, SemanticTokensPartialResult, None]:
        return self._collect(document, range)

    @language_id("robotframework")
    def collect_full_delta(
        self,
        sender: Any,
        document: TextDocument,
        previous_result_id: str,
        **kwargs: Any,
    ) -> Union[
        SemanticTokens,
        SemanticTokensDelta,
        SemanticTokensDeltaPartialResult,
        None,
    ]:
        return None
