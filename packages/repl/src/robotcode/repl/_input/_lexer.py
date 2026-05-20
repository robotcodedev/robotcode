"""Robot-aware syntax highlighter for the prompt_toolkit backend.

Three-stage tokenisation built entirely on production code that's
already in the robotcode codebase — no Pygments, no hand-rolled
regex lexer:

1. **Top-level tokens** via `robot.api.get_tokens(source,
   tokenize_variables=True, lang=...)`. Robot's own production
   tokenizer; recognises every cell type the running RF version
   supports (KEYWORD, ARGUMENT, ASSIGN, COMMENT, FOR/IF/WHILE/...,
   localised section headers, etc.).
2. **BDD-prefix splitting** for KEYWORD tokens: `Given user is
   logged in` becomes (BDD_PREFIX="Given", " ", KEYWORD="user is
   logged in"). The prefix set is pulled from the active
   `robot.api.Languages` instance, so this works for any locale RF
   ships (de, fr, es, …) — not just English.
3. **Variable sub-tokens** via `build_variable_sub_tokens()` from
   the diagnostics package. Decomposes `${nested${vars}}`,
   `${dict}[key]`, `%{HOME=default}`, `${age: int}`, `${{python}}`,
   etc. — every variable form RF supports, with sub_tokens for
   nested constructs.

The style-class mapping (`_STYLE_BY_KIND`) mirrors the
Language-Server's `_TOKEN_KIND_TO_SEM_TOKEN` mapping so the REPL
prompt uses the same colour semantics as VS Code with the RobotCode
extension installed.
"""

import io
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Set, Tuple

from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.lexers import Lexer
from robot.api import get_tokens

from robotcode.robot.diagnostics.semantic_analyzer.enums import TokenKind
from robotcode.robot.diagnostics.semantic_analyzer.nodes import SemanticToken
from robotcode.robot.diagnostics.semantic_analyzer.variable_tokenizer import (
    build_variable_sub_tokens,
)

# `robot.api.Languages` arrived in RF 6.0 — the BDD-prefix localisation
# feature simply isn't available on RF 5. We import lazily so the
# module still loads on RF 5, and fall back to the hardcoded English
# prefix set when the API isn't there.
try:
    from robot.api import Languages  # type: ignore[attr-defined,unused-ignore]
except ImportError:  # pragma: no cover — RF 5.x only
    Languages = None  # type: ignore[assignment,misc,unused-ignore]

# Hardcoded BDD prefix set used when `Languages` isn't available
# (RF 5) or when explicit `lang=None` is passed. Robot's English
# defaults; consistent with `Languages('en').bdd_prefixes`.
_EN_BDD_PREFIXES: Set[str] = {"Given", "When", "Then", "And", "But"}

_PREFIX = "*** Test Cases ***\nREPL\n"
_PREFIX_LINE_COUNT = 2
_INDENT = "    "

# Top-level Robot Token.type → prompt_toolkit style class. Token types
# come from robot.api.Token; see the comprehensive list in
# `Token.__init__`. Anything not in the map renders unstyled.
_STYLE_BY_TOKEN_TYPE: Dict[str, str] = {
    "KEYWORD": "class:rf.keyword",
    "ARGUMENT": "class:rf.argument",
    "ASSIGN": "class:rf.assign",
    "COMMENT": "class:rf.comment",
    "FOR": "class:rf.block",
    "IF": "class:rf.block",
    "WHILE": "class:rf.block",
    "TRY": "class:rf.block",
    "GROUP": "class:rf.block",
    "END": "class:rf.block",
    "ELSE": "class:rf.block",
    "ELSE IF": "class:rf.block",
    "EXCEPT": "class:rf.block",
    "FINALLY": "class:rf.block",
    "FOR SEPARATOR": "class:rf.block",
    "RETURN STATEMENT": "class:rf.block",
    "CONTINUE": "class:rf.block",
    "BREAK": "class:rf.block",
}

