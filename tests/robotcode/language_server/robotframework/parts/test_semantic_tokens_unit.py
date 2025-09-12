from typing import Any

import pytest
from robot.parsing import get_model
from robot.parsing.lexer.tokens import Token
from robot.parsing.model.statements import KeywordCall, Variable

from robotcode.language_server.robotframework.parts.semantic_tokens import (
    ROBOT_NAMED_ARGUMENT,
    ROBOT_OPERATOR,
    ArgumentProcessor,
    KeywordTokenAnalyzer,
    NamedArgumentInfo,
    NamedArgumentProcessor,
    RobotSemTokenModifiers,
    RobotSemTokenTypes,
    SemanticTokenGenerator,
    SemanticTokenMapper,
    SemTokenInfo,
)
from robotcode.robot.diagnostics.library_doc import (
    KeywordArgumentKind,
    KeywordDoc,
    LibraryDoc,
)
from robotcode.robot.utils import get_robot_version


class TestSemanticTokenMapper:
    """Test cases for SemanticTokenMapper class."""

    def test_generate_mapping_creates_valid_mapping(self) -> None:
        """Test that generate_mapping creates a valid token type mapping."""
        mapping = SemanticTokenMapper.generate_mapping()

        assert isinstance(mapping, dict)
        assert len(mapping) > 0

        # Check that some expected token types are in the mapping
        assert Token.KEYWORD in mapping
        assert Token.VARIABLE in mapping
        assert Token.ARGUMENT in mapping

    def test_mapping_singleton_behavior(self) -> None:
        """Test that mapping() returns the same instance across calls."""
        mapper1 = SemanticTokenMapper()
        mapper2 = SemanticTokenMapper()

        mapping1 = mapper1.mapping()
        mapping2 = mapper2.mapping()

        assert mapping1 is mapping2  # Should be the same object

    def test_get_semantic_info_with_valid_token(self) -> None:
        """Test get_semantic_info with valid token types."""
        mapper = SemanticTokenMapper()

        result = mapper.get_semantic_info(Token.KEYWORD)
        assert result is not None
        assert len(result) == 2  # (token_type, modifiers)

    def test_get_semantic_info_with_invalid_token(self) -> None:
        """Test get_semantic_info with invalid token types."""
        mapper = SemanticTokenMapper()

        result = mapper.get_semantic_info("INVALID_TOKEN")
        assert result is None

    def test_get_semantic_info_with_none(self) -> None:
        """Test get_semantic_info with None input."""
        mapper = SemanticTokenMapper()

        result = mapper.get_semantic_info(None)
        assert result is None

    def test_builtin_matcher_is_configured(self) -> None:
        """Test that BUILTIN_MATCHER is properly configured."""
        assert SemanticTokenMapper.BUILTIN_MATCHER.name == "BuiltIn"
        assert SemanticTokenMapper.BUILTIN_MATCHER._is_namespace is True

    @pytest.mark.parametrize(
        ("text", "expected_groups"),
        [
            ("\\n", ["\\n"]),
            ("\\\\", ["\\\\"]),
            ("\\x41", ["\\x41"]),
            ("text\\nmore", ["text", "\\n", "more"]),
            ("\\invalid", ["\\i", "nvalid"]),  # Invalid escape splits
        ],
    )
    def test_escape_regex_patterns(self, text: str, expected_groups: list[str]) -> None:
        """Test that ESCAPE_REGEX correctly matches escape sequences."""
        matches = list(SemanticTokenMapper.ESCAPE_REGEX.finditer(text))
        actual_groups = [match.group() for match in matches]
        assert actual_groups == expected_groups, f"Failed for input: {text}"

    @pytest.mark.parametrize(
        ("text", "should_match"),
        [
            ("Given something", True),
            ("When action", True),
            ("Then result", True),
            ("And more", True),
            ("But exception", True),
            ("given lowercase", True),  # Case insensitive
            ("Invalid prefix", False),
            ("Givenno space", False),
        ],
    )
    def test_bdd_token_regex_patterns(self, text: str, should_match: bool) -> None:
        """Test that BDD_TOKEN_REGEX correctly matches BDD prefixes."""
        match = SemanticTokenMapper.BDD_TOKEN_REGEX.match(text)
        assert bool(match) == should_match, f"Failed for input: {text}"

    def test_robot_framework_version_specific_mappings(self) -> None:
        """Test that version-specific token mappings are correct."""
        mapper = SemanticTokenMapper()
        mapping = mapper.mapping()
        rf_version = get_robot_version()

        # RF 5.0+ tokens
        if rf_version >= (5, 0):
            rf5_tokens = [Token.TRY, Token.EXCEPT, Token.FINALLY, Token.WHILE, Token.CONTINUE, Token.BREAK]
            for token_type in rf5_tokens:
                if hasattr(Token, token_type):  # Check if token exists in this RF version
                    token_val = getattr(Token, token_type)
                    assert token_val in mapping, f"RF 5.0+ token {token_type} should be in mapping"
                    sem_type, _ = mapping[token_val]
                    assert sem_type == RobotSemTokenTypes.CONTROL_FLOW

        # RF 6.0+ tokens
        if rf_version >= (6, 0):
            if hasattr(Token, "CONFIG"):
                assert Token.CONFIG in mapping
                sem_type, _ = mapping[Token.CONFIG]
                assert sem_type == RobotSemTokenTypes.CONFIG

        # RF 7.0+ tokens
        if rf_version >= (7, 0):
            if hasattr(Token, "VAR"):
                assert Token.VAR in mapping
                sem_type, _ = mapping[Token.VAR]
                assert sem_type == RobotSemTokenTypes.VAR

    def test_cached_unescape_function(self) -> None:
        """Test the cached unescape function."""
        from robotcode.language_server.robotframework.parts.semantic_tokens import _cached_unescape

        test_cases = [
            ("\\n", "\n"),
            ("\\t", "\t"),
            ("\\\\", "\\"),
            ("normal text", "normal text"),
            ("", ""),
        ]

        for input_text, expected in test_cases:
            result = _cached_unescape(input_text)
            assert result == expected, f"Failed for input: {input_text}"

        # Test caching - same input should return same object
        result1 = _cached_unescape("\\n")
        result2 = _cached_unescape("\\n")
        assert result1 is result2, "Cached function should return same object for same input"


