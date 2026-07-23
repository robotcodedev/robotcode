"""Model-path variable extraction shared by selection range, inline values,
and debug evaluatable expressions.

A faithful, self-contained port of the legacy
`ModelHelper.iter_variables_from_token` / `iter_expression_variables_from_token`
candidate semantics, operating on the `SemanticToken`s of a
`SemanticStatement`:

- variable occurrences are scanned from the token *values* of the cells the
  legacy tokenizer type gate admits (arguments, names, keyword cells — not
  comments or error tokens), in the same order legacy yields them: outer
  variables before nested ones, the extended-syntax base name before the
  full inner span;
- resolution goes through `SemanticModel.find_variable()` (no `ModelHelper`,
  no `Namespace` re-resolution on the model path);
- bare-``$var`` expression references come from the pre-computed
  `PYTHON_VARIABLE_REF` sub-tokens of `CONDITION` cells.

Consumers differ only in how they use the candidates: selection range takes
the first candidate whose range contains the cursor; inline values and debug
extraction re-resolve the primary candidate of each occurrence at the
debugger's stopped location and keep only found definitions.
"""

from dataclasses import dataclass
from typing import Iterator, List, Optional

from robotcode.core.lsp.types import Position, Range
from robotcode.robot.diagnostics.semantic_analyzer.enums import NodeKind, TokenKind
from robotcode.robot.diagnostics.semantic_analyzer.model import SemanticModel
from robotcode.robot.diagnostics.semantic_analyzer.nodes import SemanticStatement, SemanticToken
from robotcode.robot.diagnostics.semantic_analyzer.variable_tokenizer import (
    _MATCH_EXTENDED,
    _build_python_expression_sub_tokens,
)
from robotcode.robot.utils.variables import contains_variable, is_number_literal, search_variable

# Statement cells the legacy `tokenize_variables` walk actually scans — its
# type gate allows `Token.ALLOW_VARIABLES` (arguments, names, test-case and
# keyword definition names) plus KEYWORD, ASSIGN, and OPTION cells;
# `Token.VARIABLE` cells pass through whole. Comments, error tokens, setting
# names, control-flow words, and structural tokens are never scanned.
_SCANNABLE_KINDS = frozenset(
    {
        TokenKind.ARGUMENT,
        TokenKind.TAG,
        TokenKind.CONDITION,
        TokenKind.NAMED_ARGUMENT_NAME,
        TokenKind.NAMED_ARGUMENT_VALUE,
        TokenKind.OPTION,
        TokenKind.OPTION_NAME,
        TokenKind.OPTION_VALUE,
        TokenKind.TEST_NAME,
        TokenKind.KEYWORD_NAME,
        TokenKind.KEYWORD,
        TokenKind.KEYWORD_INNER,
        TokenKind.BDD_PREFIX,
        TokenKind.NAMESPACE,
        TokenKind.IMPORT_NAME,
        TokenKind.VARIABLE,
        TokenKind.VARIABLE_NOT_FOUND,
        TokenKind.VARIABLE_NAME,
    }
)


def scannable_statement_tokens(stmt: SemanticStatement) -> List[SemanticToken]:
    """The top-level tokens of a statement that the legacy variable iteration
    would scan (see the `_SCANNABLE_KINDS` gate above)."""
    return [token for token in stmt.tokens if token.kind in _SCANNABLE_KINDS]


@dataclass
class ModelVariableCandidate:
    """One selectable/resolvable variable occurrence candidate."""

    range: Range
    lookup_name: str
    primary: bool
    """True for the first candidate of an occurrence — the one whose lookup
    name mirrors the legacy resolution (extended syntax resolves the base)."""


# Statements whose variable-family cells come from `Token.VARIABLE` in the
# AST (definition names, FOR/EXCEPT/VAR targets) — outside the legacy
# tokenizer's type gate. Assign targets in keyword calls / inline IF are
# `Token.ASSIGN` and tokenize normally.
_UNGATED_STMT_KINDS = frozenset({NodeKind.VARIABLE_DEF, NodeKind.FOR_HEADER, NodeKind.EXCEPT_HEADER})


