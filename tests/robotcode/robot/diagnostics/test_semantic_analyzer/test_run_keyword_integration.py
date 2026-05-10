"""Integration tests for RunKeywordCallStatement creation in SemanticAnalyzer.

Verifies that Run Keyword variants produce RunKeywordCallStatement with
correctly populated inner_calls, and that normal keyword calls still
produce plain KeywordCallStatement.
"""

from typing import Any, Callable, Optional

import pytest

from robotcode.robot.diagnostics.analyzer_result import AnalyzerResult
from robotcode.robot.diagnostics.library_doc import (
    BUILTIN_LIBRARY_NAME,
    KeywordDoc,
)
from robotcode.robot.diagnostics.semantic_analyzer.enums import NodeKind
from robotcode.robot.diagnostics.semantic_analyzer.nodes import (
    KeywordCallStatement,
    RunKeywordCallStatement,
)

# Type alias keeps test signatures readable.
AnalyzerFactory = Callable[..., AnalyzerResult]


def _builtin_kw(name: str, args_to_process: Optional[int] = None) -> KeywordDoc:
    """Create a BuiltIn KeywordDoc that is recognized as a run keyword."""
    return KeywordDoc(
        line_no=-1,
        col_offset=-1,
        end_line_no=-1,
        end_col_offset=-1,
        source=None,
        name=name,
        libname=BUILTIN_LIBRARY_NAME,
        arguments=[],
        arguments_spec=None,
        args_to_process=args_to_process,
    )


def _regular_kw(name: str, libname: str = "MyLib") -> KeywordDoc:
    """Create a regular (non-run-keyword) KeywordDoc."""
    return KeywordDoc(
        line_no=-1,
        col_offset=-1,
        end_line_no=-1,
        end_col_offset=-1,
        source=None,
        name=name,
        libname=libname,
        arguments=[],
        arguments_spec=None,
    )


def _keyword_call_stmts(result: AnalyzerResult) -> list[KeywordCallStatement]:
    """Extract all KeywordCallStatement (including RunKeywordCallStatement) from model."""
    assert result.semantic_model is not None
    return [s for s in result.semantic_model.statements if isinstance(s, KeywordCallStatement)]


@pytest.fixture
def run_kw_analyzer(
    analyzer_factory: Callable[..., AnalyzerResult],
    make_library_doc_mock: Callable[..., Any],
) -> Callable[..., AnalyzerResult]:
    """Local convenience: this module's tests want a `library_doc`-shaped
    mock (with `resource_variables` / `resource_imports`) instead of the
    real `ResourceDoc`. Wrap the shared `analyzer_factory` to inject that.
    """

    def factory(
        text: str,
        keyword_map: Optional[dict[str, Optional[KeywordDoc]]] = None,
    ) -> AnalyzerResult:
        return analyzer_factory(text, keyword_map=keyword_map, library_doc=make_library_doc_mock())

    return factory


# --- Normal keyword calls: no inner_calls ---


class TestNormalKeywordCall:
    def test_plain_keyword_produces_keyword_call_statement(self, run_kw_analyzer: AnalyzerFactory) -> None:
        result = run_kw_analyzer(
            """\
*** Test Cases ***
Example
    Log    hello
""",
            {"Log": _regular_kw("Log")},
        )
        stmts = _keyword_call_stmts(result)
        assert len(stmts) == 1
        assert type(stmts[0]) is KeywordCallStatement
        assert not isinstance(stmts[0], RunKeywordCallStatement)

    def test_unknown_keyword_produces_keyword_call_statement(self, run_kw_analyzer: AnalyzerFactory) -> None:
        result = run_kw_analyzer(
            """\
*** Test Cases ***
Example
    Unknown Keyword    arg1
""",
        )
        stmts = _keyword_call_stmts(result)
        assert len(stmts) == 1
        assert type(stmts[0]) is KeywordCallStatement


# --- Run Keyword (single inner call) ---