# Variable-sub-token TokenKind → prompt_toolkit style class.
# Mirrors `_TOKEN_KIND_TO_SEM_TOKEN` from
# packages/language_server/.../semantic_tokens.py:1039 so the colour
# semantics match what RobotCode users see in VS Code.
_STYLE_BY_KIND: Dict[TokenKind, str] = {
    TokenKind.BDD_PREFIX: "class:rf.bdd",
    TokenKind.VARIABLE_PREFIX: "class:rf.variable.brace",
    TokenKind.VARIABLE_OPEN_BRACE: "class:rf.variable.brace",
    TokenKind.VARIABLE_CLOSE_BRACE: "class:rf.variable.brace",
    TokenKind.VARIABLE_BASE: "class:rf.variable.name",
    TokenKind.VARIABLE_EXTENDED: "class:rf.variable.extended",
    TokenKind.VARIABLE_TYPE_SEPARATOR: "class:rf.variable.operator",
    TokenKind.VARIABLE_TYPE_HINT: "class:rf.variable.type",
    TokenKind.VARIABLE_DEFAULT_SEPARATOR: "class:rf.variable.operator",
    TokenKind.VARIABLE_DEFAULT_VALUE: "class:rf.argument",
    TokenKind.VARIABLE_PATTERN_SEPARATOR: "class:rf.variable.operator",
    TokenKind.VARIABLE_PATTERN: "class:rf.argument",
    TokenKind.VARIABLE_ASSIGN_MARK: "class:rf.assign",
    TokenKind.VARIABLE_EXPRESSION_OPEN: "class:rf.variable.expr",
    TokenKind.VARIABLE_EXPRESSION_CLOSE: "class:rf.variable.expr",
    TokenKind.PYTHON_EXPRESSION: "class:rf.variable.python",
    TokenKind.PYTHON_VARIABLE_REF: "class:rf.variable.name",
    TokenKind.VARIABLE_INDEX_OPEN: "class:rf.variable.brace",
    TokenKind.VARIABLE_INDEX_CLOSE: "class:rf.variable.brace",
    TokenKind.VARIABLE_INDEX_CONTENT: "class:rf.variable.name",
    # Literal part of a computed-variable lookup like
    # ``${PREFIX_${SUFFIX}}`` — colour as part of the name.
    TokenKind.TEXT_FRAGMENT: "class:rf.variable.name",
    # Catch-all for VARIABLE (un-decomposed, e.g. inside a nested
    # parent before we descend) — should rarely appear because we
    # always walk into sub_tokens, but acts as a safety net.
    TokenKind.VARIABLE: "class:rf.variable.name",
}

_VARIABLE_FALLBACK_STYLE = "class:rf.variable.name"


def _iter_leaves(token: SemanticToken) -> Iterator[SemanticToken]:
    """Yield only the leaf SemanticTokens (no sub_tokens) from `token`.

    `build_variable_sub_tokens` returns a tree where parent tokens
    like ``VARIABLE`` (for ``${${inner}}``) or ``VARIABLE_INDEX`` (for
    ``[key]``) carry their decomposition inside ``sub_tokens``. For
    syntax-highlighting we want a flat sequence covering every
    character exactly once — i.e., the leaves of that tree.
    """
    if token.sub_tokens:
        for sub in token.sub_tokens:
            yield from _iter_leaves(sub)
    else:
        yield token


def _split_variable(value: str) -> Iterable[Tuple[str, str]]:
    """Delegate variable decomposition to the diagnostics-package helper.

    Wraps recursive `_iter_leaves` traversal so the lexer can drop the
    resulting `(style, text)` tuples straight into a prompt_toolkit
    line buffer. Tolerant of mid-typed input — any exception out of
    the decomposer falls back to a single un-decomposed token, which
    still renders (just without per-part colouring).
    """
    try:
        sub_tokens = build_variable_sub_tokens(value, line=1, col_offset=0)
    except Exception:
        yield (_VARIABLE_FALLBACK_STYLE, value)
        return
    if not sub_tokens:
        yield (_VARIABLE_FALLBACK_STYLE, value)
        return
    for st in sub_tokens:
        for leaf in _iter_leaves(st):
            yield (_STYLE_BY_KIND.get(leaf.kind, _VARIABLE_FALLBACK_STYLE), leaf.value)


def _split_keyword_for_bdd(value: str, bdd_prefixes: Set[str]) -> Iterable[Tuple[str, str]]:
    """Split a keyword call like ``Given user is logged in`` into
    ``(BDD_PREFIX, " ", rest)``.

    Compare is case-insensitive (matches Robot's own BDD matcher); the
    user's original casing survives in the output for fidelity.
    Returns the original token unsplit if no BDD prefix matches.
    """
    lower = value.lower()
    for prefix in bdd_prefixes:
        head = prefix.lower() + " "
        if lower.startswith(head):
            n = len(prefix)
            yield (_STYLE_BY_KIND[TokenKind.BDD_PREFIX], value[:n])
            yield ("", value[n : n + 1])  # the separating space
            yield (_STYLE_BY_TOKEN_TYPE["KEYWORD"], value[n + 1 :])
            return
    yield (_STYLE_BY_TOKEN_TYPE["KEYWORD"], value)


