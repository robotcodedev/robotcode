from __future__ import annotations

import operator
from enum import Enum
from functools import reduce
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Dict,
    FrozenSet,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Union,
)

from ....utils.logging import LoggingDescriptor
from ...common.language import language_id
from ...common.text_document import TextDocument
from ...common.types import (
    SemanticTokenModifiers,
    SemanticTokens,
    SemanticTokensPartialResult,
    SemanticTokenTypes,
)
from ..utils.ast import Token

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


class SemTokenInfo(NamedTuple):
    lineno: int
    col_offset: int
    length: int
    sem_token_type: Enum
    sem_modifiers: Optional[Set[Enum]] = None

    @classmethod
    def from_token(cls, token: Token, sem_token_type: Enum, sem_modifiers: Optional[Set[Enum]] = None) -> SemTokenInfo:
        return cls(
            token.lineno, token.col_offset, token.end_col_offset - token.col_offset, sem_token_type, sem_modifiers
        )


class RobotSemanticTokenProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)
        parent.semantic_tokens.token_types += [e for e in RobotSemTokenTypes]
        parent.semantic_tokens.collect_full.add(self.collect_full)

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

    @classmethod
    async def generate_sem_tokens(cls, token: Token) -> AsyncGenerator[SemTokenInfo, None]:
        from robot.parsing.lexer.tokens import Token as RobotToken

        if token.type in RobotToken.ALLOW_VARIABLES:
            last_sub_token = token
            try:
                for sub_token in token.tokenize_variables():
                    last_sub_token = sub_token
                    if sub_token.type is not None:
                        sem_info = cls.mapping().get(sub_token.type, None)
                        if sem_info is not None:
                            yield SemTokenInfo.from_token(sub_token, sem_info[0], sem_info[1])
            except BaseException:
                pass
            if last_sub_token == token and token.type is not None:
                sem_info = cls.mapping().get(token.type, None)
                if sem_info is not None:
                    yield SemTokenInfo.from_token(token, sem_info[0], sem_info[1])
            elif last_sub_token is not None and last_sub_token.end_col_offset < token.end_col_offset:
                if token.type is not None:
                    sem_info = cls.mapping().get(token.type, None)
                    if sem_info is not None:
                        yield SemTokenInfo(
                            token.lineno,
                            last_sub_token.end_col_offset,
                            token.end_col_offset - last_sub_token.end_col_offset - last_sub_token.col_offset,
                            sem_info[0],
                            sem_info[1],
                        )

        elif token.type is not None:
            sem_info = cls.mapping().get(token.type, None)
            if sem_info is not None:
                yield SemTokenInfo.from_token(token, sem_info[0], sem_info[1])

    @language_id("robotframework")
    async def collect_full(
        self, sender: Any, document: TextDocument, **kwargs: Any
    ) -> Union[SemanticTokens, SemanticTokensPartialResult, None]:

        data = []
        last_line = 0
        last_col = 0

        tokens = await self.parent.documents_cache.get_tokens(document)
        for robot_token in tokens:
            async for token in self.generate_sem_tokens(robot_token):
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
