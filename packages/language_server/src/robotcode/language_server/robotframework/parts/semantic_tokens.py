import ast
import operator
import re
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache, reduce
from itertools import dropwhile, takewhile
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    FrozenSet,
    Iterator,
    List,
    Optional,
    Pattern,
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
    TemplateArguments,
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
from robotcode.robot.utils.variables import split_from_equals

from .protocol_part import RobotLanguageServerProtocolPart

# Cache robot version at module level for conditional imports
_ROBOT_VERSION = get_robot_version()

if _ROBOT_VERSION >= (5, 0):
    from robot.parsing.model.statements import ExceptHeader, WhileHeader

if _ROBOT_VERSION >= (7, 0):
    from robot.parsing.model.blocks import InvalidSection

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

_AND_SEPARATOR = frozenset({"AND"})
_ELSE_SEPARATORS = frozenset({"ELSE", "ELSE IF"})


@lru_cache(maxsize=512)
def _cached_unescape(token_value: str) -> str:
    """Cached version of unescape function for performance.

    Args:
        token_value: Token value to unescape

    Returns:
        Unescaped string
    """
    return str(unescape(token_value))


ROBOT_KEYWORD_INNER = "KEYWORD_INNER"
ROBOT_NAMED_ARGUMENT = "NAMED_ARGUMENT"
ROBOT_OPERATOR = "OPERATOR"


class RobotSemTokenTypes(Enum):
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
    EXPRESSION_BEGIN = "expressionBegin"
    EXPRESSION_END = "expressionEnd"
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


# Type aliases for better type hints - extend base types to be compatible with LSP framework
AnyTokenType = Union[RobotSemTokenTypes, SemanticTokenTypes, Enum]
AnyTokenModifier = Union[RobotSemTokenModifiers, SemanticTokenModifiers, Enum]


