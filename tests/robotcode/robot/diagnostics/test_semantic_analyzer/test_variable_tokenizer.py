"""Tests for variable_tokenizer sub-token decomposition."""

from robot.parsing.lexer.tokens import Token

from robotcode.robot.diagnostics.semantic_analyzer.enums import TokenKind
from robotcode.robot.diagnostics.semantic_analyzer.nodes import SemanticToken
from robotcode.robot.diagnostics.semantic_analyzer.variable_tokenizer import (
    build_index_sub_tokens,
    build_variable_occurrence,
    build_variable_sub_tokens,
    iter_related_occurrences,
    iter_variable_occurrences_from_token,
    normalize_variable_lookup_name,
)


def _kinds(tokens: list[SemanticToken]) -> list[TokenKind]:
    """Extract token kinds for easy assertion."""
    return [t.kind for t in tokens]


def _values(tokens: list[SemanticToken]) -> list[str]:
    """Extract token values for easy assertion."""
    return [t.value for t in tokens]


# --- Empty / edge cases ---


class TestEdgeCases:
    def test_empty_string(self) -> None:
        assert build_variable_sub_tokens("", 1, 0) == []

    def test_too_short(self) -> None:
        assert build_variable_sub_tokens("$", 1, 0) == []
        assert build_variable_sub_tokens("${", 1, 0) == []

    def test_no_braces(self) -> None:
        assert build_variable_sub_tokens("abc", 1, 0) == []


# --- Simple scalar variable ---


class TestSimpleScalar:
    def test_simple_variable(self) -> None:
        tokens = build_variable_sub_tokens("${name}", 1, 0)
        assert _kinds(tokens) == [
            TokenKind.VARIABLE_PREFIX,
            TokenKind.VARIABLE_OPEN_BRACE,
            TokenKind.VARIABLE_BASE,
            TokenKind.VARIABLE_CLOSE_BRACE,
        ]
        assert _values(tokens) == ["$", "{", "name", "}"]

    def test_col_offsets(self) -> None:
        tokens = build_variable_sub_tokens("${name}", 1, 10)
        assert tokens[0].col_offset == 10  # $
        assert tokens[1].col_offset == 11  # {
        assert tokens[2].col_offset == 12  # name
        assert tokens[3].col_offset == 16  # }

    def test_line_propagated(self) -> None:
        tokens = build_variable_sub_tokens("${x}", 42, 0)
        assert all(t.line == 42 for t in tokens)

    def test_lengths(self) -> None:
        tokens = build_variable_sub_tokens("${name}", 1, 0)
        assert tokens[0].length == 1  # $
        assert tokens[1].length == 1  # {
        assert tokens[2].length == 4  # name
        assert tokens[3].length == 1  # }


# --- List, dict, env variables ---


class TestVariableTypes:
    def test_list_variable(self) -> None:
        tokens = build_variable_sub_tokens("@{items}", 1, 0)
        assert tokens[0].value == "@"
        assert tokens[0].kind == TokenKind.VARIABLE_PREFIX
        assert tokens[2].value == "items"

    def test_dict_variable(self) -> None:
        tokens = build_variable_sub_tokens("&{config}", 1, 0)
        assert tokens[0].value == "&"
        assert tokens[2].value == "config"

    def test_env_variable_simple(self) -> None:
        tokens = build_variable_sub_tokens("%{HOME}", 1, 0)
        assert tokens[0].value == "%"
        assert tokens[2].kind == TokenKind.VARIABLE_BASE
        assert tokens[2].value == "HOME"

    def test_env_variable_with_default(self) -> None:
        tokens = build_variable_sub_tokens("%{HOME=/usr/local}", 1, 0)
        # prefix, open, base, default_sep, default_val, close
        assert _kinds(tokens) == [
            TokenKind.VARIABLE_PREFIX,
            TokenKind.VARIABLE_OPEN_BRACE,
            TokenKind.VARIABLE_BASE,
            TokenKind.VARIABLE_DEFAULT_SEPARATOR,
            TokenKind.VARIABLE_DEFAULT_VALUE,
            TokenKind.VARIABLE_CLOSE_BRACE,
        ]
        assert tokens[2].value == "HOME"
        assert tokens[3].value == "="
        assert tokens[4].value == "/usr/local"

    def test_env_variable_empty_default(self) -> None:
        tokens = build_variable_sub_tokens("%{X=}", 1, 0)
        assert tokens[2].value == "X"
        assert tokens[3].value == "="
        assert tokens[4].value == ""