class TestRunKeyword:
    def test_run_keyword_creates_run_keyword_call_statement(self, run_kw_analyzer: AnalyzerFactory) -> None:
        result = run_kw_analyzer(
            """\
*** Test Cases ***
Example
    Run Keyword    Log    hello
""",
            {
                "Run Keyword": _builtin_kw("Run Keyword"),
                "Log": _regular_kw("Log"),
            },
        )
        stmts = _keyword_call_stmts(result)
        assert len(stmts) == 1
        stmt = stmts[0]
        assert isinstance(stmt, RunKeywordCallStatement)
        assert stmt.keyword_doc is not None
        assert stmt.keyword_doc.name == "Run Keyword"
        assert len(stmt.inner_calls) == 1
        inner = stmt.inner_calls[0]
        assert type(inner) is KeywordCallStatement
        assert inner.keyword_doc is not None
        assert inner.keyword_doc.name == "Log"

    def test_run_keyword_with_unresolved_inner_keyword(self, run_kw_analyzer: AnalyzerFactory) -> None:
        result = run_kw_analyzer(
            """\
*** Test Cases ***
Example
    Run Keyword    Unknown Inner    arg1
""",
            {"Run Keyword": _builtin_kw("Run Keyword")},
        )
        stmts = _keyword_call_stmts(result)
        assert len(stmts) == 1
        stmt = stmts[0]
        assert isinstance(stmt, RunKeywordCallStatement)
        assert len(stmt.inner_calls) == 1
        inner = stmt.inner_calls[0]
        assert inner.keyword_doc is None

    def test_run_keyword_without_arguments_is_plain(self, run_kw_analyzer: AnalyzerFactory) -> None:
        """Run Keyword with no arguments does not produce inner calls."""
        result = run_kw_analyzer(
            """\
*** Test Cases ***
Example
    Run Keyword
""",
            {"Run Keyword": _builtin_kw("Run Keyword")},
        )
        stmts = _keyword_call_stmts(result)
        assert len(stmts) == 1
        assert type(stmts[0]) is KeywordCallStatement


# --- Run Keyword And Continue On Failure (is_run_keyword) ---


class TestRunKeywordVariants:
    def test_run_keyword_and_continue_on_failure(self, run_kw_analyzer: AnalyzerFactory) -> None:
        result = run_kw_analyzer(
            """\
*** Test Cases ***
Example
    Run Keyword And Continue On Failure    Log    hello
""",
            {
                "Run Keyword And Continue On Failure": _builtin_kw("Run Keyword And Continue On Failure"),
                "Log": _regular_kw("Log"),
            },
        )
        stmts = _keyword_call_stmts(result)
        assert len(stmts) == 1
        stmt = stmts[0]
        assert isinstance(stmt, RunKeywordCallStatement)
        assert len(stmt.inner_calls) == 1
        assert stmt.inner_calls[0].keyword_doc is not None
        assert stmt.inner_calls[0].keyword_doc.name == "Log"


# --- Run Keyword With Condition (skips N condition args) ---


class TestRunKeywordWithCondition:
    def test_wait_until_keyword_succeeds(self, run_kw_analyzer: AnalyzerFactory) -> None:
        result = run_kw_analyzer(
            """\
*** Test Cases ***
Example
    Wait Until Keyword Succeeds    3x    1s    Log    hello
""",
            {
                "Wait Until Keyword Succeeds": _builtin_kw("Wait Until Keyword Succeeds", args_to_process=2),
                "Log": _regular_kw("Log"),
            },
        )
        stmts = _keyword_call_stmts(result)
        assert len(stmts) == 1
        stmt = stmts[0]
        assert isinstance(stmt, RunKeywordCallStatement)
        assert len(stmt.inner_calls) == 1
        assert stmt.inner_calls[0].keyword_doc is not None
        assert stmt.inner_calls[0].keyword_doc.name == "Log"

    def test_run_keyword_and_expect_error(self, run_kw_analyzer: AnalyzerFactory) -> None:
        result = run_kw_analyzer(
            """\
*** Test Cases ***
Example
    Run Keyword And Expect Error    *error*    Log    hello
""",
            {
                "Run Keyword And Expect Error": _builtin_kw("Run Keyword And Expect Error"),
                "Log": _regular_kw("Log"),
            },
        )
        stmts = _keyword_call_stmts(result)
        assert len(stmts) == 1
        stmt = stmts[0]
        assert isinstance(stmt, RunKeywordCallStatement)
        assert len(stmt.inner_calls) == 1