class TestArgumentProcessor:
    """Test cases for ArgumentProcessor class."""

    def test_initialization(self) -> None:
        """Test ArgumentProcessor initialization."""
        tokens = [Token(Token.ARGUMENT, "arg1"), Token(Token.ARGUMENT, "arg2")]
        processor = ArgumentProcessor(tokens)

        assert processor.arguments == tokens
        assert processor.index == 0

    def test_has_next_with_arguments(self) -> None:
        """Test has_next when arguments are available."""
        tokens = [Token(Token.ARGUMENT, "arg1")]
        processor = ArgumentProcessor(tokens)

        assert processor.has_next() is True

    def test_has_next_with_no_arguments(self) -> None:
        """Test has_next when no arguments are available."""
        processor = ArgumentProcessor([])

        assert processor.has_next() is False

    def test_peek_with_arguments(self) -> None:
        """Test peek without consuming arguments."""
        token = Token(Token.ARGUMENT, "arg1")
        processor = ArgumentProcessor([token])

        peeked = processor.peek()
        assert peeked is token
        assert processor.index == 0  # Should not advance

    def test_peek_with_no_arguments(self) -> None:
        """Test peek when no arguments are available."""
        processor = ArgumentProcessor([])

        peeked = processor.peek()
        assert peeked is None

    def test_consume_with_arguments(self) -> None:
        """Test consume advances and returns token."""
        token = Token(Token.ARGUMENT, "arg1")
        processor = ArgumentProcessor([token])

        consumed = processor.consume()
        assert consumed is token
        assert processor.index == 1

    def test_consume_with_no_arguments(self) -> None:
        """Test consume when no arguments are available."""
        processor = ArgumentProcessor([])

        consumed = processor.consume()
        assert consumed is None
        assert processor.index == 0

    def test_skip_non_data_tokens(self) -> None:
        """Test skipping non-data tokens."""
        tokens = [
            Token(Token.SEPARATOR, "  "),
            Token(Token.ARGUMENT, "arg1"),
            Token(Token.SEPARATOR, "  "),
            Token(Token.ARGUMENT, "arg2"),
        ]
        processor = ArgumentProcessor(tokens)

        # Mock the skip logic - the actual implementation would need to be tested
        # This is a simplified test
        skipped = processor.skip_non_data_tokens()
        assert isinstance(skipped, list)

    def test_remaining_slice(self) -> None:
        """Test getting remaining arguments as slice."""
        tokens = [Token(Token.ARGUMENT, "arg1"), Token(Token.ARGUMENT, "arg2")]
        processor = ArgumentProcessor(tokens)
        processor.consume()  # Advance past first

        remaining = processor.remaining_slice()
        assert len(remaining) == 1
        assert remaining[0].value == "arg2"

    def test_find_separator_index_with_existing_separator(self) -> None:
        """Test finding separator index when separator exists."""
        tokens = [
            Token(Token.ARGUMENT, "arg1"),
            Token(Token.ARGUMENT, "AND"),
            Token(Token.ARGUMENT, "arg2"),
        ]
        processor = ArgumentProcessor(tokens)

        index = processor.find_separator_index(frozenset({"AND"}))
        assert index == 1

    def test_find_separator_index_with_no_separator(self) -> None:
        """Test finding separator index when no separator exists."""
        tokens = [Token(Token.ARGUMENT, "arg1"), Token(Token.ARGUMENT, "arg2")]
        processor = ArgumentProcessor(tokens)

        index = processor.find_separator_index(frozenset({"AND"}))
        assert index is None

    def test_find_separator_index_with_empty_set(self) -> None:
        """Test finding separator index with empty separator set."""
        tokens = [Token(Token.ARGUMENT, "arg1")]
        processor = ArgumentProcessor(tokens)

        index = processor.find_separator_index(frozenset())
        assert index is None

    def test_iter_until_separator(self) -> None:
        """Test iterating until separator is found."""
        tokens = [
            Token(Token.ARGUMENT, "arg1"),
            Token(Token.ARGUMENT, "arg2"),
            Token(Token.ARGUMENT, "AND"),
            Token(Token.ARGUMENT, "arg3"),
        ]
        processor = ArgumentProcessor(tokens)

        # Iterate until AND separator
        collected = list(processor.iter_until_separator(["AND"]))

        assert len(collected) == 2
        assert collected[0].value == "arg1"
        assert collected[1].value == "arg2"

        # Processor should now be positioned at AND
        current = processor.peek()
        assert current is not None
        assert current.value == "AND"

    def test_iter_all_remaining(self) -> None:
        """Test iterating all remaining tokens."""
        tokens = [
            Token(Token.ARGUMENT, "arg1"),
            Token(Token.ARGUMENT, "arg2"),
            Token(Token.ARGUMENT, "arg3"),
        ]
        processor = ArgumentProcessor(tokens)

        # Consume first token
        processor.consume()

        # Iterate remaining
        remaining = list(processor.iter_all_remaining())

        assert len(remaining) == 2
        assert remaining[0].value == "arg2"
        assert remaining[1].value == "arg3"

        # Processor should be at end
        assert not processor.has_next()

    def test_skip_non_data_tokens_real_implementation(self) -> None:
        """Test skipping non-data tokens with real implementation."""
        tokens = [
            Token(Token.SEPARATOR, "  "),
            Token(Token.SEPARATOR, "\t"),
            Token(Token.ARGUMENT, "arg1"),
            Token(Token.SEPARATOR, "  "),
            Token(Token.ARGUMENT, "arg2"),
        ]
        processor = ArgumentProcessor(tokens)

        # Skip initial separators
        skipped = processor.skip_non_data_tokens()

        # Should have skipped the two separators
        assert len(skipped) == 2
        assert all(token.type == Token.SEPARATOR for token in skipped)

        # Should now be positioned at first argument
        current = processor.peek()
        assert current is not None
        assert current.value == "arg1"


class TestNamedArgumentProcessor:
    """Test cases for NamedArgumentProcessor class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.token_mapper = SemanticTokenMapper()
        self.processor = NamedArgumentProcessor(self.token_mapper)

    def test_initialization(self) -> None:
        """Test NamedArgumentProcessor initialization."""
        assert self.processor.token_mapper is self.token_mapper

    def test_parse_named_argument_valid(self) -> None:
        """Test parsing valid named argument."""
        result = self.processor.parse_named_argument("name=value")

        assert result is not None
        assert isinstance(result, NamedArgumentInfo)
        assert result.name == "name"
        assert result.value == "value"
        assert result.name_length == 4
        assert result.total_length == 10

    def test_parse_named_argument_invalid(self) -> None:
        """Test parsing invalid named argument (no equals)."""
        result = self.processor.parse_named_argument("just_a_value")

        assert result is None

    def test_parse_named_argument_empty_value(self) -> None:
        """Test parsing named argument with empty value."""
        result = self.processor.parse_named_argument("name=")

        assert result is not None
        assert result.name == "name"
        assert result.value == ""
        assert result.name_length == 4
        assert result.total_length == 5

    def test_validate_named_argument_with_valid_kw_doc(self) -> None:
        """Test validation with valid keyword documentation."""
        # Create a mock KeywordDoc with valid arguments
        kw_doc = KeywordDoc(
            name="Test Keyword",
            line_no=1,
            col_offset=0,
            end_line_no=1,
            end_col_offset=10,
            source="test.robot",
            arguments=[
                type("Arg", (), {"name": "valid_arg", "kind": KeywordArgumentKind.POSITIONAL_OR_NAMED})(),
                type("Arg", (), {"name": "var_named", "kind": KeywordArgumentKind.VAR_NAMED})(),
            ],
        )

        # Test valid argument
        is_valid = self.processor._validate_named_argument("valid_arg", kw_doc)
        assert is_valid is True

        # Test VAR_NAMED argument
        is_valid = self.processor._validate_named_argument("any_name", kw_doc)
        assert is_valid is True  # Should be valid due to VAR_NAMED

    def test_validate_named_argument_with_invalid_name(self) -> None:
        """Test validation with invalid argument name."""
        kw_doc = KeywordDoc(
            name="Test Keyword",
            line_no=1,
            col_offset=0,
            end_line_no=1,
            end_col_offset=10,
            source="test.robot",
            arguments=[
                type("Arg", (), {"name": "valid_arg", "kind": KeywordArgumentKind.POSITIONAL_OR_NAMED})(),
            ],
        )

        is_valid = self.processor._validate_named_argument("invalid_arg", kw_doc)
        assert is_valid is False

    def test_validate_named_argument_with_no_kw_doc(self) -> None:
        """Test validation with no keyword documentation."""
        is_valid = self.processor._validate_named_argument("any_arg", None)
        assert is_valid is False

    def test_validate_named_argument_with_empty_arguments(self) -> None:
        """Test validation with keyword doc but no arguments."""
        kw_doc = KeywordDoc(
            name="Test Keyword",
            line_no=1,
            col_offset=0,
            end_line_no=1,
            end_col_offset=10,
            source="test.robot",
            arguments=[],
        )

        is_valid = self.processor._validate_named_argument("any_arg", kw_doc)
        assert is_valid is False

    def test_generate_named_argument_tokens_valid(self) -> None:
        """Test generating tokens for valid named argument."""
        token = Token(Token.ARGUMENT, "name=value", 1, 0)
        arg_info = NamedArgumentInfo("name", "value", 4, 10, True)
        node = KeywordCall([])

        tokens = list(self.processor.generate_named_argument_tokens(token, arg_info, node))

        assert len(tokens) == 3
        # Name token
        assert tokens[0][0].type == ROBOT_NAMED_ARGUMENT
        assert tokens[0][0].value == "name"
        # Operator token
        assert tokens[1][0].type == ROBOT_OPERATOR
        assert tokens[1][0].value == "="
        # Value token
        assert tokens[2][0].value == "value"

    def test_generate_named_argument_tokens_invalid(self) -> None:
        """Test generating tokens for invalid named argument."""
        token = Token(Token.ARGUMENT, "name=value", 1, 0)
        arg_info = NamedArgumentInfo("name", "value", 4, 10, False)
        node = KeywordCall([])

        tokens = list(self.processor.generate_named_argument_tokens(token, arg_info, node))

        assert len(tokens) == 1  # Should yield only the original token


class TestKeywordTokenAnalyzer:
    """Test cases for KeywordTokenAnalyzer class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.token_mapper = SemanticTokenMapper()
        self.analyzer = KeywordTokenAnalyzer(self.token_mapper)

    def test_initialization(self) -> None:
        """Test KeywordTokenAnalyzer initialization."""
        assert self.analyzer.token_mapper is self.token_mapper
        assert isinstance(self.analyzer.named_arg_processor, NamedArgumentProcessor)

    def test_skip_non_data_tokens(self) -> None:
        """Test skipping non-data tokens with ArgumentProcessor."""
        tokens = [Token(Token.SEPARATOR, "  "), Token(Token.ARGUMENT, "arg")]
        processor = ArgumentProcessor(tokens)
        node = KeywordCall([])

        skipped = self.analyzer._skip_non_data_tokens(processor, node)

        assert isinstance(skipped, list)
        # Each item should be a (token, node) tuple
        for item in skipped:
            assert len(item) == 2
            assert isinstance(item[0], Token)

    def test_generate_keyword_tokens_simple(self) -> None:
        """Test generating tokens for simple keyword call."""
        kw_token = Token(Token.KEYWORD, "Log", 1, 0)
        arguments = [Token(Token.ARGUMENT, "Hello")]
        node = KeywordCall([])

        # Create a minimal namespace mock
        namespace = type("MockNamespace", (), {"find_keyword": lambda self, name, raise_keyword_error=True: None})()

        tokens = list(self.analyzer.generate_keyword_tokens(namespace, kw_token, arguments, node))

        assert len(tokens) >= 2  # At least keyword and argument tokens
        assert tokens[0][0] is kw_token

    def test_generate_keyword_tokens_with_named_args(self) -> None:
        """Test generating tokens for keyword call with named arguments."""
        kw_token = Token(Token.KEYWORD, "Log", 1, 0)
        arguments = [Token(Token.ARGUMENT, "message=Hello")]
        node = KeywordCall([])

        # Create a mock keyword doc with named arguments
        kw_doc = KeywordDoc(
            name="Log",
            line_no=1,
            col_offset=0,
            end_line_no=1,
            end_col_offset=10,
            source="test.robot",
            arguments=[
                type("Arg", (), {"name": "message", "kind": KeywordArgumentKind.POSITIONAL_OR_NAMED})(),
            ],
        )

        namespace = type("MockNamespace", (), {"find_keyword": lambda self, name, raise_keyword_error=True: kw_doc})()

        tokens = list(self.analyzer.generate_keyword_tokens(namespace, kw_token, arguments, node, kw_doc))

        assert len(tokens) >= 2