@dataclass
class SemTokenInfo:
    lineno: int
    col_offset: int
    length: int
    sem_token_type: AnyTokenType
    sem_modifiers: Optional[Set[AnyTokenModifier]] = None

    @classmethod
    def from_token(
        cls,
        token: Token,
        sem_token_type: AnyTokenType,
        sem_modifiers: Optional[Set[AnyTokenModifier]] = None,
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


class SemanticTokenMapper:
    """Handles token type mapping and classification for Robot Framework semantic tokens.

    This class is responsible for:
    - Generating and caching token type mappings
    - Providing regex patterns for token analysis
    - Managing builtin keyword matching
    """

    _mapping: ClassVar[Optional[Dict[str, Tuple[AnyTokenType, Optional[Set[AnyTokenModifier]]]]]] = None

    ESCAPE_REGEX: ClassVar[Pattern[str]] = re.compile(
        r"(?P<t>[^\\]+)|(?P<x>\\(?:[\\nrt]|x[0-9A-Fa-f]{2}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}))|(?P<e>\\(?:[^\\nrt\\xuU]|[\\xuU][^0-9a-fA-F]))",
        re.MULTILINE | re.DOTALL,
    )
    BDD_TOKEN_REGEX: ClassVar[Pattern[str]] = re.compile(r"^(Given|When|Then|And|But)\s", flags=re.IGNORECASE)
    BUILTIN_MATCHER: ClassVar[KeywordMatcher] = KeywordMatcher("BuiltIn", is_namespace=True)

    @classmethod
    def generate_mapping(cls) -> Dict[str, Tuple[AnyTokenType, Optional[Set[AnyTokenModifier]]]]:
        """Generate semantic token mappings for different Robot Framework versions.

        Returns:
            Dict mapping token types to semantic token information
        """
        definition: Dict[FrozenSet[str], Tuple[AnyTokenType, Optional[Set[AnyTokenModifier]]]] = {
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

        if _ROBOT_VERSION >= (5, 0):
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

        if _ROBOT_VERSION >= (6, 0):
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
        if _ROBOT_VERSION >= (7, 0):
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

        if _ROBOT_VERSION >= (7, 2):
            definition.update(
                {
                    frozenset({Token.GROUP}): (RobotSemTokenTypes.CONTROL_FLOW, None),
                }
            )

        result: Dict[str, Tuple[AnyTokenType, Optional[Set[AnyTokenModifier]]]] = {}
        for k, v in definition.items():
            for e in k:
                result[e] = v

        return result

    @classmethod
    def mapping(cls) -> Dict[str, Tuple[AnyTokenType, Optional[Set[AnyTokenModifier]]]]:
        """Get cached token type mappings.

        Returns:
            Dict mapping token types to semantic token information
        """
        if cls._mapping is None:
            cls._mapping = cls.generate_mapping()
        return cls._mapping

    def get_semantic_info(
        self, token_type: Optional[str]
    ) -> Optional[Tuple[AnyTokenType, Optional[Set[AnyTokenModifier]]]]:
        """Get semantic token information for a given token type.

        Args:
            token_type: The Robot Framework token type

        Returns:
            Tuple of semantic token type and modifiers, or None if not found
        """
        if token_type is None:
            return None
        return self.mapping().get(token_type, None)


@dataclass
class NamedArgumentInfo:
    """Information about a named argument token."""

    name: str
    value: str
    name_length: int
    total_length: int
    is_valid: bool


class ArgumentProcessor:
    """Efficient argument processing without list slicing for performance.

    This processor eliminates memory allocations from list slicing operations
    by using index-based navigation through argument sequences.
    """

    def __init__(self, arguments: Sequence[Token]) -> None:
        """Initialize with argument sequence.

        Args:
            arguments: Sequence of tokens to process
        """
        self.arguments = arguments
        self.index = 0

    def has_next(self) -> bool:
        """Check if more arguments are available.

        Returns:
            True if more arguments exist at current position
        """
        return self.index < len(self.arguments)

    def peek(self) -> Optional[Token]:
        """Peek at next argument without consuming it.

        Returns:
            Next token or None if no more arguments
        """
        return self.arguments[self.index] if self.has_next() else None

    def consume(self) -> Optional[Token]:
        """Consume and return next argument.

        Returns:
            Next token or None if no more arguments
        """
        if self.has_next():
            token = self.arguments[self.index]
            self.index += 1
            return token
        return None

    def skip_non_data_tokens(self) -> List[Token]:
        """Skip non-data tokens and return them.

        Returns:
            List of skipped non-data tokens
        """
        skipped = []
        while self.has_next():
            next_token = self.peek()
            if next_token and next_token.type in Token.NON_DATA_TOKENS:
                consumed = self.consume()
                if consumed:
                    skipped.append(consumed)
            else:
                break
        return skipped

    def remaining_slice(self) -> Sequence[Token]:
        """Get remaining arguments as slice (fallback for compatibility).

        Returns:
            Remaining arguments from current position
        """
        return self.arguments[self.index :]

    def find_separator_index(self, separator_values: FrozenSet[str]) -> Optional[int]:
        """Find index of next separator token.

        Args:
            separator_values: Frozen set of separator values to search for

        Returns:
            Relative index of separator from current position, or None
        """
        if not separator_values:
            return None

        if self.index >= len(self.arguments):
            return None

        try:
            return next(
                offset for offset, arg in enumerate(self.arguments[self.index :]) if arg.value in separator_values
            )
        except StopIteration:
            return None

    def iter_until_separator(self, separator_values: List[str]) -> Iterator[Token]:
        """Iterate tokens until separator is found without creating a list.

        Args:
            separator_values: List of separator values to stop at

        Yields:
            Tokens until separator is found (excluding separator)
        """
        while self.has_next():
            next_token = self.peek()
            if next_token and next_token.value in separator_values:
                break
            token = self.consume()
            if token:
                yield token

    def iter_all_remaining(self) -> Iterator[Token]:
        """Iterate all remaining tokens without creating a list.

        Yields:
            All remaining tokens from current position
        """
        while self.has_next():
            token = self.consume()
            if token:
                yield token


class NamedArgumentProcessor:
    """Handles named argument processing consistently across different contexts."""

    def __init__(self, token_mapper: SemanticTokenMapper) -> None:
        """Initialize the processor with a token mapper.

        Args:
            token_mapper: The semantic token mapper for type resolution
        """
        self.token_mapper = token_mapper

    def parse_named_argument(
        self, token_value: str, kw_doc: Optional[KeywordDoc] = None
    ) -> Optional[NamedArgumentInfo]:
        """Parse named argument token into components.

        Args:
            token_value: The token value to parse
            kw_doc: Optional keyword documentation for validation

        Returns:
            NamedArgumentInfo if valid named argument, None otherwise
        """
        name, value = split_from_equals(token_value)
        if value is None:
            return None

        is_valid = self._validate_named_argument(name, kw_doc)

        return NamedArgumentInfo(
            name=name, value=value, name_length=len(name), total_length=len(token_value), is_valid=is_valid
        )

    def _validate_named_argument(self, name: str, kw_doc: Optional[KeywordDoc]) -> bool:
        """Validate if named argument is valid for keyword.

        Args:
            name: The argument name to validate
            kw_doc: Optional keyword documentation for validation

        Returns:
            True if named argument is valid
        """
        if not kw_doc or not kw_doc.arguments:
            return False

        return any(arg.kind == KeywordArgumentKind.VAR_NAMED or arg.name == name for arg in kw_doc.arguments)

    def generate_named_argument_tokens(
        self, token: Token, arg_info: NamedArgumentInfo, node: ast.AST, token_type_override: Optional[str] = None
    ) -> Iterator[Tuple[Token, ast.AST]]:
        """Generate tokens for named argument.

        Args:
            token: Original token
            arg_info: Parsed argument information
            node: AST node
            token_type_override: Optional token type override for name token

        Yields:
            Token and node pairs for semantic highlighting
        """
        if not arg_info.is_valid:
            yield token, node
            return

        yield (
            Token(
                token_type_override or ROBOT_NAMED_ARGUMENT,
                arg_info.name,
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
                token.col_offset + arg_info.name_length,
            ),
            node,
        )

        yield (
            Token(
                token.type,
                arg_info.value,
                token.lineno,
                token.col_offset + arg_info.name_length + 1,
                token.error,
            ),
            node,
        )

    def process_token_for_named_argument(
        self,
        token: Token,
        node: ast.AST,
        kw_doc: Optional[KeywordDoc] = None,
        token_type_override: Optional[str] = None,
    ) -> Iterator[Tuple[Token, ast.AST]]:
        """Process a token that might be a named argument.

        Args:
            token: The token to process
            node: The AST node
            kw_doc: Optional keyword documentation
            token_type_override: Optional token type override for name token

        Yields:
            Token and node pairs for semantic highlighting
        """
        arg_info = self.parse_named_argument(token.value, kw_doc)
        if arg_info and arg_info.is_valid:
            yield from self.generate_named_argument_tokens(token, arg_info, node, token_type_override)
        else:
            yield token, node


class KeywordTokenAnalyzer:
    """Specialized analysis for keyword tokens and run keywords.

    This class handles the complex logic for analyzing keyword calls,
    including run keyword variants and nested keyword structures.
    """

    def __init__(self, token_mapper: SemanticTokenMapper) -> None:
        """Initialize the analyzer with a token mapper.

        Args:
            token_mapper: The semantic token mapper for type resolution
        """
        self.token_mapper = token_mapper
        self.named_arg_processor = NamedArgumentProcessor(token_mapper)

    def _skip_non_data_tokens(self, arg_processor: ArgumentProcessor, node: ast.AST) -> List[Tuple[Token, ast.AST]]:
        """Skip non-data tokens using ArgumentProcessor.

        Args:
            arg_processor: The argument processor
            node: AST node

        Returns:
            List of skipped token-node pairs
        """
        skipped_tokens = arg_processor.skip_non_data_tokens()
        return [(token, node) for token in skipped_tokens]

    def _generate_run_keyword_tokens(
        self,
        namespace: Namespace,
        builtin_library_doc: Optional[LibraryDoc],
        arguments: Sequence[Token],
        node: ast.AST,
    ) -> Iterator[Tuple[Token, ast.AST]]:
        """Generate tokens for simple Run Keyword calls.

        Args:
            namespace: The namespace context
            builtin_library_doc: BuiltIn library documentation
            arguments: Arguments to the keyword
            node: The AST node

        Yields:
            Token and node pairs for semantic highlighting
        """
        arg_processor = ArgumentProcessor(arguments)

        skipped_tokens = self._skip_non_data_tokens(arg_processor, node)
        for skipped_token in skipped_tokens:
            yield skipped_token

        if arg_processor.has_next():
            token = arg_processor.consume()
            if token:
                yield from self.generate_run_kw_tokens(
                    namespace,
                    builtin_library_doc,
                    namespace.find_keyword(_cached_unescape(token.value), raise_keyword_error=False),
                    Token(
                        ROBOT_KEYWORD_INNER,
                        token.value,
                        token.lineno,
                        token.col_offset,
                        token.error,
                    ),
                    arg_processor.remaining_slice(),
                    node,
                )

    def _generate_run_keyword_with_condition_tokens(
        self,
        namespace: Namespace,
        builtin_library_doc: Optional[LibraryDoc],
        kw_doc: KeywordDoc,
        arguments: Sequence[Token],
        node: ast.AST,
    ) -> Iterator[Tuple[Token, ast.AST]]:
        """Generate tokens for Run Keyword with condition calls.

        Args:
            namespace: The namespace context
            builtin_library_doc: BuiltIn library documentation
            kw_doc: Keyword documentation
            arguments: Arguments to the keyword
            node: The AST node

        Yields:
            Token and node pairs for semantic highlighting
        """
        arg_processor = ArgumentProcessor(arguments)
        cond_count = kw_doc.run_keyword_condition_count()

        for _ in range(cond_count):
            if arg_processor.has_next():
                consumed_token = arg_processor.consume()
                if consumed_token:
                    yield (consumed_token, node)

                skipped_tokens = self._skip_non_data_tokens(arg_processor, node)
                for skipped_token in skipped_tokens:
                    yield skipped_token

        if arg_processor.has_next():
            token = arg_processor.consume()
            if token:
                yield from self.generate_run_kw_tokens(
                    namespace,
                    builtin_library_doc,
                    namespace.find_keyword(_cached_unescape(token.value), raise_keyword_error=False),
                    Token(
                        ROBOT_KEYWORD_INNER,
                        token.value,
                        token.lineno,
                        token.col_offset,
                        token.error,
                    ),
                    arg_processor.remaining_slice(),
                    node,
                )

    def _generate_run_keywords_tokens(
        self,
        namespace: Namespace,
        builtin_library_doc: Optional[LibraryDoc],
        arguments: Sequence[Token],
        node: ast.AST,
    ) -> Iterator[Tuple[Token, ast.AST]]:
        """Generate tokens for Run Keywords calls (with AND separators).

        Args:
            namespace: The namespace context
            builtin_library_doc: BuiltIn library documentation
            arguments: Arguments to the keyword
            node: The AST node

        Yields:
            Token and node pairs for semantic highlighting
        """
        arg_processor = ArgumentProcessor(arguments)
        has_separator = False

        while arg_processor.has_next():
            skipped_tokens = self._skip_non_data_tokens(arg_processor, node)
            for skipped_token in skipped_tokens:
                yield skipped_token

            if not arg_processor.has_next():
                break

            token = arg_processor.consume()
            if not token:
                break

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

            and_index = arg_processor.find_separator_index(_AND_SEPARATOR)

            if and_index is not None:
                args = list(arg_processor.iter_until_separator(["AND"]))
                has_separator = True
            else:
                if has_separator:
                    args = list(arg_processor.iter_all_remaining())
                else:
                    args = []

            yield from self.generate_run_kw_tokens(
                namespace,
                builtin_library_doc,
                namespace.find_keyword(_cached_unescape(token.value), raise_keyword_error=False),
                Token(
                    ROBOT_KEYWORD_INNER,
                    token.value,
                    token.lineno,
                    token.col_offset,
                    token.error,
                ),
                args,
                node,
            )

    def _generate_run_keyword_if_tokens(
        self,
        namespace: Namespace,
        builtin_library_doc: Optional[LibraryDoc],
        arguments: Sequence[Token],
        node: ast.AST,
    ) -> Iterator[Tuple[Token, ast.AST]]:
        """Generate tokens for Run Keyword If calls.

        Args:
            namespace: The namespace context
            builtin_library_doc: BuiltIn library documentation
            arguments: Arguments to the keyword
            node: The AST node

        Yields:
            Token and node pairs for semantic highlighting
        """

        def generate_run_kw_if(arg_processor: ArgumentProcessor) -> Iterator[Tuple[Token, ast.AST]]:
            if arg_processor.has_next():
                consumed_token = arg_processor.consume()
                if consumed_token:
                    yield (consumed_token, node)

            while arg_processor.has_next():
                skipped_tokens = self._skip_non_data_tokens(arg_processor, node)
                for skipped_token in skipped_tokens:
                    yield skipped_token

                if not arg_processor.has_next():
                    break

                token = arg_processor.consume()
                if not token:
                    break

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
                        skipped_tokens = self._skip_non_data_tokens(arg_processor, node)
                        for skipped_token in skipped_tokens:
                            yield skipped_token

                        if arg_processor.has_next():
                            consumed_token = arg_processor.consume()
                            if consumed_token:
                                yield (consumed_token, node)
                    continue

                inner_kw_doc = namespace.find_keyword(_cached_unescape(token.value), raise_keyword_error=False)

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

                    skipped_tokens = self._skip_non_data_tokens(arg_processor, node)
                    for skipped_token in skipped_tokens:
                        yield skipped_token

                    yield from generate_run_kw_if(arg_processor)
                    continue

                separator_index = arg_processor.find_separator_index(_ELSE_SEPARATORS)
                args: Sequence[Token] = []

                if separator_index is not None:
                    args = list(arg_processor.iter_until_separator(["ELSE", "ELSE IF"]))
                else:
                    args = list(arg_processor.iter_all_remaining())

                yield from self.generate_run_kw_tokens(
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
                )

        arg_processor = ArgumentProcessor(arguments)
        yield from generate_run_kw_if(arg_processor)

    def generate_run_kw_tokens(
        self,
        namespace: Namespace,
        builtin_library_doc: Optional[LibraryDoc],
        kw_doc: Optional[KeywordDoc],
        kw_token: Token,
        arguments: Sequence[Token],
        node: ast.AST,
    ) -> Iterator[Tuple[Token, ast.AST]]:
        """Generate tokens for run keyword variants.

        Args:
            namespace: The namespace context for keyword resolution
            builtin_library_doc: BuiltIn library documentation
            kw_doc: Documentation for the keyword being analyzed
            kw_token: The keyword token
            arguments: Arguments to the keyword
            node: The AST node containing the keyword call

        Yields:
            Tuple[Token, ast.AST]: Token and node pairs for semantic highlighting
        """

        if kw_doc is not None and kw_doc.is_any_run_keyword():
            yield kw_token, node

            arg_processor = ArgumentProcessor(arguments)
            skipped_tokens = self._skip_non_data_tokens(arg_processor, node)
            for skipped_token in skipped_tokens:
                yield skipped_token

            remaining_arguments = arg_processor.remaining_slice()

            if kw_doc.is_run_keyword() and len(remaining_arguments) > 0:
                yield from self._generate_run_keyword_tokens(namespace, builtin_library_doc, remaining_arguments, node)
            elif kw_doc.is_run_keyword_with_condition() and len(remaining_arguments) > 0:
                yield from self._generate_run_keyword_with_condition_tokens(
                    namespace, builtin_library_doc, kw_doc, remaining_arguments, node
                )
            elif kw_doc.is_run_keywords() and len(remaining_arguments) > 0:
                yield from self._generate_run_keywords_tokens(namespace, builtin_library_doc, remaining_arguments, node)
            elif kw_doc.is_run_keyword_if() and len(remaining_arguments) > 0:
                yield from self._generate_run_keyword_if_tokens(
                    namespace, builtin_library_doc, remaining_arguments, node
                )
        else:
            yield from self.generate_keyword_tokens(namespace, kw_token, arguments, node, kw_doc)

    def generate_keyword_tokens(
        self,
        namespace: Namespace,
        kw_token: Token,
        arguments: Sequence[Token],
        node: ast.AST,
        kw_doc: Optional[KeywordDoc] = None,
    ) -> Iterator[Tuple[Token, ast.AST]]:
        """Generate tokens for regular keyword calls with named arguments.

        Args:
            namespace: The namespace context for keyword resolution
            kw_token: The keyword token
            arguments: Arguments to the keyword
            node: The AST node containing the keyword call
            kw_doc: Optional keyword documentation for argument validation

        Yields:
            Tuple[Token, ast.AST]: Token and node pairs for semantic highlighting
        """
        yield kw_token, node

        for token in arguments:
            if token.type == Token.ARGUMENT:
                name, value = split_from_equals(token.value)
                if value is not None:
                    if kw_doc is None:
                        kw_doc = namespace.find_keyword(_cached_unescape(kw_token.value))

                    if kw_doc and any(
                        v for v in kw_doc.arguments if v.kind == KeywordArgumentKind.VAR_NAMED or v.name == name
                    ):
                        yield from self.named_arg_processor.process_token_for_named_argument(token, node, kw_doc)
                    else:
                        yield token, node
                else:
                    yield token, node
            else:
                yield token, node


class SemanticTokenGenerator:
    """Generates semantic tokens from Robot Framework AST.

    This class handles the main token generation logic,
    creating and managing its own token mapper and keyword analyzer.
    """

    def __init__(self) -> None:
        """Initialize the generator with its own dependencies."""
        self.token_mapper = SemanticTokenMapper()
        self.keyword_analyzer = KeywordTokenAnalyzer(self.token_mapper)

    def _get_tokens_after(self, tokens: List[Token], target_token: Token) -> List[Token]:
        """Get all tokens after target token efficiently.

        This method is optimized for the common case where we need tokens after
        a specific token object. It uses object identity for faster comparison.

        Args:
            tokens: List of tokens to search through
            target_token: Token to find and get tokens after

        Returns:
            List of tokens that come after target_token
        """
        try:
            index = tokens.index(target_token)
            return tokens[index + 1 :]
        except ValueError:
            found = False
            result = []
            for token in tokens:
                if found:
                    result.append(token)
                elif token is target_token:
                    found = True
            return result

    def generate_sem_sub_tokens(
        self,
        namespace: Namespace,
        builtin_library_doc: Optional[LibraryDoc],
        token: Token,
        node: ast.AST,
        col_offset: Optional[int] = None,
        length: Optional[int] = None,
        yield_arguments: bool = False,
    ) -> Iterator[SemTokenInfo]:
        """Generate semantic token information for Robot Framework tokens.

        Args:
            namespace: The namespace context for keyword resolution
            builtin_library_doc: BuiltIn library documentation for builtin detection
            token: The Robot Framework token to process
            node: The AST node containing the token
            col_offset: Optional column offset override
            length: Optional length override
            yield_arguments: Whether to yield argument tokens

        Yields:
            SemTokenInfo: Semantic token information for LSP client
        """
        sem_info = self.token_mapper.get_semantic_info(token.type)
        if sem_info is not None:
            sem_type, sem_mod = sem_info

            if token.type in [Token.DOCUMENTATION, Token.METADATA]:
                sem_mod = {SemanticTokenModifiers.DOCUMENTATION}

            # TODO: maybe we can distinguish between local and global variables, by default all variables are global
            # if token.type in [Token.VARIABLE, Token.ASSIGN]:
            #     pass

            elif token.type in [Token.KEYWORD, ROBOT_KEYWORD_INNER] or (
                token.type == Token.NAME and cached_isinstance(node, Fixture, Template, TestTemplate)
            ):
                if (
                    namespace.find_keyword(
                        _cached_unescape(token.value),  # TODO: this must be resovle possible variables
                        raise_keyword_error=False,
                        handle_bdd_style=False,
                    )
                    is None
                ):
                    bdd_len = 0

                    if _ROBOT_VERSION < (6, 0):
                        bdd_match = self.token_mapper.BDD_TOKEN_REGEX.match(token.value)
                        if bdd_match:
                            bdd_len = len(bdd_match.group(1))
                    else:
                        bdd_prefixes = (
                            namespace.languages.bdd_prefixes
                            if namespace.languages is not None
                            else DEFAULT_BDD_PREFIXES
                        )

                        for prefix in bdd_prefixes:
                            if token.value.startswith(prefix + " "):
                                bdd_len = len(prefix)
                                break
                        else:
                            parts = token.value.split()
                            if len(parts) > 1:
                                for index in range(1, len(parts)):
                                    prefix = " ".join(parts[:index]).title()
                                    if prefix in bdd_prefixes:
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
                kw_doc = namespace.find_keyword(
                    _cached_unescape(token.value), raise_keyword_error=False
                )  # TODO: this must be resovle possible variables

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
                        {RobotSemTokenModifiers.BUILTIN} if kw_namespace == self.token_mapper.BUILTIN_MATCHER else None,
                    )
                    yield SemTokenInfo(
                        token.lineno,
                        col_offset + len(kw_namespace),
                        1,
                        SemanticTokenTypes.OPERATOR,
                    )

                if builtin_library_doc is not None and kw in builtin_library_doc.keywords:
                    if (
                        kw_doc is not None
                        and kw_doc.libname == self.token_mapper.BUILTIN_MATCHER
                        and kw_doc.matcher.match_string(kw)
                    ):
                        if not sem_mod:
                            sem_mod = set()
                        sem_mod.add(RobotSemTokenModifiers.BUILTIN)

                if kw_doc is not None and kw_doc.is_embedded and kw_doc.matcher.embedded_arguments:
                    if _ROBOT_VERSION >= (7, 3):
                        m = kw_doc.matcher.embedded_arguments.name.fullmatch(kw)
                    elif _ROBOT_VERSION >= (6, 0):
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
                                token.col_offset + kw_index + arg_start,
                            )

                            for sub_token in ModelHelper.tokenize_variables(
                                embedded_token,
                                ignore_errors=True,
                                identifiers="$@&%",
                            ):
                                for e in self.generate_sem_sub_tokens(
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

                    for g in self.token_mapper.ESCAPE_REGEX.finditer(token.value):
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
            elif _ROBOT_VERSION >= (5, 0) and token.type == Token.OPTION:
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
                    or (token.type == Token.ARGUMENT and cached_isinstance(node, TemplateArguments))
                    or (token.type != Token.NAME and cached_isinstance(node, Metadata))
                ):
                    yield SemTokenInfo.from_token(token, sem_type, sem_mod, col_offset, length)

    def generate_sem_tokens(
        self,
        token: Token,
        node: ast.AST,
        namespace: Namespace,
        builtin_library_doc: Optional[LibraryDoc],
    ) -> Iterator[SemTokenInfo]:
        """Generate semantic tokens for a given token and node.

        Args:
            token: The Robot Framework token
            node: The AST node containing the token
            namespace: The namespace context
            builtin_library_doc: BuiltIn library documentation

        Yields:
            SemTokenInfo: Semantic token information
        """
        if token.type in {Token.ARGUMENT, Token.TESTCASE_NAME, Token.KEYWORD_NAME} or (
            token.type == Token.NAME and cached_isinstance(node, VariablesImport, LibraryImport, ResourceImport)
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
                for e in self.generate_sem_sub_tokens(namespace, builtin_library_doc, sub_token, node):
                    yield e

        else:
            for e in self.generate_sem_sub_tokens(namespace, builtin_library_doc, token, node):
                yield e

    def collect_tokens(
        self,
        document: TextDocument,
        model: ast.AST,
        range: Optional[Range],
        namespace: Namespace,
        builtin_library_doc: Optional[LibraryDoc],
        token_types: Sequence[Enum],
        token_modifiers: Sequence[Enum],
    ) -> Union[SemanticTokens, SemanticTokensPartialResult, None]:
        """Collect semantic tokens from the Robot Framework AST.

        Args:
            document: The text document to process
            model: The Robot Framework AST model
            range: Optional range to limit token collection
            namespace: The namespace context
            builtin_library_doc: BuiltIn library documentation
            token_types: Available semantic token types for encoding
            token_modifiers: Available semantic token modifiers for encoding

        Returns:
            SemanticTokens with encoded token data
        """
        data = []
        last_line = 0
        last_col = 0

        def get_tokens() -> Iterator[Tuple[Token, ast.AST]]:
            current_section: Optional[Section] = None
            in_invalid_section = False

            for node in iter_nodes(model):
                if cached_isinstance(node, Section):
                    current_section = node
                    if _ROBOT_VERSION >= (7, 0):
                        in_invalid_section = cached_isinstance(current_section, InvalidSection)

                check_current_task_canceled()

                if cached_isinstance(node, Statement):
                    if cached_isinstance(node, LibraryImport) and node.name:
                        lib_doc = namespace.get_imported_library_libdoc(node.name, node.args, node.alias)
                        kw_doc = lib_doc.inits.keywords[0] if lib_doc and lib_doc.inits else None
                        if lib_doc is not None:
                            for token in node.tokens:
                                if token.type == Token.ARGUMENT:
                                    processor = self.keyword_analyzer.named_arg_processor
                                    yield from processor.process_token_for_named_argument(
                                        token, node, kw_doc, ROBOT_NAMED_ARGUMENT
                                    )
                                else:
                                    yield token, node
                            continue
                    if cached_isinstance(node, VariablesImport) and node.name:
                        lib_doc = namespace.get_variables_import_libdoc(node.name, node.args)
                        kw_doc = lib_doc.inits.keywords[0] if lib_doc and lib_doc.inits else None
                        if lib_doc is not None:
                            for token in node.tokens:
                                if token.type == Token.ARGUMENT:
                                    processor = self.keyword_analyzer.named_arg_processor
                                    yield from processor.process_token_for_named_argument(
                                        token, node, kw_doc, ROBOT_NAMED_ARGUMENT
                                    )
                                else:
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
                                _cached_unescape(ModelHelper.strip_bdd_prefix(namespace, kw_token).value)
                            ):
                                if n is not None:
                                    matcher = KeywordMatcher(n)
                                    if matcher in ALL_RUN_KEYWORDS_MATCHERS:
                                        kw = n
                            if kw:
                                kw_doc = namespace.find_keyword(_cached_unescape(kw_token.value))
                                if kw_doc is not None and kw_doc.is_any_run_keyword():
                                    for kw_res in self.keyword_analyzer.generate_run_kw_tokens(
                                        namespace,
                                        builtin_library_doc,
                                        kw_doc,
                                        kw_token,
                                        self._get_tokens_after(node.tokens, kw_token),
                                        node,
                                    ):
                                        yield kw_res
                                    continue
                            else:
                                for kw_res in self.keyword_analyzer.generate_keyword_tokens(
                                    namespace,
                                    kw_token,
                                    self._get_tokens_after(node.tokens, kw_token),
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

                data.append(token_types.index(token.sem_token_type))

                data.append(
                    reduce(
                        operator.or_,
                        [2 ** token_modifiers.index(e) for e in token.sem_modifiers],
                    )
                    if token.sem_modifiers
                    else 0
                )

        return SemanticTokens(data=data)


class RobotSemanticTokenProtocolPart(RobotLanguageServerProtocolPart):
    """Main protocol part for semantic token generation.

    This class provides a clean interface to the LSP client by delegating
    semantic token generation to the SemanticTokenGenerator.
    """

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)
        parent.semantic_tokens.token_types += list(RobotSemTokenTypes)
        parent.semantic_tokens.token_modifiers += list(RobotSemTokenModifiers)

        parent.semantic_tokens.collect_full.add(self.collect_full)

        self.parent.on_initialized.add(self._on_initialized)

        self.token_generator = SemanticTokenGenerator()

    def _on_initialized(self, sender: Any) -> None:
        self.parent.documents_cache.namespace_invalidated.add(self.namespace_invalidated)

    @language_id("robotframework")
    def namespace_invalidated(self, sender: Any, namespace: Namespace) -> None:
        if namespace.document is not None and namespace.document.opened_in_editor:
            self.parent.semantic_tokens.refresh()

    def _collect(
        self, document: TextDocument, range: Optional[Range]
    ) -> Union[SemanticTokens, SemanticTokensPartialResult, None]:
        """Collect semantic tokens for a document or range.

        Args:
            document: The text document to process
            range: Optional range to limit token collection

        Returns:
            SemanticTokens with encoded token data
        """
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

        return self.token_generator.collect_tokens(
            document,
            model,
            range,
            namespace,
            builtin_library_doc,
            self.parent.semantic_tokens.token_types,
            self.parent.semantic_tokens.token_modifiers,
        )

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