# --- Type hints ---


class TestTypeHints:
    def test_simple_type_hint(self) -> None:
        tokens = build_variable_sub_tokens("${age: int}", 1, 0)
        inner = tokens[2:-1]  # skip prefix, open, close
        assert _kinds(inner) == [
            TokenKind.VARIABLE_BASE,
            TokenKind.VARIABLE_TYPE_SEPARATOR,
            TokenKind.VARIABLE_TYPE_HINT,
        ]
        assert inner[0].value == "age"
        assert inner[1].value == ": "
        assert inner[2].value == "int"

    def test_type_hint_with_colon_in_hint(self) -> None:
        # RF uses ': ' (colon + space) as the sole type separator. Any ':' that
        # appears inside the type expression itself is NOT a pattern separator —
        # ${name: str:\w+} has 'str:\w+' as the full type hint.
        tokens = build_variable_sub_tokens("${name: str:\\w+}", 1, 0)
        inner = tokens[2:-1]
        assert _kinds(inner) == [
            TokenKind.VARIABLE_BASE,
            TokenKind.VARIABLE_TYPE_SEPARATOR,
            TokenKind.VARIABLE_TYPE_HINT,
        ]
        assert inner[0].value == "name"
        assert inner[1].value == ": "
        assert inner[2].value == "str:\\w+"

    def test_complex_type_hint_with_colon_literal_is_tokenized_correctly(self) -> None:
        # ':' inside a Literal string within the type hint must NOT be treated as a
        # pattern separator. The entire expression after ': ' is the type hint.
        value = '${x: Literal["abc", ":", ";"] | List[Literal[1,2,3]]}'
        tokens = build_variable_sub_tokens(value, 1, 0)
        inner = tokens[2:-1]

        assert _kinds(inner) == [
            TokenKind.VARIABLE_BASE,
            TokenKind.VARIABLE_TYPE_SEPARATOR,
            TokenKind.VARIABLE_TYPE_HINT,
        ]
        assert inner[0].value == "x"
        assert inner[1].value == ": "
        assert inner[2].value == 'Literal["abc", ":", ";"] | List[Literal[1,2,3]]'

    def test_type_hint_with_colon_space_in_literal_is_tokenized_correctly(self) -> None:
        # When ': ' (colon + space) appears inside a Literal string, RF's rsplit-based
        # type parsing gets confused and produces an 'Invalid variable' error at collection
        # time. Our tokenizer correctly splits at the FIRST ': ' (position 1 → base='x'),
        # so the visual representation is as accurate as possible given RF's limitation.
        # The RF parse-time error is already surfaced via Variable.errors diagnostics.
        value = '${x: Literal["abc", ": ", ";"]}'
        tokens = build_variable_sub_tokens(value, 1, 0)
        inner = tokens[2:-1]

        assert _kinds(inner) == [
            TokenKind.VARIABLE_BASE,
            TokenKind.VARIABLE_TYPE_SEPARATOR,
            TokenKind.VARIABLE_TYPE_HINT,
        ]
        assert inner[0].value == "x"
        assert inner[1].value == ": "
        assert inner[2].value == 'Literal["abc", ": ", ";"]'


# --- Embedded patterns ---


