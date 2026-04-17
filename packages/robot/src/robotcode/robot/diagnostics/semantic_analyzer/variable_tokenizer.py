"""Variable tokenizer for sub-token decomposition.

Decomposes variable expressions into granular sub-tokens for the Semantic Model.
Handles all 15 variable forms supported by Robot Framework (scalars, lists, dicts,
environment, extended syntax, index access, type hints, inline Python, nested, etc.).

Does NOT delegate to ModelHelper - implements variable tokenization from scratch
using RF's search_variable(), VariableMatch, and tokenize_variables() directly.
"""

import re
import token as python_token
from dataclasses import dataclass
from io import StringIO
from tokenize import TokenError, generate_tokens
from typing import Callable, Iterator, List, Optional, Set, Tuple

from robot.errors import VariableError
from robot.parsing.lexer.tokens import Token

from ...utils.ast import tokenize_variables
from ...utils.variables import search_variable
from .enums import TokenKind
from .nodes import SemanticToken

# Extended variable syntax: ${obj.attr}, ${SPACE * 5}
_MATCH_EXTENDED = re.compile(
    r"""
    (.+?)          # base name (group 1)
    ([^\s\w].+)    # extended part (group 2)
    """,
    re.UNICODE | re.VERBOSE,
)


@dataclass(slots=True)
class VariableOccurrence:
    """Parsed variable occurrence used as shared IR for analysis and rendering.

    `lookup_name` is the normalized variable name used for static resolution
    (for example `${obj.attr}` -> `${obj}`).
    """

    value: str
    line: int
    col_offset: int
    length: int
    lookup_name: Optional[str]
    semantic_sub_tokens: Optional[List[SemanticToken]] = None
    strip_for_reference: bool = True


def build_variable_occurrence(
    value: str, line: int, col_offset: int, *, parse_type: bool = False
) -> VariableOccurrence:
    """Parse a single variable expression once and return shared occurrence data."""
    sub_tokens = build_variable_sub_tokens(value, line, col_offset)
    return VariableOccurrence(
        value=value,
        line=line,
        col_offset=col_offset,
        length=len(value),
        lookup_name=normalize_variable_lookup_name(value, parse_type=parse_type),
        semantic_sub_tokens=sub_tokens if sub_tokens else None,
    )


def split_variable_token_index_access(token: Token) -> Tuple[Optional[Token], Optional[Token]]:
    """Split index access from variable token.

    Examples:
    - ``${var}[0]`` -> (``${var}``, ``[0]``)
    - ``${var}`` -> (original token, None)
    """

    def escaped(i: int) -> bool:
        return bool(token.value[-i - 3 : -i - 2] == "\\")

    if token.type != Token.VARIABLE or not token.value.endswith("]"):
        return (token, None)

    braces = 1
    curly_braces = 0
    index = 0
    for i, c in enumerate(reversed(token.value[:-1])):
        if c == "}" and not escaped(i):
            curly_braces += 1
        elif c == "{" and not escaped(i):
            curly_braces -= 1
        elif c == "]" and curly_braces == 0 and not escaped(i):
            braces += 1
            if braces == 0:
                index = i
        elif c == "[" and curly_braces == 0 and not escaped(i):
            braces -= 1
            if braces == 0:
                index = i

    if braces != 0 or curly_braces != 0:
        return (token, None)

    value = token.value[: -index - 2]
    var = Token(token.type, value, token.lineno, token.col_offset, token.error) if len(value) > 0 else None
    rest = Token(
        Token.ARGUMENT,
        token.value[-index - 2 :],
        token.lineno,
        token.col_offset + len(value),
        token.error,
    )

    return (var, rest)


def iter_variable_tokens_with_index_access(
    token: Token,
    identifiers: str = "$@&%",
    ignore_errors: bool = False,
    *,
    extra_types: Optional[Set[str]] = None,
    exception_handler: Optional[Callable[[Exception, Token], None]] = None,
) -> Iterator[Token]:
    """Tokenize variables and split trailing index access into separate tokens."""
    if exception_handler is not None:
        ignore_errors = False
    try:
        for t in tokenize_variables(token, identifiers, ignore_errors, extra_types=extra_types):
            if t.type == Token.VARIABLE:
                var, rest = split_variable_token_index_access(t)
                if var is not None:
                    yield var
                if rest is not None:
                    yield from iter_variable_tokens_with_index_access(
                        rest,
                        identifiers,
                        ignore_errors,
                        extra_types=extra_types,
                    )
            else:
                yield t
    except VariableError as e:
        if exception_handler is not None:
            exception_handler(e, token)
        elif not ignore_errors:
            raise