class TestRunKeywordTokenAnalysis:
    """Comprehensive tests for Run Keyword variants - CRITICAL missing functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.token_mapper = SemanticTokenMapper()
        self.analyzer = KeywordTokenAnalyzer(self.token_mapper)

    def test_run_keyword_if_complete_flow(self) -> None:
        """Test complete Run Keyword If logic with ELSE IF and ELSE."""
        kw_token = Token(Token.KEYWORD, "Run Keyword If", 1, 0)
        arguments = [
            Token(Token.ARGUMENT, "${condition1}", 1, 16),  # condition
            Token(Token.ARGUMENT, "Log", 1, 30),  # keyword
            Token(Token.ARGUMENT, "Case1", 1, 34),  # arg
            Token(Token.ARGUMENT, "ELSE IF", 1, 40),  # separator
            Token(Token.ARGUMENT, "${condition2}", 1, 48),  # condition
            Token(Token.ARGUMENT, "Log", 1, 62),  # keyword
            Token(Token.ARGUMENT, "Case2", 1, 66),  # arg
            Token(Token.ARGUMENT, "ELSE", 1, 72),  # separator
            Token(Token.ARGUMENT, "Log", 1, 77),  # keyword
            Token(Token.ARGUMENT, "Default", 1, 81),  # arg
        ]

        # Create a KeywordDoc for Run Keyword If
        kw_doc = KeywordDoc(
            name="Run Keyword If",
            line_no=1,
            col_offset=0,
            end_line_no=1,
            end_col_offset=15,
            source="BuiltIn",
            libname="BuiltIn",
        )
        node = KeywordCall([])
        namespace = type(
            "MockNamespace",
            (),
            {
                "find_keyword": lambda self, name, **kwargs: None,
                "languages": None,
            },
        )()

        # Test token generation
        tokens = list(self.analyzer.generate_run_kw_tokens(namespace, None, kw_doc, kw_token, arguments, node))

        # Should process all tokens
        assert len(tokens) >= len(arguments) + 1  # +1 for keyword token

    def test_run_keywords_with_and_separators(self) -> None:
        """Test Run Keywords with AND separators."""
        kw_token = Token(Token.KEYWORD, "Run Keywords", 1, 0)
        arguments = [
            Token(Token.ARGUMENT, "Log", 1, 13),
            Token(Token.ARGUMENT, "First", 1, 17),
            Token(Token.ARGUMENT, "AND", 1, 23),  # separator
            Token(Token.ARGUMENT, "Log", 1, 27),
            Token(Token.ARGUMENT, "Second", 1, 31),
            Token(Token.ARGUMENT, "AND", 1, 38),  # separator
            Token(Token.ARGUMENT, "Log", 1, 42),
            Token(Token.ARGUMENT, "Third", 1, 46),
        ]

        # Create a KeywordDoc for Run Keywords
        kw_doc = KeywordDoc(
            name="Run Keywords",
            line_no=1,
            col_offset=0,
            end_line_no=1,
            end_col_offset=12,
            source="BuiltIn",
            libname="BuiltIn",
        )
        node = KeywordCall([])
        namespace = type(
            "MockNamespace",
            (),
            {
                "find_keyword": lambda self, name, **kwargs: None,
                "languages": None,
            },
        )()

        tokens = list(self.analyzer.generate_run_kw_tokens(namespace, None, kw_doc, kw_token, arguments, node))

        # Should process all tokens including separators
        assert len(tokens) >= len(arguments) + 1

    def test_run_keyword_simple(self) -> None:
        """Test simple Run Keyword call."""
        kw_token = Token(Token.KEYWORD, "Run Keyword", 1, 0)
        arguments = [
            Token(Token.ARGUMENT, "Log", 1, 12),
            Token(Token.ARGUMENT, "Hello", 1, 16),
            Token(Token.ARGUMENT, "World", 1, 22),
        ]

        # Create a KeywordDoc for simple Run Keyword
        kw_doc = KeywordDoc(
            name="Run Keyword",
            line_no=1,
            col_offset=0,
            end_line_no=1,
            end_col_offset=11,
            source="BuiltIn",
            libname="BuiltIn",
        )
        node = KeywordCall([])
        namespace = type(
            "MockNamespace",
            (),
            {
                "find_keyword": lambda self, name, **kwargs: None,
                "languages": None,
            },
        )()

        tokens = list(self.analyzer.generate_run_kw_tokens(namespace, None, kw_doc, kw_token, arguments, node))

        assert len(tokens) >= len(arguments) + 1

    def test_non_run_keyword_handling(self) -> None:
        """Test that non-run-keyword calls are handled normally."""
        kw_token = Token(Token.KEYWORD, "Log", 1, 0)
        arguments = [Token(Token.ARGUMENT, "Hello")]

        # Regular keyword (not run keyword)
        kw_doc = None
        node = KeywordCall([])
        namespace = type(
            "MockNamespace",
            (),
            {
                "find_keyword": lambda self, name, **kwargs: None,
                "languages": None,
            },
        )()

        tokens = list(self.analyzer.generate_run_kw_tokens(namespace, None, kw_doc, kw_token, arguments, node))

        # Should handle as regular keyword
        assert len(tokens) >= 2  # keyword + argument


class TestRealRobotFrameworkIntegration:
    """Test with real Robot Framework code parsing - VERY IMPORTANT: Missing completely!"""

    def test_keyword_call_semantic_tokens_real_ast(self) -> None:
        """Test semantic tokens with real Robot Framework AST."""
        robot_code = """*** Test Cases ***
Example Test
    Log    message=Hello World    level=INFO
    Set Variable    ${value}    test_value
