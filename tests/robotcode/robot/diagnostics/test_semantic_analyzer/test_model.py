"""Tests for SemanticModel query API and data structures."""

from robotcode.robot.diagnostics.semantic_analyzer.enums import NodeKind, TokenKind
from robotcode.robot.diagnostics.semantic_analyzer.model import SemanticModel
from robotcode.robot.diagnostics.semantic_analyzer.nodes import (
    DefinitionBlock,
    DefinitionStatement,
    ExceptStatement,
    ForStatement,
    IfStatement,
    ImportStatement,
    KeywordCallStatement,
    ReturnStatement,
    RunKeywordCallStatement,
    SemanticBlock,
    SemanticStatement,
    SemanticToken,
    SettingStatement,
    TemplateDataStatement,
    VarStatement,
    WhileStatement,
)


def _token(kind: TokenKind, value: str, line: int, col: int, length: int) -> SemanticToken:
    return SemanticToken(kind=kind, value=value, line=line, col_offset=col, length=length)


def _token_with_subs(
    kind: TokenKind, value: str, line: int, col: int, length: int, sub_tokens: list[SemanticToken]
) -> SemanticToken:
    return SemanticToken(kind=kind, value=value, line=line, col_offset=col, length=length, sub_tokens=sub_tokens)


class TestSemanticToken:
    def test_basic_creation(self) -> None:
        t = _token(TokenKind.KEYWORD, "Log", 1, 4, 3)
        assert t.kind == TokenKind.KEYWORD
        assert t.value == "Log"
        assert t.line == 1
        assert t.col_offset == 4
        assert t.length == 3
        assert t.sub_tokens is None

    def test_with_sub_tokens(self) -> None:
        sub = _token(TokenKind.VARIABLE, "${name}", 1, 4, 7)
        parent = _token_with_subs(TokenKind.ARGUMENT, "${name}", 1, 4, 7, [sub])
        assert parent.sub_tokens is not None
        assert len(parent.sub_tokens) == 1
        assert parent.sub_tokens[0].kind == TokenKind.VARIABLE


class TestSemanticStatement:
    def test_base_statement(self) -> None:
        stmt = SemanticStatement(kind=NodeKind.UNKNOWN, line_start=5, line_end=5)
        assert stmt.kind == NodeKind.UNKNOWN
        assert stmt.tokens == []

    def test_keyword_call_statement(self) -> None:
        stmt = KeywordCallStatement(
            kind=NodeKind.KEYWORD_CALL,
            tokens=[_token(TokenKind.KEYWORD, "Log", 3, 4, 3)],
            line_start=3,
            line_end=3,
        )
        assert stmt.kind == NodeKind.KEYWORD_CALL
        assert stmt.keyword_doc is None
        assert stmt.lib_entry is None
        assert stmt.assign_variables == []

    def test_run_keyword_call_inherits(self) -> None:
        stmt = RunKeywordCallStatement(
            kind=NodeKind.KEYWORD_CALL,
            line_start=5,
            line_end=5,
        )
        assert isinstance(stmt, KeywordCallStatement)
        assert stmt.inner_calls == []

    def test_for_statement(self) -> None:
        from robotcode.robot.diagnostics.semantic_analyzer.enums import ForFlavor, ForZipMode

        stmt = ForStatement(
            kind=NodeKind.FOR_HEADER,
            flavor=ForFlavor.IN_ZIP,
            mode=ForZipMode.STRICT,
            line_start=4,
            line_end=4,
        )
        assert stmt.flavor == ForFlavor.IN_ZIP
        assert stmt.mode == ForZipMode.STRICT
        assert stmt.loop_variables == []

    def test_while_statement(self) -> None:
        from robotcode.robot.diagnostics.semantic_analyzer.enums import OnLimitAction

        stmt = WhileStatement(
            kind=NodeKind.WHILE_HEADER,
            condition="${x} > 0",
            limit="10",
            on_limit=OnLimitAction.PASS,
            line_start=6,
            line_end=6,
        )
        assert stmt.condition == "${x} > 0"
        assert stmt.on_limit == OnLimitAction.PASS

    def test_if_statement(self) -> None:
        stmt = IfStatement(
            kind=NodeKind.IF_HEADER,
            condition="${flag}",
            line_start=7,
            line_end=7,
        )
        assert stmt.condition == "${flag}"
        assert stmt.assign_variable is None

    def test_except_statement(self) -> None:
        stmt = ExceptStatement(
            kind=NodeKind.EXCEPT_HEADER,
            patterns=["ValueError", "TypeError"],
            pattern_type="GLOB",
            line_start=10,
            line_end=10,
        )
        assert len(stmt.patterns) == 2
        assert stmt.as_variable is None

    def test_var_statement(self) -> None:
        from robotcode.robot.diagnostics.semantic_analyzer.enums import VarScope

        stmt = VarStatement(
            kind=NodeKind.VARIABLE_DEF,
            variable_name=_token(TokenKind.VARIABLE_NAME, "${result}", 3, 4, 9),
            scope=VarScope.SUITE,
            line_start=3,
            line_end=3,
        )
        assert stmt.scope == VarScope.SUITE
        assert stmt.variable_name is not None
        assert stmt.variable_name.value == "${result}"

    def test_return_statement(self) -> None:
        stmt = ReturnStatement(
            kind=NodeKind.RETURN_STATEMENT,
            return_values=[_token(TokenKind.ARGUMENT, "${x}", 8, 11, 4)],
            line_start=8,
            line_end=8,
        )
        assert len(stmt.return_values) == 1

    def test_import_statement(self) -> None:
        from robotcode.robot.diagnostics.semantic_analyzer.enums import ImportType

        stmt = ImportStatement(
            kind=NodeKind.IMPORT,
            import_type=ImportType.LIBRARY,
            import_name="BuiltIn",
            line_start=2,
            line_end=2,
        )
        assert stmt.import_type == ImportType.LIBRARY
        assert stmt.alias is None

    def test_setting_statement(self) -> None:
        stmt = SettingStatement(
            kind=NodeKind.SETTING,
            setting_name="Tags",
            tag_values=["smoke", "regression"],
            line_start=3,
            line_end=3,
        )
        assert stmt.setting_name == "Tags"
        assert len(stmt.tag_values) == 2

    def test_definition_statement(self) -> None:
        stmt = DefinitionStatement(
            kind=NodeKind.TEST_CASE_DEF,
            name="My Test",
            line_start=2,
            line_end=15,
        )
        assert stmt.name == "My Test"
        assert stmt.local_variables == []
        assert stmt.tags == []

    def test_template_data_statement(self) -> None:
        stmt = TemplateDataStatement(
            kind=NodeKind.TEMPLATE_DATA,
            tokens=[_token(TokenKind.ARGUMENT, "arg1", 5, 4, 4)],
            line_start=5,
            line_end=5,
        )
        assert stmt.template_keyword_doc is None