class RobotLexer(Lexer):
    """prompt_toolkit Lexer that paints Robot syntax using Robot's own
    parser + the robotcode semantic-analyzer's variable decomposer.

    `lang` is the active `robot.api.Languages` instance. When None,
    English defaults apply — works for the vast majority of users.
    To get localised section headers / BDD prefixes tokenized, the
    caller passes the Languages instance the runner uses (wired
    through when `robotcode repl --language=de` lands; out-of-scope
    here, see plan).
    """

    def __init__(self, lang: Optional[Any] = None) -> None:
        # `lang` is a `robot.api.Languages` instance when RF >= 6, or
        # None on RF 5 where the API doesn't exist. We store the
        # original value (so we can thread it back to `get_tokens`)
        # and pre-compute the BDD-prefix union once so per-keyword
        # lookup stays O(prefix-count) per render.
        self._lang = lang
        if lang is not None:
            self._bdd_prefixes = {p for L in lang.languages for p in L.bdd_prefixes}
        elif Languages is not None:
            # No explicit `lang=` but Languages-API available → use
            # the default (English) Languages instance for both
            # `get_tokens(lang=...)` parametrisation and prefix lookup.
            self._lang = Languages()
            self._bdd_prefixes = {p for L in self._lang.languages for p in L.bdd_prefixes}
        else:
            # RF 5 — no localisation API at all. Hardcoded English
            # set keeps the BDD-splitting working for the dominant
            # case.
            self._bdd_prefixes = _EN_BDD_PREFIXES

    def lex_document(self, document: Document) -> "Callable[[int], StyleAndTextTuples]":
        """Tokenise the full buffer once and return a per-line indexer.

        Wraps user input with a ``*** Test Cases ***`` header so
        Robot's tokenizer enters test-body mode (otherwise the whole
        thing would be classified as COMMENT). Maps token line
        numbers back from the wrapped buffer to the user's line
        numbers by subtracting the prefix line count.

        Any error during tokenisation collapses to an unstyled
        rendering — the prompt stays usable even if the user types
        something the parser can't handle yet (which is normal
        mid-typing).
        """
        wrapped = _PREFIX + "\n".join(_INDENT + ln for ln in document.lines)
        by_line: Dict[int, List[Tuple[str, str]]] = {}
        try:
            # `lang=` requires RF 6+; on RF 5 we drop the kwarg.
            if Languages is not None:
                token_iter = get_tokens(io.StringIO(wrapped), tokenize_variables=True, lang=self._lang)
            else:  # pragma: no cover — RF 5.x only
                token_iter = get_tokens(io.StringIO(wrapped), tokenize_variables=True)
            for tok in token_iter:
                user_lineno = tok.lineno - _PREFIX_LINE_COUNT - 1
                if user_lineno < 0:
                    continue
                # EOL carries `\n` (renders as `^J` if we keep it);
                # EOS is empty. Both are line-terminator artefact —
                # `document.lines` already split on newlines for us.
                if tok.type in ("EOL", "EOS"):
                    continue
                row = by_line.setdefault(user_lineno, [])
                if tok.type == "VARIABLE":
                    row.extend(_split_variable(tok.value))
                elif tok.type == "KEYWORD":
                    row.extend(_split_keyword_for_bdd(tok.value, self._bdd_prefixes))
                else:
                    style = _STYLE_BY_TOKEN_TYPE.get(tok.type, "")
                    row.append((style, tok.value))
        except Exception:
            return lambda lineno: [("", document.lines[lineno])]
        # Drop the `_INDENT` we injected to coerce test-body mode —
        # otherwise it renders as 4 visible leading spaces.
        indent_len = len(_INDENT)
        by_line = {ln: _strip_leading_chars(fragments, indent_len) for ln, fragments in by_line.items()}
        # Pad rendered lines out to the buffer's actual length — Robot
        # drops trailing whitespace and prompt_toolkit would otherwise
        # pin the cursor at the rendered end (causing it to "stick"
        # while the user keeps typing spaces).
        for ln, expected_text in enumerate(document.lines):
            row = by_line.setdefault(ln, [])
            missing = len(expected_text) - sum(len(text) for _, text in row)
            if missing > 0:
                row.append(("", " " * missing))
        return lambda lineno: _coerce_to_tuples(by_line.get(lineno), document, lineno)


def _strip_leading_chars(fragments: List[Tuple[str, str]], n: int) -> List[Tuple[str, str]]:
    """Drop the first `n` characters of content from `fragments`,
    chaining across multiple `(style, text)` tuples. Tokens that
    straddle the boundary get their text trimmed; tokens fully
    inside the strip-range are dropped entirely.
    """
    remaining = n
    out: List[Tuple[str, str]] = []
    started = False
    for style, text in fragments:
        if started:
            out.append((style, text))
            continue
        if remaining >= len(text):
            remaining -= len(text)
            continue
        if remaining > 0:
            text = text[remaining:]
            remaining = 0
        started = True
        out.append((style, text))
    return out


def _coerce_to_tuples(
    fragments: Optional[List[Tuple[str, str]]],
    document: Document,
    lineno: int,
) -> StyleAndTextTuples:
    """Provide a sensible fallback when the tokenizer didn't emit
    anything for a line (e.g. a fully blank line). prompt_toolkit
    expects a non-empty `StyleAndTextTuples`; an empty list would
    suppress the line entirely."""
    if fragments:
        return fragments  # type: ignore[return-value]
    return [("", document.lines[lineno])]