def iter_related_occurrences(occurrence: VariableOccurrence) -> Iterator[VariableOccurrence]:
    """Yield the occurrence itself plus nested and Python-expression references."""
    yield occurrence
    if not occurrence.semantic_sub_tokens:
        return

    for sub in occurrence.semantic_sub_tokens:
        yield from _iter_related_occurrences_from_token(sub, occurrence)


def iter_variable_occurrences_from_token(
    token: Token,
    identifiers: str = "$@&%",
    *,
    parse_type: bool = False,
    ignore_errors: bool = False,
    extra_types: Optional[Set[str]] = None,
    exception_handler: Optional[Callable[[Exception, Token], None]] = None,
) -> Iterator[VariableOccurrence]:
    """Parse a token once and yield all variable occurrences (root + related).

    This is the shared entry point for analyzer-side variable resolution and
    model-side variable rendering consumers.
    """
    parsed_token = token
    if token.type == Token.VARIABLE and token.value.endswith("="):
        match = search_variable(token.value, ignore_errors=True, parse_type=parse_type)
        if not match.is_assign(allow_assign_mark=True):
            return

        parsed_token = Token(
            token.type,
            token.value[:-1].strip(),
            token.lineno,
            token.col_offset,
            token.error,
        )

    for sub_token in iter_variable_tokens_with_index_access(
        parsed_token,
        identifiers=identifiers,
        ignore_errors=ignore_errors,
        extra_types=extra_types,
        exception_handler=exception_handler,
    ):
        if sub_token.type != Token.VARIABLE:
            continue

        occurrence = build_variable_occurrence(
            sub_token.value,
            sub_token.lineno,
            sub_token.col_offset,
            parse_type=parse_type,
        )
        yield from iter_related_occurrences(occurrence)


def normalize_variable_lookup_name(value: str, *, parse_type: bool = False) -> Optional[str]:
    """Normalize a variable expression to a lookup name for static resolution.

    Examples:
    - `${obj.attr}` -> `${obj}`
    - `${var}[0][x]` -> `${var}`
    - `%{HOME=default}` -> `%{HOME}`
    - `${{expr}}` -> None
    - `${age: int}` -> `${age}` only when ``parse_type=True`` (declaration context)
    """
    if not value or len(value) < 3:
        return None

    if value.startswith("${{") and value.endswith("}}"):
        return None

    base = value
    while base.endswith("]"):
        start = base.rfind("[")
        if start < 0:
            break
        base = base[:start]

    if len(base) < 3 or base[1] != "{" or "}" not in base:
        return None

    prefix = base[0]
    brace_depth = 0
    brace_end = 2
    while brace_end < len(base):
        if base[brace_end] == "{":
            brace_depth += 1
        elif base[brace_end] == "}":
            if brace_depth == 0:
                break
            brace_depth -= 1
        brace_end += 1

    if brace_end >= len(base):
        return None

    inner = base[2:brace_end]
    if not inner:
        return None

    # Type hint check must precede extended-syntax matching: `: ` in `${age: int}` would
    # otherwise be consumed by _MATCH_EXTENDED (which accepts any [^\s\w] operator) and
    # silently strip the type even in reference contexts.  RF itself only strips the type
    # hint when search_variable() is called with parse_type=True — i.e. in declaration
    # contexts (Variables section, [Arguments], VAR, FOR, Assignment).
    if prefix == "$" and ": " in inner:
        if parse_type:
            inner = inner.split(": ", 1)[0]
        # else: keep inner with type hint intact; the full `${age: int}` is the lookup name.
    else:
        # Try extended syntax first: extract the base variable name before any
        # operator/expression.  This must happen *before* the nested-variable
        # guard because the tail may contain nested variables (e.g.
        # ``${A + '${B}'}``) while the base name ``A`` is perfectly resolvable.
        # Skip when the extension starts with a variable identifier (``${``,
        # ``@{`` etc.) — that indicates a **nested variable name** like
        # ``${cfg_${env}}``, not an expression.
        extended_match = _MATCH_EXTENDED.match(inner)
        if extended_match:
            ext_part = extended_match.group(2)
            if not ext_part.startswith(("${", "@{", "&{", "%{")):
                inner = extended_match.group(1)

    if "${" in inner or "@{" in inner or "&{" in inner or "%{" in inner:
        return None

    if prefix == "%" and "=" in inner:
        inner = inner.split("=", 1)[0]
    elif prefix == "$" and ":" in inner and ": " not in inner:
        # Bare colon: embedded argument pattern ${arg:\d+}.
        # Type hints (`: ` with space) are handled above, gated by parse_type.
        # Preserve builtin ${:}; only treat ':' as pattern separator when both sides exist.
        head, _, tail = inner.partition(":")
        if head and tail:
            inner = head

    inner = inner.strip()
    if not inner:
        return None

    return f"{prefix}{{{inner}}}"