class TestSemanticModelBuildIndex:
    def _build_model(self, statements: list[SemanticStatement]) -> SemanticModel:
        model = SemanticModel(statements=statements)
        model.build_index()
        return model

    def test_empty_model(self) -> None:
        model = self._build_model([])
        assert model.statement_at(1) is None
        assert model.token_at(1, 0) is None
        assert model.token_path_at(1, 0) == []

    def test_single_statement(self) -> None:
        stmt = SemanticStatement(kind=NodeKind.UNKNOWN, line_start=1, line_end=1)
        model = self._build_model([stmt])
        assert model.statement_at(1) is stmt
        assert model.statement_at(2) is None

    def test_definition_block_contains_body(self) -> None:
        defn = DefinitionStatement(
            kind=NodeKind.TEST_CASE_DEF,
            name="My Test",
            line_start=2,
            line_end=10,
        )
        body_stmt = KeywordCallStatement(
            kind=NodeKind.KEYWORD_CALL,
            tokens=[_token(TokenKind.KEYWORD, "Log", 4, 4, 3)],
            line_start=4,
            line_end=4,
        )
        model = self._build_model([defn, body_stmt])

        # Line 4 should return the more specific body_stmt (smaller range)
        assert model.statement_at(4) is body_stmt

        # Line 2 (definition header) should return defn
        assert model.statement_at(2) is defn

        # Line 6 (within defn but no explicit stmt): falls back to legacy definition
        assert model.statement_at(6) is defn

    def test_enclosing_definition_legacy(self) -> None:
        """Legacy path: DefinitionStatement in flat list, no tree."""
        defn = DefinitionStatement(
            kind=NodeKind.KEYWORD_DEF,
            name="My KW",
            line_start=5,
            line_end=20,
        )
        model = self._build_model([defn])
        # enclosing_definition falls back to legacy DefinitionStatement
        assert model.enclosing_definition(10) is defn
        assert model.enclosing_definition(4) is None
        assert model.enclosing_definition(21) is None
        # statement_at also returns it
        assert model.statement_at(10) is defn

    def test_enclosing_definition_with_block(self) -> None:
        """New path: DefinitionBlock in tree."""
        header = DefinitionStatement(
            kind=NodeKind.KEYWORD_DEF,
            name="My KW",
            line_start=5,
            line_end=5,
        )
        block = DefinitionBlock(
            kind=NodeKind.KEYWORD,
            header=header,
            name="My KW",
            line_start=5,
            line_end=20,
        )
        root = SemanticBlock(kind=NodeKind.FILE, body=[block], line_start=1, line_end=20)
        model = SemanticModel(root=root, statements=[header])
        model.build_index()
        assert model.enclosing_definition(10) is block
        assert model.enclosing_definition(4) is None
        assert model.enclosing_definition(21) is None