# --- Run Keywords (AND-separated) ---


class TestRunKeywords:
    def test_run_keywords_single(self, run_kw_analyzer: AnalyzerFactory) -> None:
        """Without AND separators, each token is a separate keyword name."""
        result = run_kw_analyzer(
            """\
*** Test Cases ***
Example
    Run Keywords    Log
""",
            {
                "Run Keywords": _builtin_kw("Run Keywords"),
                "Log": _regular_kw("Log"),
            },
        )
        stmts = _keyword_call_stmts(result)
        assert len(stmts) == 1
        stmt = stmts[0]
        assert isinstance(stmt, RunKeywordCallStatement)
        assert len(stmt.inner_calls) == 1
        assert stmt.inner_calls[0].keyword_doc is not None
        assert stmt.inner_calls[0].keyword_doc.name == "Log"

    def test_run_keywords_without_and_treats_each_token_as_keyword(self, run_kw_analyzer: AnalyzerFactory) -> None:
        """Without AND, 'Log' and 'hello' are both treated as keyword names."""
        result = run_kw_analyzer(
            """\
*** Test Cases ***
Example
    Run Keywords    Log    hello
""",
            {
                "Run Keywords": _builtin_kw("Run Keywords"),
                "Log": _regular_kw("Log"),
            },
        )
        stmts = _keyword_call_stmts(result)
        assert len(stmts) == 1
        stmt = stmts[0]
        assert isinstance(stmt, RunKeywordCallStatement)
        # Without AND separators, both "Log" and "hello" are separate keyword calls
        assert len(stmt.inner_calls) == 2

    def test_run_keywords_with_and_separator(self, run_kw_analyzer: AnalyzerFactory) -> None:
        result = run_kw_analyzer(
            """\
*** Test Cases ***
Example
    Run Keywords    Log    hello    AND    Log    world
""",
            {
                "Run Keywords": _builtin_kw("Run Keywords"),
                "Log": _regular_kw("Log"),
            },
        )
        stmts = _keyword_call_stmts(result)
        assert len(stmts) == 1
        stmt = stmts[0]
        assert isinstance(stmt, RunKeywordCallStatement)
        assert len(stmt.inner_calls) == 2
        assert all(inner.keyword_doc is not None and inner.keyword_doc.name == "Log" for inner in stmt.inner_calls)

    def test_run_keywords_three_keywords(self, run_kw_analyzer: AnalyzerFactory) -> None:
        result = run_kw_analyzer(
            """\
*** Test Cases ***
Example
    Run Keywords    Log    a    AND    Log    b    AND    Log    c
""",
            {
                "Run Keywords": _builtin_kw("Run Keywords"),
                "Log": _regular_kw("Log"),
            },
        )
        stmts = _keyword_call_stmts(result)
        assert len(stmts) == 1
        stmt = stmts[0]
        assert isinstance(stmt, RunKeywordCallStatement)
        assert len(stmt.inner_calls) == 3


# --- Run Keyword If (IF/ELSE/ELSE IF branches) ---


