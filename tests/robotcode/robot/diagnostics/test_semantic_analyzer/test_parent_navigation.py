"""Tests for the SemanticNode.parent back-pointer and the
SemanticModel parent-walk helpers.

Covers:
- parent set on every statement / block by `_add_statement` / `_add_block`
- header.parent points to its own block (block-owns-its-header)
- root has parent=None
- RunKeywordCallStatement.inner_calls have parent = the outer Run-Keyword
  statement (also for nested cases)
- SemanticModel helpers: enclosing_definition_block, enclosing_block_of_kind,
  enclosing_section, path_from_root
"""

from typing import Callable

from robotcode.robot.diagnostics.analyzer_result import AnalyzerResult
from robotcode.robot.diagnostics.library_doc import (
    BUILTIN_LIBRARY_NAME,
    KeywordDoc,
)
from robotcode.robot.diagnostics.semantic_analyzer.enums import NodeKind
from robotcode.robot.diagnostics.semantic_analyzer.model import SemanticModel
from robotcode.robot.diagnostics.semantic_analyzer.nodes import (
    DefinitionBlock,
    DefinitionStatement,
    ForBlock,
    IfBlock,
    ImportStatement,
    KeywordCallStatement,
    RunKeywordCallStatement,
    SemanticBlock,
    SemanticNode,
    SemanticStatement,
)

AnalyzerFactory = Callable[..., AnalyzerResult]


def _model(result: AnalyzerResult) -> SemanticModel:
    assert result.semantic_model is not None
    return result.semantic_model


def _first_statement_of_kind(model: SemanticModel, kind: NodeKind) -> SemanticStatement:
    for stmt in model.statements:
        if stmt.kind is kind:
            return stmt
    raise AssertionError(f"no statement of kind {kind!r} in model")


def _find_block(node: SemanticBlock, predicate: Callable[[SemanticBlock], bool]) -> SemanticBlock:
    if predicate(node):
        return node
    for child in node.body:
        if isinstance(child, SemanticBlock):
            try:
                return _find_block(child, predicate)
            except AssertionError:
                continue
    raise AssertionError("no matching block found")


# ---------------------------------------------------------------------------
# Basic wiring: every node knows its parent
# ---------------------------------------------------------------------------