def iter_model_variable_candidates(
    token: SemanticToken,
    model: SemanticModel,
    resolve_line: int,
    resolve_col: Optional[int] = None,
    stmt_kind: Optional[NodeKind] = None,
) -> Iterator[ModelVariableCandidate]:
    """Yield the regular variable candidates of one statement token in legacy
    order (`iter_variables_from_token`).

    ``resolve_line`` / ``resolve_col`` form the position used for
    visibility-aware lookups (the cursor position for selection range, the
    debugger's stopped location for inline values). ``stmt_kind`` is the
    containing statement's kind — it decides whether a variable-family cell
    is a `Token.VARIABLE` (processed whole, outside the legacy tokenizer's
    type gate) or a tokenized `Token.ASSIGN`.
    """
    if token.value and token.col_offset is not None:
        ungated = stmt_kind in _UNGATED_STMT_KINDS and token.kind in (
            TokenKind.VARIABLE,
            TokenKind.VARIABLE_NOT_FOUND,
            TokenKind.VARIABLE_NAME,
        )
        yield from _scan_value(token.value, token.line, token.col_offset, ungated, model, resolve_line, resolve_col)


def iter_condition_ref_candidates(token: SemanticToken) -> Iterator[ModelVariableCandidate]:
    """Yield the bare ``$var`` expression-reference candidates of a
    `CONDITION` cell from its pre-computed `PYTHON_VARIABLE_REF` sub-tokens
    (legacy `iter_expression_variables_from_token`). Used by inline values
    and debug extraction, but not by selection range."""
    if token.kind is not TokenKind.CONDITION:
        return
    for sub in token.sub_tokens or []:
        if sub.kind is TokenKind.PYTHON_VARIABLE_REF:
            yield from _expression_ref_candidate(sub)


def _scan_value(
    value: str,
    line: int,
    col_offset: int,
    ungated: bool,
    model: SemanticModel,
    resolve_line: int,
    resolve_col: Optional[int],
) -> Iterator[ModelVariableCandidate]:
    """Scan a value fragment for variable occurrences, mirroring the legacy
    `tokenize_variables` walk (outer occurrence first, then its index-access
    content and the rest of the fragment)."""
    pos = 0
    while pos < len(value):
        matcher = search_variable(value[pos:], "$@&%", ignore_errors=True)
        base = matcher.base
        if base is None:
            if ungated and pos == 0 and len(value) >= 2 and value[0] in "$@&%" and value[1] == "{":
                # Unclosed variable at the start of the cell (`${aaa`):
                # legacy yields the whole raw token
                # (`strip_variable_token` leaves unparseable values untouched).
                yield ModelVariableCandidate(
                    range=_make_range(line, col_offset, len(value)),
                    lookup_name=value,
                    primary=True,
                )
            return

        var_start = pos + matcher.start
        name = matcher.name or ""
        if not name:
            # `${}` / `@{}`: legacy yields the whole unstripped remainder once
            # and stops scanning the token.
            span = value[var_start : pos + matcher.end] or value[var_start:]
            yield ModelVariableCandidate(
                range=_make_range(line, col_offset + var_start, len(span)),
                lookup_name=span,
                primary=True,
            )
            return

        yield from _occurrence_candidates(
            name, base, line, col_offset + var_start, ungated, model, resolve_line, resolve_col
        )
        if ungated:
            # An ungated cell is processed as a single whole occurrence.
            return

        # Continue right after the variable's closing brace: index-access
        # content (`${x}[${i}]`) and the remaining text are scanned like the
        # legacy rest-recursion.
        pos = var_start + len(name)