class TestRunKeywordIf:
    def test_run_keyword_if_single_branch(self, run_kw_analyzer: AnalyzerFactory) -> None:
        result = run_kw_analyzer(
            """\
*** Test Cases ***
Example
    Run Keyword If    True    Log    hello
""",
            {
                "Run Keyword If": _builtin_kw("Run Keyword If"),
                "Log": _regular_kw("Log"),
            },
        )
        stmts = _keyword_call_stmts(result)
        assert len(stmts) == 1
        stmt = stmts[0]
        assert isinstance(stmt, RunKeywordCallStatement)
        assert len(stmt.inner_calls) == 1
        assert stmt.inner_calls[0].keyword_doc is not None
        assert stmt.inner_calls[0].keyword_doc.name == "Log"

    def test_run_keyword_if_with_else(self, run_kw_analyzer: AnalyzerFactory) -> None:
        result = run_kw_analyzer(
            """\
*** Test Cases ***
Example
    Run Keyword If    True    Log    hello    ELSE    Log    world
""",
            {
                "Run Keyword If": _builtin_kw("Run Keyword If"),
                "Log": _regular_kw("Log"),
            },
        )
        stmts = _keyword_call_stmts(result)
        assert len(stmts) == 1
        stmt = stmts[0]
        assert isinstance(stmt, RunKeywordCallStatement)
        assert len(stmt.inner_calls) == 2
        assert all(inner.keyword_doc is not None and inner.keyword_doc.name == "Log" for inner in stmt.inner_calls)

    def test_run_keyword_if_with_else_if_and_else(self, run_kw_analyzer: AnalyzerFactory) -> None:
        result = run_kw_analyzer(
            """\
*** Test Cases ***
Example
    Run Keyword If    True    Log    a    ELSE IF    False    Log    b    ELSE    Log    c
""",
            {
                "Run Keyword If": _builtin_kw("Run Keyword If"),
                "Log": _regular_kw("Log"),
            },
        )
        stmts = _keyword_call_stmts(result)
        assert len(stmts) == 1
        stmt = stmts[0]
        assert isinstance(stmt, RunKeywordCallStatement)
        assert len(stmt.inner_calls) == 3

    def test_run_keyword_if_with_nested_run_keyword_in_if_branch(self, run_kw_analyzer: AnalyzerFactory) -> None:
        """IF branch contains a nested Run Keyword — must not consume ELSE tokens."""
        result = run_kw_analyzer(
            """\
*** Test Cases ***
Example
    Run Keyword If    True    Run Keyword    Log    hello    ELSE    Log    world
""",
            {
                "Run Keyword If": _builtin_kw("Run Keyword If"),
                "Run Keyword": _builtin_kw("Run Keyword"),
                "Log": _regular_kw("Log"),
            },
        )
        stmts = _keyword_call_stmts(result)
        assert len(stmts) == 1
        stmt = stmts[0]
        assert isinstance(stmt, RunKeywordCallStatement)
        # IF branch (Run Keyword → Log) + ELSE branch (Log)
        assert len(stmt.inner_calls) == 2
        # IF branch should be a RunKeywordCallStatement with Run Keyword → Log nested
        if_branch = stmt.inner_calls[0]
        assert isinstance(if_branch, RunKeywordCallStatement)
        assert if_branch.keyword_doc is not None
        assert if_branch.keyword_doc.name == "Run Keyword"
        assert len(if_branch.inner_calls) == 1
        assert if_branch.inner_calls[0].keyword_doc is not None
        assert if_branch.inner_calls[0].keyword_doc.name == "Log"
        # ELSE branch should be a plain keyword call to Log
        else_branch = stmt.inner_calls[1]
        assert else_branch.keyword_doc is not None
        assert else_branch.keyword_doc.name == "Log"

    def test_run_keyword_if_with_nested_run_keyword_in_else_branch(self, run_kw_analyzer: AnalyzerFactory) -> None:
        """ELSE branch contains a nested Run Keyword."""
        result = run_kw_analyzer(
            """\
*** Test Cases ***
Example
    Run Keyword If    True    Log    hello    ELSE    Run Keyword    Log    world
""",
            {
                "Run Keyword If": _builtin_kw("Run Keyword If"),
                "Run Keyword": _builtin_kw("Run Keyword"),
                "Log": _regular_kw("Log"),
            },
        )
        stmts = _keyword_call_stmts(result)
        assert len(stmts) == 1
        stmt = stmts[0]
        assert isinstance(stmt, RunKeywordCallStatement)
        assert len(stmt.inner_calls) == 2
        # IF branch: plain Log
        if_branch = stmt.inner_calls[0]
        assert if_branch.keyword_doc is not None
        assert if_branch.keyword_doc.name == "Log"
        # ELSE branch: Run Keyword → Log
        else_branch = stmt.inner_calls[1]
        assert isinstance(else_branch, RunKeywordCallStatement)
        assert else_branch.keyword_doc is not None
        assert else_branch.keyword_doc.name == "Run Keyword"
        assert len(else_branch.inner_calls) == 1
        assert else_branch.inner_calls[0].keyword_doc is not None
        assert else_branch.inner_calls[0].keyword_doc.name == "Log"

    def test_run_keyword_if_with_nested_run_keyword_in_else_if_branch(self, run_kw_analyzer: AnalyzerFactory) -> None:
        """ELSE IF branch contains a nested Run Keyword."""
        result = run_kw_analyzer(
            """\
*** Test Cases ***
Example
    Run Keyword If    True    Log    a    ELSE IF    False    Run Keyword    Log    b    ELSE    Log    c
""",
            {
                "Run Keyword If": _builtin_kw("Run Keyword If"),
                "Run Keyword": _builtin_kw("Run Keyword"),
                "Log": _regular_kw("Log"),
            },
        )
        stmts = _keyword_call_stmts(result)
        assert len(stmts) == 1
        stmt = stmts[0]
        assert isinstance(stmt, RunKeywordCallStatement)
        assert len(stmt.inner_calls) == 3
        # IF branch: plain Log
        assert stmt.inner_calls[0].keyword_doc is not None
        assert stmt.inner_calls[0].keyword_doc.name == "Log"
        # ELSE IF branch: Run Keyword → Log
        elif_branch = stmt.inner_calls[1]
        assert isinstance(elif_branch, RunKeywordCallStatement)
        assert elif_branch.keyword_doc is not None
        assert elif_branch.keyword_doc.name == "Run Keyword"
        assert len(elif_branch.inner_calls) == 1
        assert elif_branch.inner_calls[0].keyword_doc is not None
        assert elif_branch.inner_calls[0].keyword_doc.name == "Log"
        # ELSE branch: plain Log
        assert stmt.inner_calls[2].keyword_doc is not None
        assert stmt.inner_calls[2].keyword_doc.name == "Log"