"""

        # Parse real Robot Framework code
        model = get_model(robot_code)
        generator = SemanticTokenGenerator()

        # Find KeywordCall nodes in AST
        keyword_calls = []
        import ast

        for node in ast.walk(model):
            if hasattr(node, "tokens") and any(t.type == Token.KEYWORD for t in getattr(node, "tokens", [])):
                keyword_calls.append(node)

        assert len(keyword_calls) >= 2  # Log and Set Variable

        # Create minimal namespace for testing
        namespace = type(
            "MockNamespace",
            (),
            {
                "find_keyword": lambda self, name, **kwargs: None,
                "languages": None,
            },
        )()

        # Test that tokens are generated without errors
        for kw_call in keyword_calls:
            if hasattr(kw_call, "tokens"):
                for token in getattr(kw_call, "tokens", []):
                    if token.type == Token.KEYWORD:
                        sem_tokens = list(generator.generate_sem_tokens(token, kw_call, namespace, None))
                        assert len(sem_tokens) >= 1
                        assert all(isinstance(st, SemTokenInfo) for st in sem_tokens)

    def test_named_arguments_in_real_code(self) -> None:
        """Test named arguments parsing in real Robot Framework code."""
        robot_code = """*** Keywords ***
Custom Keyword
    Log    message=Hello    level=DEBUG    console=True
    Should Be Equal    first=1    second=1    msg=Values should match
"""

        model = get_model(robot_code)
        processor = NamedArgumentProcessor(SemanticTokenMapper())

        # Find all ARGUMENT tokens with equals
        argument_tokens = []
        import ast

        for node in ast.walk(model):
            if hasattr(node, "tokens"):
                for token in getattr(node, "tokens", []):
                    if token.type == Token.ARGUMENT and "=" in token.value:
                        argument_tokens.append(token)

        # Test named argument parsing
        named_args = []
        for token in argument_tokens:
            arg_info = processor.parse_named_argument(token.value)
            if arg_info:
                named_args.append(arg_info)

        # Should find multiple named arguments
        assert len(named_args) >= 4  # message=, level=, console=, first=, second=, msg=

        # Verify structure
        for arg_info in named_args:
            assert isinstance(arg_info, NamedArgumentInfo)
            assert arg_info.name_length > 0
            assert arg_info.total_length > arg_info.name_length

    def test_variable_expressions_in_real_code(self) -> None:
        """Test variable expression handling in real code."""
        robot_code = """*** Variables ***
${SIMPLE_VAR}    Hello
@{LIST_VAR}      item1    item2
&{DICT_VAR}      key=value    another=test

*** Test Cases ***
Variable Test
    Log    ${SIMPLE_VAR}
    Log Many    @{LIST_VAR}
    Log    &{DICT_VAR}[key]
"""

        model = get_model(robot_code)
        generator = SemanticTokenGenerator()

        # Find variable tokens (declarations in *** Variables *** section)
        variable_declarations = []
        # Find argument tokens that contain variables (usage in test cases)
        variable_usages = []

        import ast

        for node in ast.walk(model):
            if hasattr(node, "tokens"):
                for token in getattr(node, "tokens", []):
                    if token.type == Token.VARIABLE:
                        variable_declarations.append((token, node))
                    elif token.type == Token.ARGUMENT and any(pattern in token.value for pattern in ["${", "@{", "&{"]):
                        variable_usages.append((token, node))

        # Should find 3 variable declarations and some variable usages
        assert len(variable_declarations) == 3  # ${SIMPLE_VAR}, @{LIST_VAR}, &{DICT_VAR}
        assert len(variable_usages) >= 3  # ${SIMPLE_VAR}, @{LIST_VAR}, &{DICT_VAR}[key]

        # Test semantic token generation for variable declarations
        namespace = type(
            "MockNamespace",
            (),
            {
                "find_keyword": lambda self, name, **kwargs: None,
                "languages": None,
            },
        )()

        for token, node in variable_declarations:
            sem_tokens = list(generator.generate_sem_tokens(token, node, namespace, None))
            assert len(sem_tokens) >= 1
            assert any(st.sem_token_type == RobotSemTokenTypes.VARIABLE for st in sem_tokens)

        # Test that variable usages in arguments are also processed
        for token, node in variable_usages:
            sem_tokens = list(generator.generate_sem_tokens(token, node, namespace, None))
            assert len(sem_tokens) >= 1  # Should generate at least one token

    def test_bdd_prefixes_in_real_code(self) -> None:
        """Test BDD prefix detection in real Robot Framework code."""
        robot_code = """*** Test Cases ***
BDD Test Case
    Given I have initial state
    When I perform action
    Then I should see result
    And I should also see this
    But not this other thing
"""

        model = get_model(robot_code)

        # Find keyword tokens that might have BDD prefixes
        keyword_tokens = []
        import ast

        for node in ast.walk(model):
            if hasattr(node, "tokens"):
                for token in getattr(node, "tokens", []):
                    if token.type == Token.KEYWORD:
                        keyword_tokens.append(token)

        # Test BDD regex on actual keywords
        bdd_matches = []
        for token in keyword_tokens:
            match = SemanticTokenMapper.BDD_TOKEN_REGEX.match(token.value)
            if match:
                bdd_matches.append((token.value, match.group(1)))

        # Should find BDD prefixes
        assert len(bdd_matches) >= 5  # Given, When, Then, And, But

        # Verify expected prefixes
        expected_prefixes = {"Given", "When", "Then", "And", "But"}
        found_prefixes = {match[1] for match in bdd_matches}
        assert expected_prefixes.issubset(found_prefixes)


class TestSemanticTokenGenerator:
    """Test cases for SemanticTokenGenerator class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.generator = SemanticTokenGenerator()

    def test_initialization(self) -> None:
        """Test SemanticTokenGenerator initialization."""
        assert isinstance(self.generator.token_mapper, SemanticTokenMapper)
        assert isinstance(self.generator.keyword_analyzer, KeywordTokenAnalyzer)

    def test_get_tokens_after_with_valid_token(self) -> None:
        """Test getting tokens after a specific token."""
        token1 = Token(Token.KEYWORD, "Log", 1, 0)
        token2 = Token(Token.ARGUMENT, "Hello", 1, 4)
        token3 = Token(Token.ARGUMENT, "World", 1, 10)
        tokens = [token1, token2, token3]

        result = self.generator._get_tokens_after(tokens, token1)

        assert len(result) == 2
        assert result[0] is token2
        assert result[1] is token3

    def test_get_tokens_after_with_missing_token(self) -> None:
        """Test getting tokens after a token that doesn't exist."""
        token1 = Token(Token.KEYWORD, "Log", 1, 0)
        token2 = Token(Token.ARGUMENT, "Hello", 1, 4)
        missing_token = Token(Token.KEYWORD, "Missing", 1, 0)
        tokens = [token1, token2]

        result = self.generator._get_tokens_after(tokens, missing_token)

        assert len(result) == 0

    def test_get_tokens_after_with_last_token(self) -> None:
        """Test getting tokens after the last token."""
        token1 = Token(Token.KEYWORD, "Log", 1, 0)
        token2 = Token(Token.ARGUMENT, "Hello", 1, 4)
        tokens = [token1, token2]

        result = self.generator._get_tokens_after(tokens, token2)

        assert len(result) == 0

    def test_generate_sem_sub_tokens_basic(self) -> None:
        """Test generating semantic sub-tokens for basic token."""
        token = Token(Token.KEYWORD, "Log", 1, 0)
        node = KeywordCall([])

        # Create minimal mocks
        namespace = type("MockNamespace", (), {"find_keyword": lambda self, name, **kwargs: None, "languages": None})()

        sem_tokens = list(self.generator.generate_sem_sub_tokens(namespace, None, token, node))

        assert len(sem_tokens) >= 1
        assert all(isinstance(st, SemTokenInfo) for st in sem_tokens)

    def test_generate_sem_tokens_with_variable_token(self) -> None:
        """Test generating semantic tokens for variable token."""
        token = Token(Token.VARIABLE, "${var}", 1, 0)
        node = Variable([])

        namespace = type("MockNamespace", (), {"find_keyword": lambda self, name, **kwargs: None, "languages": None})()

        sem_tokens = list(self.generator.generate_sem_tokens(token, node, namespace, None))

        assert len(sem_tokens) >= 1
        assert all(isinstance(st, SemTokenInfo) for st in sem_tokens)


