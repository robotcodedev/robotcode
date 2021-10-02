from __future__ import annotations

import asyncio
import itertools
import operator
import re
from enum import Enum
from functools import reduce
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    FrozenSet,
    Generator,
    Iterable,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Union,
)

from ....utils.async_event import CancelationToken
from ....utils.logging import LoggingDescriptor
from ...common.language import language_id
from ...common.text_document import TextDocument
from ...common.types import (
    Range,
    SemanticTokenModifiers,
    SemanticTokens,
    SemanticTokensDelta,
    SemanticTokensDeltaPartialResult,
    SemanticTokensPartialResult,
    SemanticTokenTypes,
)
from ..utils.ast import Token, token_in_range

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .protocol_part import RobotLanguageServerProtocolPart


class RobotSemTokenTypes(Enum):
    SECTION = "section"
    SETTING_IMPORT = "settingImport"
    SETTING = "setting"
    HEADER = "header"
    HEADER_SETTING = "headerSetting"
    HEADER_VARIABLE = "headerVariable"
    HEADER_TESTCASE = "headerTestcase"
    HEADER_COMMENT = "headerComment"
    HEADER_KEYWORD = "headerKeyword"
    TESTCASE_NAME = "testcaseName"
    KEYWORD_NAME = "keywordName"
    CONTROL_FLOW = "controlFlow"
    ARGUMENT = "argument"
    VARIABLE = "variable"
    KEYWORD = "keywordCall"
    NAME = "nameCall"
    CONTINUATION = "continuation"
    SEPARATOR = "separator"
    TERMINATOR = "terminator"
    FOR_SEPARATOR = "forSeparator"
    VARIABLE_BEGIN = "variableBegin"
    VARIABLE_END = "variableEnd"
    ESCAPE = "escape"
    NAMESPACE = "namespace"


class SemTokenInfo(NamedTuple):
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


class RobotSemanticTokenProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)
        parent.semantic_tokens.token_types += [e for e in RobotSemTokenTypes]

        parent.semantic_tokens.collect_full.add(self.collect_full)
        parent.semantic_tokens.collect_range.add(self.collect_range)
        # parent.semantic_tokens.collect_full_delta.add(self.collect_full_delta)

    @classmethod
    def generate_mapping(cls) -> Dict[str, Tuple[Enum, Optional[Set[Enum]]]]:
        from robot.parsing.lexer.tokens import Token as RobotToken

        definition: Dict[FrozenSet[str], Tuple[Enum, Optional[Set[Enum]]]] = {
            frozenset(RobotToken.HEADER_TOKENS): (RobotSemTokenTypes.HEADER, None),
            frozenset({RobotToken.SETTING_HEADER}): (RobotSemTokenTypes.HEADER_SETTING, None),
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
            frozenset({RobotToken.NAME}): (RobotSemTokenTypes.NAME, None),
            frozenset({RobotToken.CONTINUATION}): (RobotSemTokenTypes.CONTINUATION, None),
            frozenset({RobotToken.SEPARATOR}): (RobotSemTokenTypes.SEPARATOR, None),
            frozenset({RobotToken.EOL, RobotToken.EOS}): (RobotSemTokenTypes.TERMINATOR, None),
        }

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
        r"(?P<t>[^\\]+)|(?P<x>\\([^xuU]|x[0-f]{2}|u[0-f]{4}|U[0-f]{8}){0,1})", re.MULTILINE | re.DOTALL
    )

    @classmethod
    def generate_sem_sub_tokens(
        cls, token: Token, col_offset: Optional[int] = None, length: Optional[int] = None
    ) -> Generator[SemTokenInfo, None, None]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.variables.search import is_variable

        sem_info = cls.mapping().get(token.type, None) if token.type is not None else None

        if sem_info is not None:
            if token.type == RobotToken.VARIABLE:
                if col_offset is None:
                    col_offset = token.col_offset
                if length is None:
                    length = token.end_col_offset - token.col_offset

                if is_variable(token.value):
                    yield SemTokenInfo(token.lineno, col_offset, 2, RobotSemTokenTypes.VARIABLE_BEGIN)
                    yield SemTokenInfo.from_token(token, sem_info[0], sem_info[1], col_offset + 2, length - 3)
                    yield SemTokenInfo(token.lineno, col_offset + length - 1, 1, RobotSemTokenTypes.VARIABLE_END)
                else:
                    yield SemTokenInfo.from_token(token, sem_info[0], sem_info[1])

            elif token.type == RobotToken.ARGUMENT and "\\" in token.value:
                if col_offset is None:
                    col_offset = token.col_offset
                if length is None:
                    length = token.end_col_offset - token.col_offset

                for g in cls.ESCAPE_REGEX.finditer(token.value):
                    yield SemTokenInfo.from_token(
                        token,
                        sem_info[0] if g.group("x") is None or g.end() - g.start() == 1 else RobotSemTokenTypes.ESCAPE,
                        sem_info[1],
                        col_offset + g.start(),
                        g.end() - g.start(),
                    )
            elif token.type == RobotToken.KEYWORD:
                if col_offset is None:
                    col_offset = token.col_offset
                if length is None:
                    length = token.end_col_offset - token.col_offset

                index = token.value.find(".")
                old_index = 0
                while index >= 0:
                    if index > 0:
                        yield SemTokenInfo(
                            token.lineno,
                            col_offset + old_index,
                            index - old_index,
                            RobotSemTokenTypes.NAMESPACE,
                            {SemanticTokenModifiers.DEFAULT_LIBRARY}
                            if token.value[:index].casefold() == "BuiltIn".casefold()
                            else None,
                        )
                    yield SemTokenInfo(token.lineno, col_offset + index, 1, RobotSemTokenTypes.SEPARATOR)

                    new_index = token.value.find(".", index + 1)
                    if new_index >= 0:
                        old_index = index
                        index = new_index
                    else:
                        break

                yield SemTokenInfo.from_token(
                    token, sem_info[0], sem_info[1], col_offset + index + 1, length - index - 1
                )
            else:
                yield SemTokenInfo.from_token(token, sem_info[0], sem_info[1], col_offset, length)

    @classmethod
    def generate_sem_tokens(cls, token: Token) -> Generator[SemTokenInfo, None, None]:
        from robot.parsing.lexer.tokens import Token as RobotToken

        if token.type in RobotToken.ALLOW_VARIABLES:
            last_sub_token = token
            try:
                for sub_token in token.tokenize_variables():
                    last_sub_token = sub_token
                    for e in cls.generate_sem_sub_tokens(sub_token):
                        yield e
            except BaseException:
                pass
            if last_sub_token == token:
                for e in cls.generate_sem_sub_tokens(last_sub_token):
                    yield e
            elif last_sub_token is not None and last_sub_token.end_col_offset < token.end_col_offset:
                for e in cls.generate_sem_sub_tokens(
                    token,
                    last_sub_token.end_col_offset,
                    token.end_col_offset - last_sub_token.end_col_offset - last_sub_token.col_offset,
                ):
                    yield e

        else:
            for e in cls.generate_sem_sub_tokens(token):
                yield e

    def collect(
        self, tokens: Iterable[Token], range: Optional[Range], cancel_token: CancelationToken
    ) -> Union[SemanticTokens, SemanticTokensPartialResult, None]:

        data = []
        last_line = 0
        last_col = 0

        for robot_token in itertools.takewhile(
            lambda t: not cancel_token.throw_if_canceled() and (range is None or token_in_range(t, range)),
            itertools.dropwhile(
                lambda t: not cancel_token.throw_if_canceled() and range is not None and not token_in_range(t, range),
                tokens,
            ),
        ):
            cancel_token.throw_if_canceled()

            for token in self.generate_sem_tokens(robot_token):
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

    async def collect_threading(
        self, document: TextDocument, range: Optional[Range]
    ) -> Union[SemanticTokens, SemanticTokensPartialResult, None]:
        try:
            cancel_token = CancelationToken()
            return await asyncio.get_event_loop().run_in_executor(
                None, self.collect, await self.parent.documents_cache.get_tokens(document), range, cancel_token
            )
        except BaseException:
            cancel_token.cancel()
            raise

    @language_id("robotframework")
    async def collect_full(
        self, sender: Any, document: TextDocument, **kwargs: Any
    ) -> Union[SemanticTokens, SemanticTokensPartialResult, None]:
        return await document.get_cache(self.collect_threading, None)

    @language_id("robotframework")
    async def collect_range(
        self, sender: Any, document: TextDocument, range: Range, **kwargs: Any
    ) -> Union[SemanticTokens, SemanticTokensPartialResult, None]:
        return await self.collect_threading(document, range)

    @language_id("robotframework")
    async def collect_full_delta(
        self, sender: Any, document: TextDocument, previous_result_id: str, **kwargs: Any
    ) -> Union[SemanticTokens, SemanticTokensDelta, SemanticTokensDeltaPartialResult, None]:
        return None