class TestEmbeddedPatterns:
    def test_pattern_without_type(self) -> None:
        tokens = build_variable_sub_tokens("${arg:\\d+}", 1, 0)
        inner = tokens[2:-1]
        assert _kinds(inner) == [
            TokenKind.VARIABLE_BASE,
            TokenKind.VARIABLE_PATTERN_SEPARATOR,
            TokenKind.VARIABLE_PATTERN,
        ]
        assert inner[0].value == "arg"
        assert inner[2].value == "\\d+"


# --- Extended syntax ---


class TestExtendedSyntax:
    def test_dot_access(self) -> None:
        tokens = build_variable_sub_tokens("${obj.attr}", 1, 0)
        inner = tokens[2:-1]
        assert _kinds(inner) == [
            TokenKind.VARIABLE_BASE,
            TokenKind.VARIABLE_EXTENDED,
        ]
        assert inner[0].value == "obj"
        assert inner[1].value == ".attr"

    def test_multiply(self) -> None:
        tokens = build_variable_sub_tokens("${SPACE * 4}", 1, 0)
        inner = tokens[2:-1]
        assert inner[0].kind == TokenKind.VARIABLE_BASE
        assert inner[0].value == "SPACE "
        assert inner[1].kind == TokenKind.VARIABLE_EXTENDED
        assert inner[1].value == "* 4"


# --- Assign mark ---


class TestAssignMark:
    def test_assign_mark(self) -> None:
        tokens = build_variable_sub_tokens("${result}=", 1, 0)
        assert tokens[-1].kind == TokenKind.VARIABLE_ASSIGN_MARK
        assert tokens[-1].value == "="
        assert tokens[-1].col_offset == 9

    def test_no_assign_mark(self) -> None:
        tokens = build_variable_sub_tokens("${result}", 1, 0)
        assert tokens[-1].kind == TokenKind.VARIABLE_CLOSE_BRACE


# --- Inline Python expression ---


class TestInlinePython:
    def test_basic_expression(self) -> None:
        tokens = build_variable_sub_tokens("${{1 + 2}}", 1, 0)
        assert _kinds(tokens) == [
            TokenKind.VARIABLE_PREFIX,
            TokenKind.VARIABLE_EXPRESSION_OPEN,
            TokenKind.PYTHON_EXPRESSION,
            TokenKind.VARIABLE_EXPRESSION_CLOSE,
        ]
        assert tokens[1].value == "{{"
        assert tokens[2].value == "1 + 2"
        assert tokens[3].value == "}}"

    def test_expression_offsets(self) -> None:
        tokens = build_variable_sub_tokens("${{expr}}", 1, 5)
        assert tokens[0].col_offset == 5  # $
        assert tokens[1].col_offset == 6  # {{
        assert tokens[2].col_offset == 8  # expr
        assert tokens[3].col_offset == 12  # }}

    def test_expression_with_dollar_var(self) -> None:
        tokens = build_variable_sub_tokens("${{$x + 1}}", 1, 0)
        expr_token = tokens[2]
        assert expr_token.kind == TokenKind.PYTHON_EXPRESSION
        assert expr_token.sub_tokens is not None
        assert len(expr_token.sub_tokens) == 1
        assert expr_token.sub_tokens[0].kind == TokenKind.PYTHON_VARIABLE_REF
        assert expr_token.sub_tokens[0].value == "$x"

    def test_expression_no_dollar_var(self) -> None:
        tokens = build_variable_sub_tokens("${{len('abc')}}", 1, 0)
        expr_token = tokens[2]
        assert expr_token.sub_tokens is None


# --- Nested variables ---