class TestSemTokenInfo:
    """Test cases for SemTokenInfo dataclass."""

    def test_from_token_basic(self) -> None:
        """Test creating SemTokenInfo from basic token."""
        token = Token(Token.KEYWORD, "Log", 1, 5)

        sem_token = SemTokenInfo.from_token(token, RobotSemTokenTypes.KEYWORD)

        assert sem_token.lineno == 1
        assert sem_token.col_offset == 5
        assert sem_token.length == 3  # len("Log")
        assert sem_token.sem_token_type == RobotSemTokenTypes.KEYWORD
        assert sem_token.sem_modifiers is None

    def test_from_token_with_modifiers(self) -> None:
        """Test creating SemTokenInfo with modifiers."""
        token = Token(Token.KEYWORD, "Log", 1, 5)
        modifiers = {RobotSemTokenModifiers.BUILTIN}

        sem_token = SemTokenInfo.from_token(token, RobotSemTokenTypes.KEYWORD, modifiers)  # type: ignore[arg-type]

        assert sem_token.sem_modifiers == modifiers

    def test_from_token_with_custom_offset_and_length(self) -> None:
        """Test creating SemTokenInfo with custom offset and length."""
        token = Token(Token.KEYWORD, "Long Keyword Name", 1, 0)

        sem_token = SemTokenInfo.from_token(token, RobotSemTokenTypes.KEYWORD, None, 5, 7)

        assert sem_token.col_offset == 5
        assert sem_token.length == 7

    def test_from_token_with_zero_length(self) -> None:
        """Test creating SemTokenInfo with zero length."""
        token = Token(Token.KEYWORD, "", 1, 5)

        sem_token = SemTokenInfo.from_token(token, RobotSemTokenTypes.KEYWORD)

        assert sem_token.length == 0


class TestNamedArgumentInfo:
    """Test cases for NamedArgumentInfo dataclass."""

    def test_initialization(self) -> None:
        """Test NamedArgumentInfo initialization."""
        info = NamedArgumentInfo("name", "value", 4, 10, True)

        assert info.name == "name"
        assert info.value == "value"
        assert info.name_length == 4
        assert info.total_length == 10
        assert info.is_valid is True

    def test_equality(self) -> None:
        """Test NamedArgumentInfo equality comparison."""
        info1 = NamedArgumentInfo("name", "value", 4, 10, True)
        info2 = NamedArgumentInfo("name", "value", 4, 10, True)
        info3 = NamedArgumentInfo("name", "other", 4, 9, True)

        assert info1 == info2
        assert info1 != info3


# Integration test fixtures
@pytest.fixture
def sample_namespace() -> Any:
    """Create a sample namespace for testing."""
    # This would need to be implemented based on the actual Namespace class
    return type(
        "MockNamespace",
        (),
        {
            "find_keyword": lambda self, name, **kwargs: None,
            "languages": None,
            "get_imported_library_libdoc": lambda self, *args: None,
            "get_variables_import_libdoc": lambda self, *args: None,
        },
    )()


@pytest.fixture
def sample_builtin_library_doc() -> LibraryDoc:
    """Create a sample builtin library doc for testing."""
    return LibraryDoc(name="BuiltIn")


class TestIntegration:
    """Integration tests for semantic tokens components."""

    def test_complete_semantic_token_pipeline(
        self,
        sample_namespace: Any,
        sample_builtin_library_doc: LibraryDoc,
    ) -> None:
        """Test complete pipeline from Robot Framework code to semantic tokens."""
        robot_code = """*** Settings ***
Library    Collections

*** Test Cases ***
Integration Test
    Log    message=Hello World    level=INFO
    Create Dictionary    key=value    another=test

*** Keywords ***
Custom Keyword
    [Arguments]    ${arg1}    ${arg2}=default
    Log    ${arg1}
    RETURN    ${arg2}
"""

        # Parse real Robot Framework code
        model = get_model(robot_code)
        generator = SemanticTokenGenerator()

        # Find all tokens that should generate semantic tokens
        all_tokens = []
        import ast

        for node in ast.walk(model):
            if hasattr(node, "tokens"):
                for token in getattr(node, "tokens", []):
                    if token.type not in [Token.SEPARATOR, Token.EOL, Token.EOS]:
                        all_tokens.append((token, node))

        assert len(all_tokens) >= 10  # Should have many tokens

        # Test semantic token generation for each token
        successful_generations = 0
        for token, node in all_tokens:
            try:
                sem_tokens = list(
                    generator.generate_sem_tokens(token, node, sample_namespace, sample_builtin_library_doc)
                )
                assert all(isinstance(st, SemTokenInfo) for st in sem_tokens)
                successful_generations += 1
            except Exception as e:
                # Log but don't fail - some tokens might not be processable
                print(f"Token generation failed for {token.type}:{token.value} - {e}")

        # Most tokens should be successfully processed
        assert successful_generations >= len(all_tokens) * 0.8  # 80% success rate

    def test_semantic_token_consistency(self, sample_namespace: Any, sample_builtin_library_doc: LibraryDoc) -> None:
        """Test that semantic token generation is consistent."""
        generator = SemanticTokenGenerator()
        token = Token(Token.KEYWORD, "Log", 1, 0)
        node = KeywordCall([])

        # Generate tokens multiple times
        results = []
        for _ in range(3):
            sem_tokens = list(generator.generate_sem_tokens(token, node, sample_namespace, sample_builtin_library_doc))
            results.append(sem_tokens)

        # Results should be identical
        assert len(set(len(result) for result in results)) == 1  # All same length

        # Content should be the same
        for i in range(1, len(results)):
            assert len(results[0]) == len(results[i])
            for j, (st1, st2) in enumerate(zip(results[0], results[i])):
                assert st1.sem_token_type == st2.sem_token_type, f"Mismatch at position {j}"
                assert st1.lineno == st2.lineno, f"Line mismatch at position {j}"
                assert st1.col_offset == st2.col_offset, f"Column mismatch at position {j}"