# --- Deeply nested Run Keywords ---


class TestNestedRunKeyword:
    def test_run_keyword_nested_in_run_keyword(self, run_kw_analyzer: AnalyzerFactory) -> None:
        result = run_kw_analyzer(
            """\
*** Test Cases ***
Example
    Run Keyword    Run Keyword    Log    hello
""",
            {
                "Run Keyword": _builtin_kw("Run Keyword"),
                "Log": _regular_kw("Log"),
            },
        )
        stmts = _keyword_call_stmts(result)
        assert len(stmts) == 1
        outer = stmts[0]
        assert isinstance(outer, RunKeywordCallStatement)
        assert len(outer.inner_calls) == 1
        middle = outer.inner_calls[0]
        assert isinstance(middle, RunKeywordCallStatement)
        assert middle.keyword_doc is not None
        assert middle.keyword_doc.name == "Run Keyword"
        assert len(middle.inner_calls) == 1
        inner = middle.inner_calls[0]
        assert type(inner) is KeywordCallStatement
        assert inner.keyword_doc is not None
        assert inner.keyword_doc.name == "Log"


# --- Setup / Teardown with Run Keywords ---


class TestRunKeywordInFixtures:
    def test_setup_with_run_keyword(self, run_kw_analyzer: AnalyzerFactory) -> None:
        result = run_kw_analyzer(
            """\
*** Test Cases ***
Example
    [Setup]    Run Keyword    Log    hello
    Log    test
""",
            {
                "Run Keyword": _builtin_kw("Run Keyword"),
                "Log": _regular_kw("Log"),
            },
        )
        assert result.semantic_model is not None
        setup_stmts = [
            s
            for s in result.semantic_model.statements
            if isinstance(s, KeywordCallStatement) and s.kind == NodeKind.SETUP
        ]
        assert len(setup_stmts) == 1
        stmt = setup_stmts[0]
        assert isinstance(stmt, RunKeywordCallStatement)
        assert len(stmt.inner_calls) == 1

    def test_teardown_with_run_keyword(self, run_kw_analyzer: AnalyzerFactory) -> None:
        result = run_kw_analyzer(
            """\
*** Test Cases ***
Example
    [Teardown]    Run Keyword    Log    hello
    Log    test
""",
            {
                "Run Keyword": _builtin_kw("Run Keyword"),
                "Log": _regular_kw("Log"),
            },
        )
        assert result.semantic_model is not None
        teardown_stmts = [
            s
            for s in result.semantic_model.statements
            if isinstance(s, KeywordCallStatement) and s.kind == NodeKind.TEARDOWN
        ]
        assert len(teardown_stmts) == 1
        stmt = teardown_stmts[0]
        assert isinstance(stmt, RunKeywordCallStatement)
        assert len(stmt.inner_calls) == 1