def build_variable_sub_tokens(
    value: str,
    line: int,
    col_offset: int,
) -> List[SemanticToken]:
    """Decompose a variable expression into granular sub-tokens.

    Takes a full variable string like ``${name}``, ``${age: int}``,
    ``${{expr}}``, ``%{HOME=default}``, ``${var}[0]``, etc.
    Returns a list of sub-tokens covering every character.

    Args:
        value: The full variable string including delimiters.
        line: 1-indexed line number.
        col_offset: 0-indexed column offset of the start of the variable.
    """
    if not value or len(value) < 3:
        return []

    prefix_char = value[0]
    tokens: List[SemanticToken] = []

    # Inline Python expression: ${{expr}}
    if value.startswith("${{") and value.endswith("}}"):
        tokens.append(
            SemanticToken(
                kind=TokenKind.VARIABLE_PREFIX,
                value=prefix_char,
                line=line,
                col_offset=col_offset,
                length=1,
            )
        )
        tokens.append(
            SemanticToken(
                kind=TokenKind.VARIABLE_EXPRESSION_OPEN,
                value="{{",
                line=line,
                col_offset=col_offset + 1,
                length=2,
            )
        )
        expr_content = value[3:-2]
        expr_start = col_offset + 3

        # Collect sub-tokens: both $name (Python shorthand) and ${name}
        # (standard RF syntax) are valid inside ${{expr}}.
        expr_sub_tokens = _build_python_expression_sub_tokens(expr_content, line, expr_start)
        has_nested_vars = "${" in expr_content or "@{" in expr_content or "&{" in expr_content or "%{" in expr_content
        if has_nested_vars:
            nested = _decompose_nested_variable(expr_content, line, expr_start)
            if nested:
                if expr_sub_tokens is None:
                    expr_sub_tokens = []
                expr_sub_tokens.extend(nested)

        tokens.append(
            SemanticToken(
                kind=TokenKind.PYTHON_EXPRESSION,
                value=expr_content,
                line=line,
                col_offset=expr_start,
                length=len(expr_content),
                sub_tokens=expr_sub_tokens if expr_sub_tokens else None,
            )
        )
        tokens.append(
            SemanticToken(
                kind=TokenKind.VARIABLE_EXPRESSION_CLOSE,
                value="}}",
                line=line,
                col_offset=col_offset + len(value) - 2,
                length=2,
            )
        )
        return tokens

    # Regular variable: ${name}, @{list}, &{dict}, %{env}
    if len(value) >= 3 and value[1] == "{" and "}" in value:
        # Find the matching closing brace (accounting for nested braces)
        brace_depth = 0
        brace_end = 2
        while brace_end < len(value):
            if value[brace_end] == "{":
                brace_depth += 1
            elif value[brace_end] == "}":
                if brace_depth == 0:
                    break
                brace_depth -= 1
            brace_end += 1

        if brace_end >= len(value):
            return []

        # Handle index access after the variable: ${var}[0]
        index_part = value[brace_end + 1 :]

        # Build tokens for the main variable part
        tokens.append(
            SemanticToken(
                kind=TokenKind.VARIABLE_PREFIX,
                value=prefix_char,
                line=line,
                col_offset=col_offset,
                length=1,
            )
        )
        tokens.append(
            SemanticToken(
                kind=TokenKind.VARIABLE_OPEN_BRACE,
                value="{",
                line=line,
                col_offset=col_offset + 1,
                length=1,
            )
        )

        inner = value[2:brace_end]
        inner_start = col_offset + 2

        # Parse the inner content
        inner_tokens = _decompose_variable_inner(inner, line, inner_start, prefix_char)
        tokens.extend(inner_tokens)

        tokens.append(
            SemanticToken(
                kind=TokenKind.VARIABLE_CLOSE_BRACE,
                value="}",
                line=line,
                col_offset=col_offset + brace_end,
                length=1,
            )
        )

        # Handle assign mark: ${result}=
        if index_part == "=":
            tokens.append(
                SemanticToken(
                    kind=TokenKind.VARIABLE_ASSIGN_MARK,
                    value="=",
                    line=line,
                    col_offset=col_offset + brace_end + 1,
                    length=1,
                )
            )
        elif index_part.startswith("["):
            # Index access: ${var}[0], ${var}[key], ${var}[0][key]
            idx_tokens = build_index_sub_tokens(index_part, line, col_offset + brace_end + 1)
            tokens.extend(idx_tokens)

    return tokens