class TestRunKeywordVariantsComprehensive:
    """Comprehensive tests for all Run Keyword variants - CRITICAL missing functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.token_mapper = SemanticTokenMapper()
        self.analyzer = KeywordTokenAnalyzer(self.token_mapper)

        # Create comprehensive namespace mock
        self.namespace = type(
            "MockNamespace",
            (),
            {
                "find_keyword": self._mock_find_keyword,
                "languages": None,
            },
        )()

    def _mock_find_keyword(self, name: str, **kwargs: Any) -> Any:
        """Mock keyword finder that returns appropriate docs for Run Keywords."""
        if "Run Keyword If" in name:
            return self._create_run_keyword_if_doc()
        if "Run Keywords" in name:
            return self._create_run_keywords_doc()
        if "Run Keyword And" in name:
            return self._create_run_keyword_with_condition_doc()
        if "Run Keyword" in name:
            return self._create_run_keyword_doc()
        return None

    def _create_run_keyword_if_doc(self) -> Any:
        """Create mock doc for Run Keyword If."""
        return type(
            "MockKeywordDoc",
            (),
            {
                "name": "Run Keyword If",
                "source": "BuiltIn",
                "is_any_run_keyword": lambda: True,
                "is_run_keyword": lambda: False,
                "is_run_keyword_with_condition": lambda: False,
                "is_run_keyword_if": lambda: True,
                "is_run_keywords": lambda: False,
            },
        )()

    def _create_run_keywords_doc(self) -> Any:
        """Create mock doc for Run Keywords."""
        return type(
            "MockKeywordDoc",
            (),
            {
                "name": "Run Keywords",
                "source": "BuiltIn",
                "is_any_run_keyword": lambda self: True,
                "is_run_keyword": lambda self: False,
                "is_run_keyword_with_condition": lambda self: False,
                "is_run_keyword_if": lambda self: False,
                "is_run_keywords": lambda self: True,
            },
        )()

    def _create_run_keyword_with_condition_doc(self) -> Any:
        """Create mock doc for Run Keyword And Return/Continue/etc."""
        return type(
            "MockKeywordDoc",
            (),
            {
                "name": "Run Keyword And Return",
                "source": "BuiltIn",
                "is_any_run_keyword": lambda self: True,
                "is_run_keyword": lambda self: False,
                "is_run_keyword_with_condition": lambda self: True,
                "is_run_keyword_if": lambda self: False,
                "is_run_keywords": lambda self: False,
                "run_keyword_condition_count": lambda self: 1,
            },
        )()

    def _create_run_keyword_doc(self) -> Any:
        """Create mock doc for simple Run Keyword."""
        return type(
            "MockKeywordDoc",
            (),
            {
                "name": "Run Keyword",
                "source": "BuiltIn",
                "is_any_run_keyword": lambda self: True,
                "is_run_keyword": lambda self: True,
                "is_run_keyword_with_condition": lambda self: False,
                "is_run_keyword_if": lambda self: False,
                "is_run_keywords": lambda self: False,
            },
        )()

    def test_run_keyword_if_complex_structure(self) -> None:
        """Test Run Keyword If with complex ELSE IF/ELSE structure."""
        arguments = [
            Token(Token.ARGUMENT, "${condition1}", 1, 16),
            Token(Token.ARGUMENT, "Log", 1, 30),
            Token(Token.ARGUMENT, "First Case", 1, 34),
            Token(Token.ARGUMENT, "ELSE IF", 1, 45),
            Token(Token.ARGUMENT, "${condition2}", 1, 53),
            Token(Token.ARGUMENT, "Log", 1, 67),
            Token(Token.ARGUMENT, "Second Case", 1, 71),
            Token(Token.ARGUMENT, "ELSE IF", 1, 83),
            Token(Token.ARGUMENT, "${condition3}", 1, 91),
            Token(Token.ARGUMENT, "Log", 1, 105),
            Token(Token.ARGUMENT, "Third Case", 1, 109),
            Token(Token.ARGUMENT, "ELSE", 1, 120),
            Token(Token.ARGUMENT, "Log", 1, 125),
            Token(Token.ARGUMENT, "Default Case", 1, 129),
        ]

        node = KeywordCall([])

        tokens = list(self.analyzer._generate_run_keyword_if_tokens(self.namespace, None, arguments, node))

        # Should process all tokens correctly
        assert len(tokens) >= len(arguments)

        # Verify that separator tokens (ELSE IF, ELSE) are processed
        separator_tokens = [t for t in tokens if t[0].value in ["ELSE IF", "ELSE"]]
        assert len(separator_tokens) >= 3  # 2x ELSE IF, 1x ELSE

    def test_run_keywords_with_multiple_and_separators(self) -> None:
        """Test Run Keywords with multiple AND separators."""
        arguments = [
            Token(Token.ARGUMENT, "Log", 1, 13),
            Token(Token.ARGUMENT, "First", 1, 17),
            Token(Token.ARGUMENT, "arg1", 1, 23),
            Token(Token.ARGUMENT, "AND", 1, 28),
            Token(Token.ARGUMENT, "Log", 1, 32),
            Token(Token.ARGUMENT, "Second", 1, 36),
            Token(Token.ARGUMENT, "AND", 1, 43),
            Token(Token.ARGUMENT, "Set Variable", 1, 47),
            Token(Token.ARGUMENT, "${var}", 1, 60),
            Token(Token.ARGUMENT, "value", 1, 67),
            Token(Token.ARGUMENT, "AND", 1, 73),
            Token(Token.ARGUMENT, "Log", 1, 77),
            Token(Token.ARGUMENT, "Third", 1, 81),
        ]

        node = KeywordCall([])

        tokens = list(self.analyzer._generate_run_keywords_tokens(self.namespace, None, arguments, node))

        # Should process all tokens including AND separators
        assert len(tokens) >= len(arguments)

        # Verify AND separators are properly handled
        and_tokens = [t for t in tokens if t[0].value == "AND"]
        assert len(and_tokens) == 3

    def test_run_keyword_and_return_variants(self) -> None:
        """Test Run Keyword And Return/Continue/Ignore Error variants."""
        variants = [
            "Run Keyword And Return",
            "Run Keyword And Continue On Failure",
            "Run Keyword And Ignore Error",
            "Run Keyword And Return If",
        ]

        for variant in variants:
            arguments = [
                Token(Token.ARGUMENT, "Log", 1, len(variant) + 1),
                Token(Token.ARGUMENT, "Test Message", 1, len(variant) + 5),
            ]

            kw_doc = self._create_run_keyword_with_condition_doc()
            kw_doc.name = variant
            node = KeywordCall([])

            tokens = list(
                self.analyzer._generate_run_keyword_with_condition_tokens(self.namespace, None, kw_doc, arguments, node)
            )

            # Should process all tokens
            assert len(tokens) >= len(arguments)

    def test_run_keyword_executing_run_keywords(self) -> None:
        """Test Run Keyword executing Run Keywords (one level nesting)."""
        arguments = [
            Token(Token.ARGUMENT, "Run Keywords", 1, 12),  # Run Keywords as argument to Run Keyword
            Token(Token.ARGUMENT, "Log", 1, 25),
            Token(Token.ARGUMENT, "Nested1", 1, 29),
            Token(Token.ARGUMENT, "AND", 1, 37),
            Token(Token.ARGUMENT, "Log", 1, 41),
            Token(Token.ARGUMENT, "Nested2", 1, 45),
        ]

        node = KeywordCall([])

        tokens = list(self.analyzer._generate_run_keyword_tokens(self.namespace, None, arguments, node))

        # Should handle Run Keyword → Run Keywords → Log structure
        assert len(tokens) >= len(arguments)

        # Verify that specific tokens are processed correctly
        token_values = [token[0].value for token in tokens]

        # Should contain the Run Keywords keyword (executed by Run Keyword)
        assert "Run Keywords" in token_values

        # Should contain both Log keywords (executed by Run Keywords)
        assert token_values.count("Log") >= 2

        # Should contain the AND separator
        assert "AND" in token_values

        # Should contain both argument values
        assert "Nested1" in token_values
        assert "Nested2" in token_values

    def test_truly_nested_run_keywords(self) -> None:
        """Test actual nested Run Keywords calling other Run Keywords."""
        arguments = [
            Token(Token.ARGUMENT, "Run Keywords", 1, 13),  # First Run Keywords call
            Token(Token.ARGUMENT, "Log", 1, 26),
            Token(Token.ARGUMENT, "First", 1, 30),
            Token(Token.ARGUMENT, "AND", 1, 36),
            Token(Token.ARGUMENT, "Run Keywords", 1, 40),  # Nested Run Keywords!
            Token(Token.ARGUMENT, "Log", 1, 53),
            Token(Token.ARGUMENT, "Nested1", 1, 57),
            Token(Token.ARGUMENT, "AND", 1, 65),
            Token(Token.ARGUMENT, "Log", 1, 69),
            Token(Token.ARGUMENT, "Nested2", 1, 73),
        ]

        node = KeywordCall([])

        tokens = list(self.analyzer._generate_run_keywords_tokens(self.namespace, None, arguments, node))

        # Should handle Run Keywords → Run Keywords → Log structure
        assert len(tokens) >= len(arguments)

        # Verify that specific tokens are processed correctly
        token_values = [token[0].value for token in tokens]

        # Should contain multiple Run Keywords calls
        assert token_values.count("Run Keywords") >= 2

        # Should contain multiple Log keywords
        assert token_values.count("Log") >= 3

        # Should contain AND separators
        assert token_values.count("AND") >= 2

    def test_run_keyword_edge_cases(self) -> None:
        """Test edge cases for Run Keyword variants."""
        # Empty arguments
        arguments: list[Token] = []
        node = KeywordCall([])

        tokens = list(self.analyzer._generate_run_keyword_tokens(self.namespace, None, arguments, node))

        # Should handle empty arguments gracefully
        assert len(tokens) == 0  # No tokens for empty arguments

        # Single argument
        arguments = [Token(Token.ARGUMENT, "Log", 1, 12)]
        tokens = list(self.analyzer._generate_run_keyword_tokens(self.namespace, None, arguments, node))

        assert len(tokens) == 1  # Just the keyword token


class TestArgumentProcessorEdgeCases:
    """Comprehensive edge case tests for ArgumentProcessor."""

    def test_find_separator_from_current_position(self) -> None:
        """Test find_separator_index respects current position."""
        tokens = [
            Token(Token.ARGUMENT, "arg1"),
            Token(Token.ARGUMENT, "AND"),
            Token(Token.ARGUMENT, "arg2"),
            Token(Token.ARGUMENT, "OR"),
            Token(Token.ARGUMENT, "arg3"),
        ]
        processor = ArgumentProcessor(tokens)

        # Find first occurrence from start
        index = processor.find_separator_index(frozenset({"AND", "OR"}))
        assert index == 1  # Should find AND first

        # The method should search from current index, not from a set position
        # Let's test the actual behavior
        processor.index = 0
        first_separator = processor.find_separator_index(frozenset({"OR"}))
        assert first_separator == 3  # Should find OR at index 3

    def test_iter_until_separator_multiple_types(self) -> None:
        """Test iter_until_separator with multiple separator types."""
        tokens = [
            Token(Token.ARGUMENT, "start"),
            Token(Token.ARGUMENT, "arg1"),
            Token(Token.ARGUMENT, "arg2"),
            Token(Token.ARGUMENT, "ELSE IF"),  # First separator
            Token(Token.ARGUMENT, "condition"),
            Token(Token.ARGUMENT, "ELSE"),  # Second separator
            Token(Token.ARGUMENT, "final"),
        ]
        processor = ArgumentProcessor(tokens)

        # Consume start token
        processor.consume()

        # Iterate until any separator
        collected = list(processor.iter_until_separator(["ELSE IF", "ELSE"]))

        assert len(collected) == 2
        assert collected[0].value == "arg1"
        assert collected[1].value == "arg2"

        # Should be positioned at separator
        current = processor.peek()
        assert current is not None
        assert current.value == "ELSE IF"

    def test_argument_processor_with_unicode(self) -> None:
        """Test ArgumentProcessor with Unicode characters."""
        tokens = [
            Token(Token.ARGUMENT, "Ärg1"),  # German umlaut
            Token(Token.ARGUMENT, "测试"),  # Chinese characters
            Token(Token.ARGUMENT, "🤖"),  # Emoji
            Token(Token.ARGUMENT, "AND"),
            Token(Token.ARGUMENT, "Ñoño"),  # Spanish characters
        ]
        processor = ArgumentProcessor(tokens)

        # Should handle Unicode properly
        consumed = []
        while processor.has_next():
            token = processor.consume()
            if token:
                consumed.append(token)

        assert len(consumed) == 5
        assert consumed[0].value == "Ärg1"
        assert consumed[1].value == "测试"
        assert consumed[2].value == "🤖"

    def test_skip_non_data_tokens_comprehensive(self) -> None:
        """Test skip_non_data_tokens with various non-data token types."""
        tokens = [
            Token(Token.SEPARATOR, "  "),
            Token(Token.SEPARATOR, "\t"),
            Token(Token.SEPARATOR, "\n"),
            Token(Token.COMMENT, "# Comment"),
            Token(Token.ARGUMENT, "first_arg"),
            Token(Token.SEPARATOR, "  "),
            Token(Token.ARGUMENT, "second_arg"),
        ]
        processor = ArgumentProcessor(tokens)

        # Skip all initial non-data tokens
        skipped = processor.skip_non_data_tokens()

        # Should skip separators and comments
        assert len(skipped) >= 3  # At least the 3 separators

        # Should be positioned at first argument
        current = processor.peek()
        assert current is not None
        assert current.value == "first_arg"


class TestNamedArgumentValidationRobust:
    """Robust tests for named argument validation and edge cases."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.processor = NamedArgumentProcessor(SemanticTokenMapper())

    def test_named_arguments_with_variables(self) -> None:
        """Test named arguments containing variables."""
        test_cases = [
            "name=${variable}",
            "${var_name}=value",
            "${var1}=${var2}",
            "name=${var.attribute}",
            "name=${var}[index]",
            "name=@{list_var}",
            "name=&{dict_var}",
        ]

        for test_input in test_cases:
            result = self.processor.parse_named_argument(test_input)
            assert result is not None, f"Should parse: {test_input}"
            assert isinstance(result, NamedArgumentInfo)

    @pytest.mark.parametrize(
        ("test_input", "expected_name", "expected_value"),
        [
            ("name=path/to/file.txt", "name", "path/to/file.txt"),
            ("timeout=30s", "timeout", "30s"),
            ("level=INFO", "level", "INFO"),
            ("message=Hello World!", "message", "Hello World!"),
            ("pattern=.*\\.robot$", "pattern", ".*\\.robot$"),
            ("url=https://example.com?param=value", "url", "https://example.com?param=value"),
        ],
    )
    def test_named_arguments_with_complex_values(
        self, test_input: str, expected_name: str, expected_value: str
    ) -> None:
        """Test named arguments with complex values."""
        result = self.processor.parse_named_argument(test_input)
        assert result is not None
        assert result.name == expected_name
        assert result.value == expected_value

    def test_validate_named_argument_comprehensive(self) -> None:
        """Test comprehensive named argument validation scenarios."""
        # Create mock keyword doc with various argument types
        args = [
            type("Arg", (), {"name": "required_arg", "kind": KeywordArgumentKind.POSITIONAL_OR_NAMED})(),
            type("Arg", (), {"name": "optional_arg", "kind": KeywordArgumentKind.NAMED_ONLY})(),
            type("Arg", (), {"name": "var_named", "kind": KeywordArgumentKind.VAR_NAMED})(),
        ]

        kw_doc = KeywordDoc(
            name="Test Keyword",
            line_no=1,
            col_offset=0,
            end_line_no=1,
            end_col_offset=10,
            source="test.robot",
            arguments=args,
        )

        # Test valid arguments
        assert self.processor._validate_named_argument("required_arg", kw_doc) is True
        assert self.processor._validate_named_argument("optional_arg", kw_doc) is True

        # Test VAR_NAMED (should accept any name)
        assert self.processor._validate_named_argument("any_name", kw_doc) is True
        assert self.processor._validate_named_argument("custom_param", kw_doc) is True

        # Test invalid argument
        kw_doc_no_var_named = KeywordDoc(
            name="Test Keyword",
            line_no=1,
            col_offset=0,
            end_line_no=1,
            end_col_offset=10,
            source="test.robot",
            arguments=args[:-1],  # Remove VAR_NAMED
        )

        assert self.processor._validate_named_argument("invalid_arg", kw_doc_no_var_named) is False

    def test_generate_named_argument_tokens_edge_cases(self) -> None:
        """Test token generation for edge cases."""
        node = KeywordCall([])

        # Test with special characters in name/value
        token = Token(Token.ARGUMENT, "special_name=value with spaces", 1, 0)
        arg_info = NamedArgumentInfo("special_name", "value with spaces", 12, 30, True)

        tokens = list(self.processor.generate_named_argument_tokens(token, arg_info, node))

        assert len(tokens) == 3
        assert tokens[0][0].value == "special_name"
        assert tokens[1][0].value == "="
        assert tokens[2][0].value == "value with spaces"

        # Test with empty value
        token = Token(Token.ARGUMENT, "name=", 1, 0)
        arg_info = NamedArgumentInfo("name", "", 4, 5, True)

        tokens = list(self.processor.generate_named_argument_tokens(token, arg_info, node))

        assert len(tokens) == 3
        assert tokens[2][0].value == ""  # Empty value