class TestSemanticModelTokenQueries:
    def test_token_at_simple(self) -> None:
        token = _token(TokenKind.KEYWORD, "Log", 3, 4, 3)
        stmt = KeywordCallStatement(
            kind=NodeKind.KEYWORD_CALL,
            tokens=[token],
            line_start=3,
            line_end=3,
        )
        model = SemanticModel(statements=[stmt])
        model.build_index()

        assert model.token_at(3, 4) is token
        assert model.token_at(3, 6) is token
        assert model.token_at(3, 7) is None  # past end
        assert model.token_at(3, 3) is None  # before start

    def test_token_at_with_sub_tokens(self) -> None:
        inner = _token(TokenKind.VARIABLE, "${name}", 3, 10, 7)
        outer = _token_with_subs(TokenKind.ARGUMENT, "${name}", 3, 10, 7, [inner])
        stmt = KeywordCallStatement(
            kind=NodeKind.KEYWORD_CALL,
            tokens=[_token(TokenKind.KEYWORD, "Log", 3, 4, 3), outer],
            line_start=3,
            line_end=3,
        )
        model = SemanticModel(statements=[stmt])
        model.build_index()

        # Should descend into sub_tokens
        result = model.token_at(3, 12)
        assert result is inner

    def test_token_at_nested_sub_tokens(self) -> None:
        var_base = _token(TokenKind.VARIABLE_BASE, "name", 3, 12, 4)
        var_prefix = _token(TokenKind.VARIABLE_PREFIX, "$", 3, 10, 1)
        var_open = _token(TokenKind.VARIABLE_OPEN_BRACE, "{", 3, 11, 1)
        var_close = _token(TokenKind.VARIABLE_CLOSE_BRACE, "}", 3, 16, 1)
        variable = _token_with_subs(
            TokenKind.VARIABLE,
            "${name}",
            3,
            10,
            7,
            [var_prefix, var_open, var_base, var_close],
        )
        arg = _token_with_subs(TokenKind.ARGUMENT, "${name}", 3, 10, 7, [variable])
        stmt = KeywordCallStatement(
            kind=NodeKind.KEYWORD_CALL,
            tokens=[arg],
            line_start=3,
            line_end=3,
        )
        model = SemanticModel(statements=[stmt])
        model.build_index()

        # Should reach deepest: VARIABLE_BASE
        result = model.token_at(3, 13)
        assert result is var_base

        # VARIABLE_PREFIX at col 10
        result = model.token_at(3, 10)
        assert result is var_prefix

    def test_token_path_at(self) -> None:
        var_base = _token(TokenKind.VARIABLE_BASE, "name", 3, 12, 4)
        variable = _token_with_subs(TokenKind.VARIABLE, "${name}", 3, 10, 7, [var_base])
        arg = _token_with_subs(TokenKind.ARGUMENT, "${name}", 3, 10, 7, [variable])
        stmt = KeywordCallStatement(
            kind=NodeKind.KEYWORD_CALL,
            tokens=[arg],
            line_start=3,
            line_end=3,
        )
        model = SemanticModel(statements=[stmt])
        model.build_index()

        path = model.token_path_at(3, 13)
        assert len(path) == 3
        assert path[0] is arg
        assert path[1] is variable
        assert path[2] is var_base

    def test_token_path_at_no_match(self) -> None:
        model = SemanticModel(statements=[])
        model.build_index()
        assert model.token_path_at(1, 0) == []


class TestNormalizeVariableName:
    def test_simple_variable(self) -> None:
        assert SemanticModel._normalize_variable_name("${name}") == "${name}"

    def test_list_variable(self) -> None:
        assert SemanticModel._normalize_variable_name("@{items}") == "@{items}"

    def test_dict_variable(self) -> None:
        assert SemanticModel._normalize_variable_name("&{config}") == "&{config}"

    def test_env_variable(self) -> None:
        assert SemanticModel._normalize_variable_name("%{HOME}") == "%{HOME}"

    def test_index_access(self) -> None:
        assert SemanticModel._normalize_variable_name("${var}[0]") == "${var}"

    def test_multiple_index_access(self) -> None:
        assert SemanticModel._normalize_variable_name("${var}[0][key]") == "${var}"

    def test_extended_dot(self) -> None:
        assert SemanticModel._normalize_variable_name("${obj.attr}") == "${obj}"

    def test_extended_space(self) -> None:
        assert SemanticModel._normalize_variable_name("${SPACE * 5}") == "${SPACE}"

    def test_inline_python(self) -> None:
        assert SemanticModel._normalize_variable_name("${{len(items)}}") is None

    def test_empty_string(self) -> None:
        assert SemanticModel._normalize_variable_name("") is None

    def test_no_extended_syntax(self) -> None:
        assert SemanticModel._normalize_variable_name("${simple}") == "${simple}"