def _decompose_variable_inner(
    inner: str,
    line: int,
    col_offset: int,
    prefix_char: str,
) -> List[SemanticToken]:
    """Parse content between { and } of a variable.

    Handles:
    - Simple name: ``name``
    - Type hint (RF 7.0+): ``age: int``
    - Extended syntax: ``obj.attr``, ``SPACE * 5``
    - Default value (env vars): ``HOME=default``
    - Embedded pattern: ``arg:\\d+``
    - Nested variables: ``cfg_${env}``
    """
    tokens: List[SemanticToken] = []

    if not inner:
        return tokens

    # Environment variable default: %{NAME=default}
    if prefix_char == "%":
        if "=" in inner:
            eq_pos = inner.index("=")
            base = inner[:eq_pos]
            default_val = inner[eq_pos + 1 :]
            tokens.append(
                SemanticToken(
                    kind=TokenKind.VARIABLE_BASE,
                    value=base,
                    line=line,
                    col_offset=col_offset,
                    length=len(base),
                )
            )
            tokens.append(
                SemanticToken(
                    kind=TokenKind.VARIABLE_DEFAULT_SEPARATOR,
                    value="=",
                    line=line,
                    col_offset=col_offset + eq_pos,
                    length=1,
                )
            )
            tokens.append(
                SemanticToken(
                    kind=TokenKind.VARIABLE_DEFAULT_VALUE,
                    value=default_val,
                    line=line,
                    col_offset=col_offset + eq_pos + 1,
                    length=len(default_val),
                )
            )
            return tokens
        tokens.append(
            SemanticToken(
                kind=TokenKind.VARIABLE_BASE,
                value=inner,
                line=line,
                col_offset=col_offset,
                length=len(inner),
            )
        )
        return tokens

    # Check for nested variables: ${cfg_${env}}
    if "${" in inner or "@{" in inner or "&{" in inner or "%{" in inner:
        return _decompose_nested_variable(inner, line, col_offset)

    # Check for type hint: ${age: int}
    # RF uses ': ' (colon + space) as the type separator.
    # Everything after ': ' is the type hint — no further splitting.
    if ": " in inner and prefix_char == "$":
        colon_pos = inner.index(": ")
        base = inner[:colon_pos]
        rest = inner[colon_pos + 2 :]

        tokens.append(
            SemanticToken(
                kind=TokenKind.VARIABLE_BASE,
                value=base,
                line=line,
                col_offset=col_offset,
                length=len(base),
            )
        )
        tokens.append(
            SemanticToken(
                kind=TokenKind.VARIABLE_TYPE_SEPARATOR,
                value=": ",
                line=line,
                col_offset=col_offset + colon_pos,
                length=2,
            )
        )

        tokens.append(
            SemanticToken(
                kind=TokenKind.VARIABLE_TYPE_HINT,
                value=rest,
                line=line,
                col_offset=col_offset + colon_pos + 2,
                length=len(rest),
            )
        )
        return tokens

    # Check for embedded pattern without type: ${arg:\d+}
    if ":" in inner and prefix_char == "$":
        colon_pos = inner.index(":")
        base = inner[:colon_pos]
        pattern = inner[colon_pos + 1 :]
        tokens.append(
            SemanticToken(
                kind=TokenKind.VARIABLE_BASE,
                value=base,
                line=line,
                col_offset=col_offset,
                length=len(base),
            )
        )
        tokens.append(
            SemanticToken(
                kind=TokenKind.VARIABLE_PATTERN_SEPARATOR,
                value=":",
                line=line,
                col_offset=col_offset + colon_pos,
                length=1,
            )
        )
        tokens.append(
            SemanticToken(
                kind=TokenKind.VARIABLE_PATTERN,
                value=pattern,
                line=line,
                col_offset=col_offset + colon_pos + 1,
                length=len(pattern),
            )
        )
        return tokens

    # Check for extended syntax: ${obj.attr}, ${SPACE * 5}
    extended_match = _MATCH_EXTENDED.match(inner)
    if extended_match:
        base, extended = extended_match.groups()
        tokens.append(
            SemanticToken(
                kind=TokenKind.VARIABLE_BASE,
                value=base,
                line=line,
                col_offset=col_offset,
                length=len(base),
            )
        )
        tokens.append(
            SemanticToken(
                kind=TokenKind.VARIABLE_EXTENDED,
                value=extended,
                line=line,
                col_offset=col_offset + len(base),
                length=len(extended),
            )
        )
        return tokens

    # Simple variable name
    tokens.append(
        SemanticToken(
            kind=TokenKind.VARIABLE_BASE,
            value=inner,
            line=line,
            col_offset=col_offset,
            length=len(inner),
        )
    )

    return tokens