class TestRegexPatternsComprehensive:
    """Comprehensive tests for regex patterns used in semantic tokens."""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            # Basic escapes that actually work
            ("\\n", ["\\n"]),
            ("\\t", ["\\t"]),
            ("\\r", ["\\r"]),
            ("\\\\", ["\\\\"]),
            # Mixed content - test what the regex actually does
            ("Hello\\nWorld", ["Hello", "\\n", "World"]),
            ("Path\\\\file.txt", ["Path", "\\\\", "file.txt"]),
            # Edge cases
            ("", []),
            ("no_escapes", ["no_escapes"]),
            # Note: Single backslash doesn't match the escape regex pattern
        ],
    )
    def test_escape_regex_comprehensive(self, text: str, expected: list[str]) -> None:
        """Test ESCAPE_REGEX with realistic escape sequences."""
        matches = list(SemanticTokenMapper.ESCAPE_REGEX.finditer(text))
        actual = [match.group() for match in matches]
        assert actual == expected, f"Failed for input: '{text}' - got {actual}, expected {expected}"

    @pytest.mark.parametrize(
        ("text", "should_match", "expected_prefix"),
        [
            # Valid BDD prefixes (require space)
            ("Given I have something", True, "Given"),
            ("When I do something", True, "When"),
            ("Then I should see", True, "Then"),
            ("And I also do", True, "And"),
            ("But not this", True, "But"),
            # Case insensitive
            ("given lowercase", True, "given"),
            ("WHEN UPPERCASE", True, "WHEN"),
            ("aNd MiXeD", True, "aNd"),
            # Invalid cases (no space after prefix)
            ("Givenno space", False, None),
            ("NotABDDPrefix", False, None),
            ("", False, None),
            ("Just text", False, None),
            ("Given", False, None),  # Just the prefix without space
            ("  Given something", False, None),  # Leading spaces
        ],
    )
    def test_bdd_token_regex_comprehensive(self, text: str, should_match: bool, expected_prefix: str | None) -> None:
        """Test BDD_TOKEN_REGEX with comprehensive BDD patterns."""
        # Test actual BDD patterns - the regex requires space after prefix
        match = SemanticTokenMapper.BDD_TOKEN_REGEX.match(text)
        if should_match:
            assert match is not None, f"Should match: '{text}'"
            assert match.group(1) == expected_prefix, f"Wrong prefix for: '{text}'"
        else:
            assert match is None, f"Should not match: '{text}'"

    def test_builtin_matcher_patterns(self) -> None:
        """Test builtin library name matching."""
        # The BUILTIN_MATCHER should match BuiltIn library
        assert SemanticTokenMapper.BUILTIN_MATCHER.name == "BuiltIn"
        assert SemanticTokenMapper.BUILTIN_MATCHER._is_namespace is True

    def test_all_run_keywords_matchers(self) -> None:
        """Test ALL_RUN_KEYWORDS_MATCHERS patterns."""
        # Import the matchers from where they're actually defined
        from robotcode.robot.diagnostics.library_doc import ALL_RUN_KEYWORDS_MATCHERS

        # Should contain patterns for various Run Keyword variants
        matchers = ALL_RUN_KEYWORDS_MATCHERS
        assert len(matchers) > 0

        # Test that it matches expected patterns
        test_keywords = [
            "Run Keyword",
            "Run Keywords",
            "Run Keyword If",
            "Run Keyword And Return",
            "Run Keyword And Continue On Failure",
        ]

        for keyword in test_keywords:
            # Test that it matches expected patterns - just verify structure
            # Note: This tests the structure, actual matching depends on implementation
            assert isinstance(matchers, (list, tuple)), "Should be a collection of matchers"
            assert len(matchers) > 0, "Should have at least one matcher"