class TestRootHasNoParent:
    def test_file_root_parent_is_none(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory("*** Test Cases ***\nT\n    Log    hi\n")
        model = _model(result)
        assert model.root is not None
        assert model.root.parent is None
        assert model.root.kind is NodeKind.FILE


class TestStatementParentChain:
    def test_section_parent_is_root(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory("*** Test Cases ***\nT\n    Log    hi\n")
        model = _model(result)
        assert model.root is not None
        section = model.root.body[0]
        assert isinstance(section, SemanticBlock)
        assert section.kind is NodeKind.TESTCASE_SECTION
        assert section.parent is model.root

    def test_definition_block_parent_is_section(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory("*** Test Cases ***\nT\n    Log    hi\n")
        model = _model(result)
        assert model.root is not None
        section = model.root.body[0]
        assert isinstance(section, SemanticBlock)
        defn = next(child for child in section.body if isinstance(child, DefinitionBlock))
        assert defn.parent is section

    def test_section_header_parent_is_section(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory("*** Test Cases ***\nT\n    Log    hi\n")
        model = _model(result)
        assert model.root is not None
        section = model.root.body[0]
        assert isinstance(section, SemanticBlock)
        section_header = next(
            child
            for child in section.body
            if isinstance(child, SemanticStatement) and child.kind is NodeKind.SECTION_HEADER
        )
        assert section_header.parent is section

    def test_definition_header_parent_is_definition_block(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory("*** Test Cases ***\nT\n    Log    hi\n")
        model = _model(result)
        defn_stmt = _first_statement_of_kind(model, NodeKind.TEST_CASE_DEF)
        assert isinstance(defn_stmt, DefinitionStatement)
        assert isinstance(defn_stmt.parent, DefinitionBlock)

    def test_keyword_call_in_test_parent_is_definition_block(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory("*** Test Cases ***\nT\n    Log    hi\n")
        model = _model(result)
        kw_call = _first_statement_of_kind(model, NodeKind.KEYWORD_CALL)
        assert isinstance(kw_call.parent, DefinitionBlock)

    def test_import_statement_parent_is_setting_section(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            "*** Settings ***\nLibrary    Collections\n*** Test Cases ***\nT\n    Log    hi\n",
        )
        model = _model(result)
        imp = next(stmt for stmt in model.statements if isinstance(stmt, ImportStatement))
        assert isinstance(imp.parent, SemanticBlock)
        assert imp.parent.kind is NodeKind.SETTING_SECTION


# ---------------------------------------------------------------------------
# Control-flow blocks: header.parent is the block; body.parent is the block
# ---------------------------------------------------------------------------


class TestControlFlowParentWiring:
    def test_for_header_parent_is_for_block(self, analyzer_factory: AnalyzerFactory) -> None:
        text = "*** Test Cases ***\nT\n    FOR    ${i}    IN RANGE    3\n        Log    ${i}\n    END\n"
        result = analyzer_factory(text)
        model = _model(result)
        assert model.root is not None
        for_block = _find_block(model.root, lambda b: isinstance(b, ForBlock))
        assert for_block.header is not None
        assert for_block.header.parent is for_block

    def test_for_body_statement_parent_is_for_block(self, analyzer_factory: AnalyzerFactory) -> None:
        text = "*** Test Cases ***\nT\n    FOR    ${i}    IN RANGE    3\n        Log    ${i}\n    END\n"
        result = analyzer_factory(text)
        model = _model(result)
        assert model.root is not None
        for_block = _find_block(model.root, lambda b: isinstance(b, ForBlock))
        body_call = next(child for child in for_block.body if isinstance(child, KeywordCallStatement))
        assert body_call.parent is for_block

    def test_if_header_parent_is_if_block(self, analyzer_factory: AnalyzerFactory) -> None:
        text = "*** Test Cases ***\nT\n    IF    True\n        Log    yes\n    END\n"
        result = analyzer_factory(text)
        model = _model(result)
        assert model.root is not None
        if_block = _find_block(model.root, lambda b: isinstance(b, IfBlock))
        assert if_block.header is not None
        assert if_block.header.parent is if_block


# ---------------------------------------------------------------------------
# RunKeyword inner_calls
# ---------------------------------------------------------------------------


def _builtin_run_kw_doc(name: str) -> KeywordDoc:
    """Build a BuiltIn-namespaced KeywordDoc that the analyzer recognizes as a
    Run Keyword variant via the hardcoded-names path (`is_any_run_keyword`)."""
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
    )


def _regular_kw_doc(name: str) -> KeywordDoc:
    return KeywordDoc(
        line_no=-1,
        col_offset=-1,
        end_line_no=-1,
        end_col_offset=-1,
        source=None,
        name=name,
        libname="MyLib",
        arguments=[],
        arguments_spec=None,
    )


class TestRunKeywordInnerCallsParent:
    def test_inner_call_parent_is_outer_run_keyword_via_analyzer(
        self,
        analyzer_factory: AnalyzerFactory,
        make_library_doc_mock: Callable[..., object],
    ) -> None:
        text = "*** Test Cases ***\nT\n    Run Keyword    Log    hello\n"
        result = analyzer_factory(
            text,
            keyword_map={
                "Run Keyword": _builtin_run_kw_doc("Run Keyword"),
                "Log": _regular_kw_doc("Log"),
            },
            library_doc=make_library_doc_mock(),
        )
        model = _model(result)
        outer = _first_statement_of_kind(model, NodeKind.KEYWORD_CALL)
        assert isinstance(outer, RunKeywordCallStatement), (
            f"expected RunKeywordCallStatement, got {type(outer).__name__}"
        )
        assert outer.inner_calls, "expected inner Log call"
        for inner in outer.inner_calls:
            assert inner.parent is outer, f"inner call {inner!r} should have outer Run-Keyword as parent"

    def test_inner_call_parent_via_post_init_only(self) -> None:
        # Pure unit test — don't go through the analyzer at all. Verifies that
        # __post_init__ wires parent for any RunKeywordCallStatement, regardless
        # of where it's constructed.
        inner_a = KeywordCallStatement(kind=NodeKind.KEYWORD_CALL)
        inner_b = KeywordCallStatement(kind=NodeKind.KEYWORD_CALL)
        outer = RunKeywordCallStatement(
            kind=NodeKind.KEYWORD_CALL,
            inner_calls=[inner_a, inner_b],
        )
        assert inner_a.parent is outer
        assert inner_b.parent is outer

    def test_nested_run_keyword_parent_chain(self) -> None:
        # Run Keyword If → Run Keyword → Log : two levels of nesting.
        leaf = KeywordCallStatement(kind=NodeKind.KEYWORD_CALL)
        mid = RunKeywordCallStatement(
            kind=NodeKind.KEYWORD_CALL,
            inner_calls=[leaf],
        )
        top = RunKeywordCallStatement(
            kind=NodeKind.KEYWORD_CALL,
            inner_calls=[mid],
        )
        assert leaf.parent is mid
        assert mid.parent is top
        assert top.parent is None  # not yet wired into a block


# ---------------------------------------------------------------------------
# SemanticModel helper methods
# ---------------------------------------------------------------------------


class TestEnclosingDefinitionBlock:
    def test_keyword_call_resolves_to_test_case(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory("*** Test Cases ***\nT\n    Log    hi\n")
        model = _model(result)
        kw_call = _first_statement_of_kind(model, NodeKind.KEYWORD_CALL)

        defn = SemanticModel.enclosing_definition_block(kw_call)
        assert isinstance(defn, DefinitionBlock)
        assert defn.kind is NodeKind.TESTCASE
        assert defn.name == "T"

    def test_for_loop_body_resolves_to_test_case(self, analyzer_factory: AnalyzerFactory) -> None:
        text = "*** Test Cases ***\nT\n    FOR    ${i}    IN RANGE    3\n        Log    ${i}\n    END\n"
        result = analyzer_factory(text)
        model = _model(result)
        kw_call = _first_statement_of_kind(model, NodeKind.KEYWORD_CALL)
        defn = SemanticModel.enclosing_definition_block(kw_call)
        assert isinstance(defn, DefinitionBlock)
        assert defn.name == "T"

    def test_import_returns_none(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            "*** Settings ***\nLibrary    Collections\n*** Test Cases ***\nT\n    Log    hi\n",
        )
        model = _model(result)
        imp = next(stmt for stmt in model.statements if isinstance(stmt, ImportStatement))
        assert SemanticModel.enclosing_definition_block(imp) is None


class TestEnclosingBlockOfKind:
    def test_finds_for_block_from_inner_call(self, analyzer_factory: AnalyzerFactory) -> None:
        text = "*** Test Cases ***\nT\n    FOR    ${i}    IN RANGE    3\n        Log    ${i}\n    END\n"
        result = analyzer_factory(text)
        model = _model(result)
        kw_call = _first_statement_of_kind(model, NodeKind.KEYWORD_CALL)
        for_block = SemanticModel.enclosing_block_of_kind(kw_call, frozenset({NodeKind.FOR}))
        assert isinstance(for_block, ForBlock)

    def test_returns_none_when_no_match(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory("*** Test Cases ***\nT\n    Log    hi\n")
        model = _model(result)
        kw_call = _first_statement_of_kind(model, NodeKind.KEYWORD_CALL)
        assert SemanticModel.enclosing_block_of_kind(kw_call, frozenset({NodeKind.FOR})) is None


class TestEnclosingSection:
    def test_keyword_call_finds_testcase_section(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory("*** Test Cases ***\nT\n    Log    hi\n")
        model = _model(result)
        kw_call = _first_statement_of_kind(model, NodeKind.KEYWORD_CALL)
        section = SemanticModel.enclosing_section(kw_call)
        assert section is not None
        assert section.kind is NodeKind.TESTCASE_SECTION

    def test_import_finds_settings_section(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory(
            "*** Settings ***\nLibrary    Collections\n*** Test Cases ***\nT\n    Log    hi\n",
        )
        model = _model(result)
        imp = next(stmt for stmt in model.statements if isinstance(stmt, ImportStatement))
        section = SemanticModel.enclosing_section(imp)
        assert section is not None
        assert section.kind is NodeKind.SETTING_SECTION

    def test_root_returns_none(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory("*** Test Cases ***\nT\n    Log    hi\n")
        model = _model(result)
        assert model.root is not None
        assert SemanticModel.enclosing_section(model.root) is None


class TestPathFromRoot:
    def test_chain_for_keyword_call_in_for_loop(self, analyzer_factory: AnalyzerFactory) -> None:
        text = "*** Test Cases ***\nT\n    FOR    ${i}    IN RANGE    3\n        Log    ${i}\n    END\n"
        result = analyzer_factory(text)
        model = _model(result)
        kw_call = _first_statement_of_kind(model, NodeKind.KEYWORD_CALL)
        chain = SemanticModel.path_from_root(kw_call)

        # Expected order: FILE → TESTCASE_SECTION → TESTCASE → FOR → KEYWORD_CALL
        kinds = [n.kind for n in chain]
        assert kinds == [
            NodeKind.FILE,
            NodeKind.TESTCASE_SECTION,
            NodeKind.TESTCASE,
            NodeKind.FOR,
            NodeKind.KEYWORD_CALL,
        ]

    def test_root_chain_is_just_root(self, analyzer_factory: AnalyzerFactory) -> None:
        result = analyzer_factory("*** Test Cases ***\nT\n    Log    hi\n")
        model = _model(result)
        assert model.root is not None
        chain = SemanticModel.path_from_root(model.root)
        assert chain == [model.root]


# ---------------------------------------------------------------------------
# parent stays out of repr / equality
# ---------------------------------------------------------------------------


class TestParentExcludedFromReprAndEquality:
    def test_parent_not_in_repr(self) -> None:
        # Repr would otherwise infinitely recurse through the parent cycle.
        block = SemanticBlock(kind=NodeKind.FILE)
        stmt = SemanticStatement(kind=NodeKind.COMMENT, parent=block)
        block.body.append(stmt)
        text = repr(stmt)
        assert "parent" not in text

    def test_parent_not_in_equality(self) -> None:
        # Two leaves with identical fields but different parents must compare
        # equal (parent is excluded from __eq__).
        parent_a = SemanticBlock(kind=NodeKind.TESTCASE_SECTION)
        parent_b = SemanticBlock(kind=NodeKind.KEYWORD_SECTION)
        stmt_a = SemanticStatement(kind=NodeKind.COMMENT, parent=parent_a)
        stmt_b = SemanticStatement(kind=NodeKind.COMMENT, parent=parent_b)
        assert stmt_a == stmt_b


# ---------------------------------------------------------------------------
# Cross-cutting integration test
# ---------------------------------------------------------------------------


def test_every_non_root_node_has_a_parent(analyzer_factory: AnalyzerFactory) -> None:
    """Walking the tree from root, every reachable node except root itself
    must have a parent that points back to the directly enclosing node."""
    text = (
        "*** Settings ***\n"
        "Library    Collections\n"
        "*** Test Cases ***\n"
        "T\n"
        "    FOR    ${i}    IN RANGE    3\n"
        "        IF    ${i} > 1\n"
        "            Log    ${i}\n"
        "        END\n"
        "    END\n"
        "*** Keywords ***\n"
        "My KW\n"
        "    Log    hi\n"
    )
    result = analyzer_factory(text)
    model = _model(result)
    assert model.root is not None
    assert model.root.parent is None

    def visit(block: SemanticBlock) -> None:
        if block.header is not None:
            assert block.header.parent is block, f"header of {block.kind} must have block as parent"
        for child in block.body:
            assert child.parent is block, f"body child {child.kind} of {block.kind} has wrong parent"
            if isinstance(child, SemanticBlock):
                visit(child)

    visit(model.root)


def test_parent_pointers_survive_pickle(analyzer_factory: AnalyzerFactory) -> None:
    """Pickle handles the parent cycle natively via the memo table — after
    unpickling the parent chain must still be intact."""
    import pickle

    text = "*** Test Cases ***\nT\n    FOR    ${i}    IN RANGE    3\n        Log    ${i}\n    END\n"
    result = analyzer_factory(text)
    model = _model(result)

    blob = pickle.dumps(model)
    restored: SemanticModel = pickle.loads(blob)
    assert restored.root is not None

    restored_kw = _first_statement_of_kind(restored, NodeKind.KEYWORD_CALL)
    chain_kinds = [n.kind for n in SemanticModel.path_from_root(restored_kw)]
    assert chain_kinds == [
        NodeKind.FILE,
        NodeKind.TESTCASE_SECTION,
        NodeKind.TESTCASE,
        NodeKind.FOR,
        NodeKind.KEYWORD_CALL,
    ]


# ---------------------------------------------------------------------------
# Type sanity: parent is typed as SemanticNode (not SemanticBlock) so it can
# also point at a Statement (RunKeyword inner_calls case).
# ---------------------------------------------------------------------------


def test_parent_type_accepts_statement() -> None:
    # SemanticNode.parent is typed as SemanticNode, so a Statement can be a
    # parent. This is the case for RunKeyword inner_calls — the test verifies
    # the runtime type, not just the static type.
    inner = KeywordCallStatement(kind=NodeKind.KEYWORD_CALL)
    RunKeywordCallStatement(kind=NodeKind.KEYWORD_CALL, inner_calls=[inner])
    parent: SemanticNode | None = inner.parent
    assert isinstance(parent, KeywordCallStatement)
    assert not isinstance(parent, SemanticBlock)  # type: ignore[unreachable]