def _occurrence_candidates(
    name: str,
    base: str,
    line: int,
    col_offset: int,
    ungated: bool,
    model: SemanticModel,
    resolve_line: int,
    resolve_col: Optional[int],
) -> Iterator[ModelVariableCandidate]:
    """Candidates of one well-formed variable occurrence ``name`` (e.g.
    ``${obj.attr}``) whose ``$`` sits at ``col_offset``.

    Mirrors the legacy resolution order: raw lookup → number-literal skip →
    extended-syntax base lookup → not-found candidates; nested variables
    always follow their container.
    """
    if base.startswith("{") and base.endswith("}"):
        # `${{expr}}`: only bare `$var` refs inside the expression count.
        yield from _python_expression_candidates(base[1:-1], line, col_offset + 3)
        return

    nested = contains_variable(base, "$@&%")
    stripped = base.strip()
    inner_range = _make_range(
        line,
        col_offset + 2 + (len(base) - len(base.lstrip())),
        len(stripped),
    )

    if model.find_variable(name, resolve_line, resolve_col, extended=False) is not None:
        # Raw name resolves (including literal names with spaces or nested
        # syntax, e.g. a definition row `${VALID VAR ${A}}`).
        yield ModelVariableCandidate(range=inner_range, lookup_name=name, primary=True)
    elif is_number_literal(name):
        # Number literals (`${42}`, `${0x1F}`) are values, not variables.
        pass
    else:
        extended = _MATCH_EXTENDED.match(base)
        if extended is not None:
            base_name = extended.group(1).strip()
            base_lookup = f"{name[0]}{{{base_name}}}"
            base_range = _make_range(line, col_offset + 2, len(base_name))
            if base_name and not contains_variable(base_name, "$@&%"):
                if model.find_variable(base_lookup, resolve_line, resolve_col, extended=False) is not None:
                    yield ModelVariableCandidate(range=base_range, lookup_name=base_lookup, primary=True)
                elif not is_number_literal(base_lookup) and not contains_variable(base, "$@&"):
                    # Legacy quirk: the unresolved-container check runs with
                    # the default `$@&` identifiers, so `%{}`-only nesting
                    # still yields the not-found pair.
                    yield ModelVariableCandidate(range=base_range, lookup_name=base_lookup, primary=True)
                    yield ModelVariableCandidate(range=inner_range, lookup_name=name, primary=False)
        elif not nested:
            yield ModelVariableCandidate(range=inner_range, lookup_name=name, primary=True)

    if nested:
        if ungated:
            # Legacy re-slices ungated containers raw (`value[2:-1]`) instead
            # of tokenizing them: the whole inner span comes back once as an
            # unresolvable pseudo-variable; the nested variables themselves
            # are never reached.
            yield ModelVariableCandidate(
                range=_make_range(line, col_offset + 2, len(base)),
                lookup_name=base,
                primary=True,
            )
            return
        # Nested occurrences inside the container's braces.
        yield from _scan_value(base, line, col_offset + 2, False, model, resolve_line, resolve_col)


def _python_expression_candidates(expr: str, line: int, col_offset: int) -> Iterator[ModelVariableCandidate]:
    """Name-only candidates for the ``$var`` refs of a `${{expr}}` body,
    positions identical to the analyzer's `PYTHON_VARIABLE_REF` sub-tokens."""
    for ref in _build_python_expression_sub_tokens(expr, line, col_offset) or []:
        yield from _expression_ref_candidate(ref)


def _expression_ref_candidate(ref: SemanticToken) -> Iterator[ModelVariableCandidate]:
    """Name-only candidate of a `PYTHON_VARIABLE_REF` (`$var` → `var`)."""
    if ref.length <= 1:
        return
    name = ref.value[1:] if ref.value.startswith("$") else ref.value
    yield ModelVariableCandidate(
        range=_make_range(ref.line, ref.col_offset + 1, ref.length - 1),
        lookup_name=f"${{{name}}}",
        primary=True,
    )


def _make_range(line: int, col_offset: int, length: int) -> Range:
    return Range(
        start=Position(line=line - 1, character=col_offset),
        end=Position(line=line - 1, character=col_offset + length),
    )


def iter_statement_tokens_at_line(model: SemanticModel, line: int) -> Iterator[SemanticToken]:
    """Scannable top-level tokens of every statement covering a 1-indexed
    line.

    A line can hold several statements (inline `IF` header plus its branch
    calls), so the single most-specific `statement_at()` result is not
    enough for position-based candidate searches.
    """
    for stmt in model.statements:
        if stmt.line_start <= line <= stmt.line_end:
            yield from scannable_statement_tokens(stmt)


def iter_line_variable_candidates(
    model: SemanticModel,
    line: int,
    resolve_col: Optional[int] = None,
) -> Iterator[ModelVariableCandidate]:
    """Regular variable candidates of every statement covering a 1-indexed
    line."""
    for stmt in model.statements:
        if stmt.line_start <= line <= stmt.line_end:
            for token in scannable_statement_tokens(stmt):
                yield from iter_model_variable_candidates(token, model, line, resolve_col, stmt.kind)


def iter_line_condition_ref_candidates(model: SemanticModel, line: int) -> Iterator[ModelVariableCandidate]:
    """Bare ``$var`` expression-reference candidates of every condition cell
    on a 1-indexed line."""
    for stmt in model.statements:
        if stmt.line_start <= line <= stmt.line_end:
            for token in stmt.tokens:
                yield from iter_condition_ref_candidates(token)


def find_model_variable_range_at(
    model: SemanticModel,
    position: Position,
    within: Range,
) -> Optional[Range]:
    """First candidate range containing the position — the model-path
    replacement for the legacy selection-range variable step.

    ``within`` is the range of the AST token under the cursor: legacy only
    iterates the variables of that one token, so candidates outside it (a
    neighbouring cell whose end touches the position) must not match.
    """
    for candidate in iter_line_variable_candidates(model, position.line + 1, position.character):
        if position in candidate.range and candidate.range.start >= within.start and candidate.range.end <= within.end:
            return candidate.range
    return None