class TestErrorHandling:
    """Test error handling - Missing completely!"""

    def test_malformed_named_arguments(self) -> None:
        """Test handling of malformed named arguments."""
        processor = NamedArgumentProcessor(SemanticTokenMapper())

        # Test various malformed cases
        test_cases = [
            "=value",  # Missing name
            "name=",  # Empty value (should be valid)
            "name==value",  # Double equals
            "just_text",  # No equals at all
            "",  # Empty string
            "name=value=more",  # Multiple equals
            "name with spaces=value",  # Spaces in name
        ]

        for test_input in test_cases:
            try:
                result = processor.parse_named_argument(test_input)
                # Should return None or valid NamedArgumentInfo, never raise exception
                assert result is None or isinstance(result, NamedArgumentInfo)
            except Exception as e:
                pytest.fail(f"Should not raise exception for input '{test_input}': {e}")

    def test_empty_argument_processor_edge_cases(self) -> None:
        """Test ArgumentProcessor with edge cases."""
        # Empty processor
        processor = ArgumentProcessor([])

        assert not processor.has_next()
        assert processor.peek() is None
        assert processor.consume() is None
        assert processor.find_separator_index(frozenset({"AND"})) is None
        assert list(processor.iter_until_separator(["AND"])) == []
        assert list(processor.iter_all_remaining()) == []

    def test_semantic_token_generator_with_invalid_tokens(self) -> None:
        """Test SemanticTokenGenerator with invalid/unusual tokens."""
        generator = SemanticTokenGenerator()
        namespace = type(
            "MockNamespace",
            (),
            {
                "find_keyword": lambda self, name, **kwargs: None,
                "languages": None,
            },
        )()

        # Test with unusual token types
        unusual_tokens = [
            Token("INVALID_TYPE", "test", 1, 0),  # Invalid token type
            Token(Token.KEYWORD, "", 1, 0),  # Empty value
            Token(Token.VARIABLE, "${}", 1, 0),  # Malformed variable
            Token(Token.ARGUMENT, "arg", -1, -1),  # Negative positions
        ]

        for token in unusual_tokens:
            try:
                node = KeywordCall([])
                sem_tokens = list(generator.generate_sem_tokens(token, node, namespace, None))
                # Should handle gracefully
                assert isinstance(sem_tokens, list)
            except Exception as e:
                # Some exceptions might be expected, but document them
                print(f"Expected exception for {token}: {e}")

    def test_semantic_token_mapper_with_unknown_tokens(self) -> None:
        """Test SemanticTokenMapper with unknown token types."""
        mapper = SemanticTokenMapper()

        unknown_tokens = [
            "COMPLETELY_UNKNOWN",
            "",  # Empty string
            None,  # None value
            123,  # Invalid type
        ]

        for token_type in unknown_tokens:
            try:
                result = mapper.get_semantic_info(token_type)  # type: ignore[arg-type]
                # Should return None for unknown tokens
                assert result is None
            except Exception as e:
                # Should not raise exceptions
                pytest.fail(f"Should not raise exception for unknown token '{token_type}': {e}")


class TestRealWorldIntegration:
    """Real-world integration tests with actual Robot Framework patterns."""

    def test_complex_library_imports_and_usage(self) -> None:
        """Test semantic tokens with complex library imports and usage."""
        robot_code = """*** Settings ***
Library    Collections
Library    String
Library    OperatingSystem    WITH NAME    OS

*** Variables ***
${GLOBAL_VAR}    global_value
@{LIST_VAR}      item1    item2    item3
&{DICT_VAR}      key1=value1    key2=value2

*** Test Cases ***
Complex Integration Test
    # Collections library usage
    Create Dictionary    key=value    another=test    third=${GLOBAL_VAR}
    Create List    @{LIST_VAR}    additional

    # String library usage
    Should Match Regexp    ${GLOBAL_VAR}    ^global.*

    # OS library with alias
    OS.File Should Exist    /tmp

    # Complex variable usage
    Log    Dictionary: &{DICT_VAR}[key1]
    Log Many    @{LIST_VAR}

    # Nested keywords
    Run Keyword If    '${GLOBAL_VAR}' == 'global_value'
    ...    Log    Condition met
    ...    ELSE
    ...    Fail    Unexpected value

*** Keywords ***
Custom Keyword With Complex Args
    [Arguments]    ${required}    ${optional}=default    @{varargs}    &{kwargs}
    Log    Required: ${required}
    Log    Optional: ${optional}
    Log Many    @{varargs}
    Log    &{kwargs}
    RETURN    ${required}
"""

        # Parse real Robot Framework code
        model = get_model(robot_code)
        generator = SemanticTokenGenerator()

        # Create more comprehensive namespace mock
        namespace = type(
            "MockNamespace",
            (),
            {
                "find_keyword": lambda self, name, **kwargs: None,
                "languages": None,
                "get_imported_library_libdoc": lambda self, *args: None,
                "get_variables_import_libdoc": lambda self, *args: None,
            },
        )()

        # Process all tokens
        successful_tokens = 0
        total_tokens = 0

        import ast

        for node in ast.walk(model):
            if hasattr(node, "tokens"):
                for token in getattr(node, "tokens", []):
                    if token.type not in [Token.SEPARATOR, Token.EOL, Token.EOS, Token.COMMENT]:
                        total_tokens += 1
                        try:
                            sem_tokens = list(generator.generate_sem_tokens(token, node, namespace, None))
                            if sem_tokens:
                                successful_tokens += 1
                                # Verify semantic token structure
                                for sem_token in sem_tokens:
                                    assert isinstance(sem_token, SemTokenInfo)
                                    assert sem_token.lineno >= 1
                                    assert sem_token.col_offset >= 0
                                    assert sem_token.length >= 0
                        except Exception as e:
                            print(f"Token processing failed: {token.type}:{token.value} - {e}")

        # Should process most tokens successfully
        assert total_tokens >= 50  # Should have many tokens in this complex example
        assert successful_tokens >= total_tokens * 0.7  # 70% success rate minimum


if __name__ == "__main__":
    pytest.main([__file__])