# --- Inner call line numbers ---


class TestInnerCallLineInfo:
    def test_inner_call_has_correct_line_number(self, run_kw_analyzer: AnalyzerFactory) -> None:
        result = run_kw_analyzer(
            """\
*** Test Cases ***
Example
    Run Keyword    Log    hello
""",
            {
                "Run Keyword": _builtin_kw("Run Keyword"),
                "Log": _regular_kw("Log"),
            },
        )
        stmts = _keyword_call_stmts(result)
        stmt = stmts[0]
        assert isinstance(stmt, RunKeywordCallStatement)
        inner = stmt.inner_calls[0]
        # Inner call "Log" is on the same line as "Run Keyword" (line 3)
        assert inner.line_start == 3
        assert inner.line_end == 3


# --- Inner-call tokens are populated ---


class TestInnerCallTokens:
    def test_run_keyword_inner_call_has_keyword_and_argument_tokens(self, run_kw_analyzer: AnalyzerFactory) -> None:
        from robotcode.robot.diagnostics.semantic_analyzer.enums import TokenKind

        result = run_kw_analyzer(
            """\
*** Test Cases ***
Example
    Run Keyword    Log    hello
""",
            {
                "Run Keyword": _builtin_kw("Run Keyword"),
                "Log": _regular_kw("Log"),
            },
        )
        stmts = _keyword_call_stmts(result)
        assert isinstance(stmts[0], RunKeywordCallStatement)
        inner = stmts[0].inner_calls[0]
        kw_tokens = [t for t in inner.tokens if t.kind == TokenKind.KEYWORD]
        arg_tokens = [t for t in inner.tokens if t.kind == TokenKind.ARGUMENT]
        assert len(kw_tokens) == 1
        assert kw_tokens[0].value == "Log"
        assert len(arg_tokens) == 1
        assert arg_tokens[0].value == "hello"

    def test_run_keywords_each_inner_call_has_tokens(self, run_kw_analyzer: AnalyzerFactory) -> None:
        from robotcode.robot.diagnostics.semantic_analyzer.enums import TokenKind

        result = run_kw_analyzer(
            """\
*** Test Cases ***
Example
    Run Keywords    Log    hello    AND    Log    world
""",
            {
                "Run Keywords": _builtin_kw("Run Keywords"),
                "Log": _regular_kw("Log"),
            },
        )
        stmts = _keyword_call_stmts(result)
        assert isinstance(stmts[0], RunKeywordCallStatement)
        assert len(stmts[0].inner_calls) == 2
        for i, expected_arg in enumerate(["hello", "world"]):
            inner = stmts[0].inner_calls[i]
            assert any(t.kind == TokenKind.KEYWORD and t.value == "Log" for t in inner.tokens)
            assert any(t.kind == TokenKind.ARGUMENT and t.value == expected_arg for t in inner.tokens)


# --- Template keywords: never produce RunKeywordCallStatement ---


class TestTemplateNoRunKeyword:
    def test_test_template_is_always_plain(self, run_kw_analyzer: AnalyzerFactory) -> None:
        """Templates pass analyze_run_keywords=False, so no inner calls."""
        result = run_kw_analyzer(
            """\
*** Test Cases ***
Example
    [Template]    Run Keyword
    Log    hello
""",
            {
                "Run Keyword": _builtin_kw("Run Keyword"),
                "Log": _regular_kw("Log"),
            },
        )
        assert result.semantic_model is not None
        template_stmts = [
            s
            for s in result.semantic_model.statements
            if isinstance(s, KeywordCallStatement) and s.kind == NodeKind.TEMPLATE_KEYWORD
        ]
        assert len(template_stmts) == 1
        assert type(template_stmts[0]) is KeywordCallStatement
        assert not isinstance(template_stmts[0], RunKeywordCallStatement)