def _decompose_nested_variable(
    inner: str,
    line: int,
    col_offset: int,
) -> List[SemanticToken]:
    """Decompose inner content that contains nested variables.

    E.g., ``cfg_${env}`` -> TEXT_FRAGMENT + nested VARIABLE sub-tokens.
    """
    tokens: List[SemanticToken] = []
    pos = 0

    while pos < len(inner):
        # Look for next variable start
        next_var = -1
        for ident in ("${", "@{", "&{", "%{"):
            idx = inner.find(ident, pos)
            if idx >= 0 and (next_var < 0 or idx < next_var):
                next_var = idx

        if next_var < 0:
            # No more variables, rest is text
            if pos < len(inner):
                text = inner[pos:]
                tokens.append(
                    SemanticToken(
                        kind=TokenKind.TEXT_FRAGMENT,
                        value=text,
                        line=line,
                        col_offset=col_offset + pos,
                        length=len(text),
                    )
                )
            break

        # Text before variable
        if next_var > pos:
            text = inner[pos:next_var]
            tokens.append(
                SemanticToken(
                    kind=TokenKind.TEXT_FRAGMENT,
                    value=text,
                    line=line,
                    col_offset=col_offset + pos,
                    length=len(text),
                )
            )

        # Find matching closing brace
        brace_depth = 0
        end = next_var + 2  # skip identifier + {
        while end < len(inner):
            if inner[end] == "{":
                brace_depth += 1
            elif inner[end] == "}":
                if brace_depth == 0:
                    break
                brace_depth -= 1
            end += 1

        if end >= len(inner):
            # Unbalanced braces, treat as text
            text = inner[next_var:]
            tokens.append(
                SemanticToken(
                    kind=TokenKind.TEXT_FRAGMENT,
                    value=text,
                    line=line,
                    col_offset=col_offset + next_var,
                    length=len(text),
                )
            )
            break

        # Recurse into the nested variable
        nested_var = inner[next_var : end + 1]
        nested_sub = build_variable_sub_tokens(nested_var, line, col_offset + next_var)
        # The parent kind should be the nested variable itself
        tokens.append(
            SemanticToken(
                kind=TokenKind.VARIABLE,
                value=nested_var,
                line=line,
                col_offset=col_offset + next_var,
                length=len(nested_var),
                sub_tokens=nested_sub if nested_sub else None,
            )
        )
        pos = end + 1

    return tokens