class TestNestedVariables:
    def test_simple_nesting(self) -> None:
        tokens = build_variable_sub_tokens("${cfg_${env}}", 1, 0)
        # prefix, open, [nested content], close
        inner = tokens[2:-1]
        assert len(inner) == 2  # TEXT_FRAGMENT + VARIABLE
        assert inner[0].kind == TokenKind.TEXT_FRAGMENT
        assert inner[0].value == "cfg_"
        assert inner[1].kind == TokenKind.VARIABLE
        assert inner[1].value == "${env}"

    def test_nested_has_sub_tokens(self) -> None:
        tokens = build_variable_sub_tokens("${cfg_${env}}", 1, 0)
        inner = tokens[2:-1]
        nested = inner[1]
        assert nested.sub_tokens is not None
        assert len(nested.sub_tokens) == 4  # prefix, open, base, close
        assert nested.sub_tokens[2].value == "env"

    def test_text_before_and_after(self) -> None:
        tokens = build_variable_sub_tokens("${a${b}c}", 1, 0)
        inner = tokens[2:-1]
        kinds = _kinds(inner)
        assert TokenKind.TEXT_FRAGMENT in kinds
        assert TokenKind.VARIABLE in kinds


# --- Index access ---


class TestIndexAccess:
    def test_single_index(self) -> None:
        tokens = build_variable_sub_tokens("${var}[0]", 1, 0)
        # last token should be VARIABLE_INDEX
        idx = tokens[-1]
        assert idx.kind == TokenKind.VARIABLE_INDEX
        assert idx.value == "[0]"
        assert idx.sub_tokens is not None

    def test_index_sub_tokens(self) -> None:
        tokens = build_variable_sub_tokens("${var}[0]", 1, 0)
        idx = tokens[-1]
        assert idx.sub_tokens is not None
        idx_kinds = _kinds(idx.sub_tokens)
        assert idx_kinds == [
            TokenKind.VARIABLE_INDEX_OPEN,
            TokenKind.VARIABLE_INDEX_CONTENT,
            TokenKind.VARIABLE_INDEX_CLOSE,
        ]
        assert idx.sub_tokens[0].value == "["
        assert idx.sub_tokens[1].value == "0"
        assert idx.sub_tokens[2].value == "]"

    def test_double_index(self) -> None:
        tokens = build_variable_sub_tokens("${var}[0][key]", 1, 0)
        # Should have two VARIABLE_INDEX tokens at the end
        idx_tokens = [t for t in tokens if t.kind == TokenKind.VARIABLE_INDEX]
        assert len(idx_tokens) == 2
        assert idx_tokens[0].value == "[0]"
        assert idx_tokens[1].value == "[key]"

    def test_index_offsets(self) -> None:
        tokens = build_variable_sub_tokens("${var}[0]", 1, 0)
        idx = tokens[-1]
        assert idx.col_offset == 6  # ${var} is 6 chars
        assert idx.length == 3  # [0]


# --- build_index_sub_tokens standalone ---


class TestBuildIndexSubTokens:
    def test_single_bracket(self) -> None:
        tokens = build_index_sub_tokens("[key]", 1, 0)
        assert len(tokens) == 1
        idx = tokens[0]
        assert idx.kind == TokenKind.VARIABLE_INDEX
        assert idx.sub_tokens is not None
        assert len(idx.sub_tokens) == 3

    def test_double_bracket(self) -> None:
        tokens = build_index_sub_tokens("[0][1]", 1, 0)
        assert len(tokens) == 2

    def test_nested_variable_in_index(self) -> None:
        tokens = build_index_sub_tokens("[${idx}]", 1, 0)
        assert len(tokens) == 1
        idx = tokens[0]
        assert idx.sub_tokens is not None
        # open, nested variable, close
        kinds = _kinds(idx.sub_tokens)
        assert TokenKind.VARIABLE_INDEX_OPEN in kinds
        assert TokenKind.VARIABLE in kinds or TokenKind.TEXT_FRAGMENT in kinds
        assert TokenKind.VARIABLE_INDEX_CLOSE in kinds

    def test_offsets(self) -> None:
        tokens = build_index_sub_tokens("[key]", 1, 10)
        assert tokens[0].col_offset == 10
        assert tokens[0].sub_tokens is not None
        assert tokens[0].sub_tokens[0].col_offset == 10  # [
        assert tokens[0].sub_tokens[1].col_offset == 11  # key
        assert tokens[0].sub_tokens[2].col_offset == 14  # ]

    def test_empty_index(self) -> None:
        tokens = build_index_sub_tokens("[]", 1, 0)
        assert len(tokens) == 1
        idx = tokens[0]
        assert idx.sub_tokens is not None
        # open, empty content, close
        content = [t for t in idx.sub_tokens if t.kind == TokenKind.VARIABLE_INDEX_CONTENT]
        assert len(content) == 1
        assert content[0].value == ""