def build_index_sub_tokens(
    index_str: str,
    line: int,
    col_offset: int,
) -> List[SemanticToken]:
    """Decompose index access into sub-tokens.

    E.g., ``[0]`` -> INDEX_OPEN + INDEX_CONTENT + INDEX_CLOSE
    E.g., ``[0][key]`` -> two VARIABLE_INDEX tokens each with sub-tokens.
    """
    tokens: List[SemanticToken] = []
    pos = 0

    while pos < len(index_str) and index_str[pos] == "[":
        # Find matching ]
        depth = 0
        end = pos
        while end < len(index_str):
            if index_str[end] == "[":
                depth += 1
            elif index_str[end] == "]":
                depth -= 1
                if depth == 0:
                    break
            end += 1

        if end >= len(index_str) or depth != 0:
            break

        index_content = index_str[pos : end + 1]
        inner_content = index_str[pos + 1 : end]

        sub_tokens = [
            SemanticToken(
                kind=TokenKind.VARIABLE_INDEX_OPEN,
                value="[",
                line=line,
                col_offset=col_offset + pos,
                length=1,
            ),
        ]

        # Check if inner content has variables
        if "${" in inner_content or "@{" in inner_content or "&{" in inner_content:
            nested = _decompose_nested_variable(inner_content, line, col_offset + pos + 1)
            sub_tokens.extend(nested)
        else:
            sub_tokens.append(
                SemanticToken(
                    kind=TokenKind.VARIABLE_INDEX_CONTENT,
                    value=inner_content,
                    line=line,
                    col_offset=col_offset + pos + 1,
                    length=len(inner_content),
                )
            )

        sub_tokens.append(
            SemanticToken(
                kind=TokenKind.VARIABLE_INDEX_CLOSE,
                value="]",
                line=line,
                col_offset=col_offset + end,
                length=1,
            )
        )

        tokens.append(
            SemanticToken(
                kind=TokenKind.VARIABLE_INDEX,
                value=index_content,
                line=line,
                col_offset=col_offset + pos,
                length=len(index_content),
                sub_tokens=sub_tokens,
            )
        )

        pos = end + 1

    return tokens


def _build_python_expression_sub_tokens(
    expr: str,
    line: int,
    col_offset: int,
) -> Optional[List[SemanticToken]]:
    """Extract $-prefixed variable references from a Python expression.

    E.g., ``os.path.join($base, "sub")`` -> PYTHON_VARIABLE_REF for ``$base``.
    """
    refs: List[SemanticToken] = []
    try:
        variable_started = False
        for toknum, tokval, (_, tokcol), _, _ in generate_tokens(StringIO(expr).readline):
            if variable_started:
                if toknum == python_token.NAME:
                    refs.append(
                        SemanticToken(
                            kind=TokenKind.PYTHON_VARIABLE_REF,
                            value=f"${tokval}",
                            line=line,
                            col_offset=col_offset + tokcol - 1,  # -1 for the $ sign
                            length=len(tokval) + 1,
                        )
                    )
                variable_started = False
            if tokval == "$":
                variable_started = True
    except TokenError:
        pass

    return refs if refs else None


def _iter_related_occurrences_from_token(
    token: SemanticToken,
    root_occurrence: VariableOccurrence,
) -> Iterator[VariableOccurrence]:
    if token.kind == TokenKind.VARIABLE and (
        token.value != root_occurrence.value
        or token.line != root_occurrence.line
        or token.col_offset != root_occurrence.col_offset
    ):
        nested = VariableOccurrence(
            value=token.value,
            line=token.line,
            col_offset=token.col_offset,
            length=token.length,
            lookup_name=normalize_variable_lookup_name(token.value, parse_type=False),
            semantic_sub_tokens=token.sub_tokens if token.sub_tokens else None,
        )
        yield nested
        if nested.semantic_sub_tokens:
            for sub in nested.semantic_sub_tokens:
                yield from _iter_related_occurrences_from_token(sub, nested)
        return

    if token.kind == TokenKind.PYTHON_VARIABLE_REF and token.value.startswith("$"):
        name = token.value[1:]
        if name:
            yield VariableOccurrence(
                value=name,
                line=token.line,
                col_offset=token.col_offset + 1,
                length=len(name),
                lookup_name=f"${{{name}}}",
                semantic_sub_tokens=None,
                strip_for_reference=False,
            )

    if token.sub_tokens:
        for sub in token.sub_tokens:
            yield from _iter_related_occurrences_from_token(sub, root_occurrence)