# --- Coverage completeness ---


class TestCoverageCompleteness:
    """Ensure all token kinds produced by variable_tokenizer can actually appear."""

    def test_all_variable_prefix_chars(self) -> None:
        for prefix in ("$", "@", "&", "%"):
            tokens = build_variable_sub_tokens(f"{prefix}{{x}}", 1, 0)
            assert tokens[0].kind == TokenKind.VARIABLE_PREFIX
            assert tokens[0].value == prefix

    def test_full_coverage_of_env_with_default(self) -> None:
        """Ensure env variable with long default works correctly."""
        tokens = build_variable_sub_tokens("%{DATABASE_URL=postgres://localhost:5432/db}", 1, 0)
        base = next(t for t in tokens if t.kind == TokenKind.VARIABLE_BASE)
        default = next(t for t in tokens if t.kind == TokenKind.VARIABLE_DEFAULT_VALUE)
        assert base.value == "DATABASE_URL"
        assert default.value == "postgres://localhost:5432/db"


# --- VariableOccurrence IR ---


class TestLookupNormalization:
    def test_simple_variable(self) -> None:
        assert normalize_variable_lookup_name("${name}") == "${name}"

    def test_builtin_path_separator_variable(self) -> None:
        assert normalize_variable_lookup_name("${:}") == "${:}"

    def test_extended_variable(self) -> None:
        assert normalize_variable_lookup_name("${obj.attr}") == "${obj}"

    def test_index_variable(self) -> None:
        assert normalize_variable_lookup_name("${items}[0][name]") == "${items}"

    def test_env_default_variable(self) -> None:
        assert normalize_variable_lookup_name("%{HOME=/tmp}") == "%{HOME}"

    def test_type_hint_variable(self) -> None:
        # In reference contexts (parse_type=False, the default), RF does NOT strip the type hint.
        # Only declaration contexts (Variables section, [Arguments], VAR, FOR, Assignment) use
        # parse_type=True, mirroring Robot Framework's own search_variable(parse_type=True) behavior.
        assert normalize_variable_lookup_name("${age: int}") == "${age: int}"
        assert normalize_variable_lookup_name("${age: int}", parse_type=True) == "${age}"

    def test_complex_type_hint_variable(self) -> None:
        value = '${x: Literal["abc", ":", ";"] | List[Literal[1,2,3]]}'
        assert normalize_variable_lookup_name(value) == value
        assert normalize_variable_lookup_name(value, parse_type=True) == "${x}"

    def test_pattern_variable(self) -> None:
        assert normalize_variable_lookup_name("${arg:\\d+}") == "${arg}"

    def test_nested_variable_returns_none(self) -> None:
        assert normalize_variable_lookup_name("${cfg_${env}}") is None

    def test_inline_python_returns_none(self) -> None:
        assert normalize_variable_lookup_name("${{1 + 2}}") is None

    def test_unbalanced_variable_returns_none(self) -> None:
        assert normalize_variable_lookup_name("${name") is None

    def test_extended_with_index_variable(self) -> None:
        assert normalize_variable_lookup_name("${obj.attr}[0]") == "${obj}"

    def test_multiple_index_chain_variable(self) -> None:
        assert normalize_variable_lookup_name("${items}[0][sub][1]") == "${items}"


class TestVariableOccurrenceBuild:
    def test_build_occurrence_contains_lookup_and_sub_tokens(self) -> None:
        occ = build_variable_occurrence("${obj.attr}", 3, 8)
        assert occ.value == "${obj.attr}"
        assert occ.lookup_name == "${obj}"
        assert occ.line == 3
        assert occ.col_offset == 8
        assert occ.length == len("${obj.attr}")
        assert occ.semantic_sub_tokens is not None

    def test_occurrence_for_expression_has_no_lookup(self) -> None:
        occ = build_variable_occurrence("${{$base + 1}}", 2, 1)
        assert occ.lookup_name is None
        assert occ.semantic_sub_tokens is not None


class TestRelatedOccurrences:
    def test_nested_occurrences_are_extracted(self) -> None:
        occ = build_variable_occurrence("${cfg_${env}}", 1, 0)
        related = list(iter_related_occurrences(occ))
        values = [r.value for r in related]
        lookups = [r.lookup_name for r in related]

        assert "${cfg_${env}}" in values
        assert "${env}" in values
        assert "${env}" in lookups

    def test_python_variable_refs_are_extracted(self) -> None:
        occ = build_variable_occurrence("${{$base + $other}}", 1, 0)
        related = list(iter_related_occurrences(occ))
        lookups = [r.lookup_name for r in related if r.lookup_name is not None]

        assert "${base}" in lookups
        assert "${other}" in lookups

    def test_related_occurrence_for_python_ref_does_not_strip(self) -> None:
        occ = build_variable_occurrence("${{$base}}", 1, 0)
        related = list(iter_related_occurrences(occ))
        python_refs = [r for r in related if r.lookup_name == "${base}"]

        assert len(python_refs) == 1
        assert python_refs[0].strip_for_reference is False

    def test_multiple_python_variable_refs_are_all_extracted(self) -> None:
        occ = build_variable_occurrence("${{$a + $b + func($c)}}", 1, 0)
        related = list(iter_related_occurrences(occ))
        lookups = [r.lookup_name for r in related if r.lookup_name is not None]

        assert "${a}" in lookups
        assert "${b}" in lookups
        assert "${c}" in lookups

    def test_unbalanced_nested_content_does_not_crash(self) -> None:
        occ = build_variable_occurrence("${cfg_${env}", 1, 0)
        related = list(iter_related_occurrences(occ))
        assert len(related) >= 1


class TestTokenToOccurrences:
    def test_occurrences_from_argument_token_include_nested(self) -> None:
        token = Token(Token.ARGUMENT, "${cfg_${env}}", 3, 4)
        occ = list(iter_variable_occurrences_from_token(token, ignore_errors=True))

        values = [o.value for o in occ]
        assert "${cfg_${env}}" in values
        assert "${env}" in values

    def test_occurrences_from_expression_include_python_refs(self) -> None:
        token = Token(Token.ARGUMENT, "${{$a + $b}}", 4, 2)
        occ = list(iter_variable_occurrences_from_token(token, ignore_errors=True))
        lookups = [o.lookup_name for o in occ if o.lookup_name is not None]

        assert "${a}" in lookups
        assert "${b}" in lookups

    def test_variable_assign_mark_token_is_normalized(self) -> None:
        token = Token(Token.VARIABLE, "${x}=", 5, 1)
        occ = list(iter_variable_occurrences_from_token(token, ignore_errors=True))

        assert len(occ) == 1
        assert occ[0].value == "${x}"

    def test_declaration_occurrence_strips_type_when_enabled(self) -> None:
        token = Token(Token.VARIABLE, "${age: int}", 6, 2)

        reference_occurrences = list(iter_variable_occurrences_from_token(token, ignore_errors=True))
        declaration_occurrences = list(iter_variable_occurrences_from_token(token, ignore_errors=True, parse_type=True))

        assert reference_occurrences[0].lookup_name == "${age: int}"
        assert declaration_occurrences[0].lookup_name == "${age}"
