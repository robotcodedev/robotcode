from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional, Tuple

from .enums import (
    ForFlavor,
    ForZipMode,
    ImportType,
    NodeKind,
    OnLimitAction,
    TokenKind,
    VarScope,
)

if TYPE_CHECKING:
    from ..entities import LibraryEntry, VariableDefinition
    from ..library_doc import ArgumentSpec, KeywordDoc


@dataclass(slots=True)
class SemanticToken:
    """A single resolved token in the Semantic Model.

    Contains both position info and resolved semantic information.
    All resolution has already happened — consumers just read fields.

    Robot Framework tokens are always single-line (one cell = one line).
    Multi-line constructs use continuation lines (...) which are separate tokens
    on separate lines. Therefore a single `line` field is sufficient.
    """

    kind: TokenKind
    value: str
    line: int  # 1-indexed (matches RF Token.lineno)
    col_offset: int  # 0-indexed (matches RF Token.col_offset)
    length: int

    sub_tokens: Optional[List["SemanticToken"]] = None


@dataclass(slots=True)
class SemanticNode:
    """Common base for all nodes in the SemanticModel.

    Both statements (leaf nodes with tokens) and blocks (structural containers
    with children) share kind and position fields.
    """

    kind: NodeKind
    line_start: int = 0  # 1-indexed
    line_end: int = 0  # 1-indexed, inclusive


@dataclass(slots=True)
class SemanticStatement(SemanticNode):
    """Leaf node — a single resolved statement with tokens.

    Corresponds roughly to one RF AST node (KeywordCall, Fixture, etc.)
    but with all tokens pre-resolved and the statement kind determined.
    Subclasses add type-specific properties for completion, inlay hints, etc.

    Used directly for simple statements like BREAK, CONTINUE, COMMENT,
    END, ELSE, TRY, FINALLY, section headers.

    Subclass hierarchy:
        SemanticStatement (base)
        ├── KeywordCallStatement     — keyword calls, setup, teardown, template keyword
        │   └── RunKeywordCallStatement — Run Keyword variants with nested inner calls
        ├── ForStatement             — FOR loop header
        ├── WhileStatement           — WHILE loop header
        ├── IfStatement              — IF / ELSE IF header (including inline IF)
        ├── ExceptStatement          — EXCEPT header
        ├── VarStatement             — VAR statement (RF 7.0+)
        ├── ReturnStatement          — RETURN statement AND deprecated [Return] setting
        ├── ImportStatement          — Library / Resource / Variables import
        ├── SettingStatement         — [Tags], [Documentation], [Timeout], etc.
        ├── DefinitionStatement      — Test case / Task / Keyword definition header
        └── TemplateDataStatement    — Template argument rows
    """

    tokens: List[SemanticToken] = field(default_factory=list)


# --- Keyword-executing statements ---


@dataclass(slots=True)
class KeywordCallStatement(SemanticStatement):
    """A statement that executes a keyword: keyword calls, setup, teardown, template.

    Covers NodeKind: KEYWORD_CALL, SETUP, TEARDOWN, TEMPLATE_KEYWORD.
    """

    keyword_doc: Optional["KeywordDoc"] = None

    # Resolved library entry for namespace qualifier ("BuiltIn" in "BuiltIn.Log").
    # Only set when the keyword is called with a namespace prefix.
    lib_entry: Optional["LibraryEntry"] = None

    # Variables that receive the return value: ${result}=    My Keyword
    assign_variables: List[SemanticToken] = field(default_factory=list)


@dataclass(slots=True)
class RunKeywordCallStatement(KeywordCallStatement):
    """A keyword call containing nested keyword calls (Run Keyword variants,
    robot:keyword-call type hints).

    The outer keyword (e.g. Run Keyword If) is in keyword_doc.
    Inner keyword calls are full KeywordCallStatements with own keyword_doc,
    tokens, and potentially own inner_calls (deeply nested).

    CONTROL_FLOW tokens (ELSE, AND, ELSE IF) stay on this statement's tokens
    list — they belong to the outer Run Keyword syntax, not to any inner call.

    Only created for actual Run Keyword variants — normal keyword calls use
    KeywordCallStatement directly. isinstance(stmt, KeywordCallStatement)
    matches both types.
    """

    inner_calls: List["KeywordCallStatement"] = field(default_factory=list)


# --- Control flow statements ---


@dataclass(slots=True)
class ForStatement(SemanticStatement):
    """FOR loop header.

    Completable options depend on flavor:
    - IN RANGE: start, end, step
    - IN ENUMERATE: start= (starting index)
    - IN ZIP: mode= (SHORTEST|LONGEST|STRICT), fill=
    - IN: no options
    """

    flavor: Optional[ForFlavor] = None
    loop_variables: List[SemanticToken] = field(default_factory=list)

    start: Optional[str] = None  # IN ENUMERATE: start=
    mode: Optional[ForZipMode] = None  # IN ZIP: mode=
    fill: Optional[str] = None  # IN ZIP: fill=


@dataclass(slots=True)
class WhileStatement(SemanticStatement):
    """WHILE loop header.

    Completable options: limit=, on_limit=, on_limit_message=
    """

    condition: Optional[str] = None
    limit: Optional[str] = None
    on_limit: Optional[OnLimitAction] = None
    on_limit_message: Optional[str] = None


@dataclass(slots=True)
class IfStatement(SemanticStatement):
    """IF or ELSE IF header.

    Covers NodeKind: IF_HEADER, ELSE_IF_HEADER.
    """

    condition: Optional[str] = None

    # Inline IF assign variable: ${result}=    IF    ...
    assign_variable: Optional[SemanticToken] = None


@dataclass(slots=True)
class ExceptStatement(SemanticStatement):
    """EXCEPT header.

    Completable options: type= (GLOB|REGEXP|START|LITERAL), AS variable
    """

    patterns: List[str] = field(default_factory=list)
    pattern_type: Optional[str] = None

    # AS variable: EXCEPT    error    AS    ${err}
    as_variable: Optional[SemanticToken] = None


# --- Variable / Return statements ---


@dataclass(slots=True)
class VarStatement(SemanticStatement):
    """VAR statement (RF 7.0+).

    Completable options: scope= (LOCAL|TEST|TASK|SUITE|GLOBAL), separator=
    """

    variable_name: Optional[SemanticToken] = None
    scope: Optional[VarScope] = None
    separator: Optional[str] = None
    values: List[SemanticToken] = field(default_factory=list)


@dataclass(slots=True)
class ReturnStatement(SemanticStatement):
    """RETURN statement or deprecated [Return] setting.

    Covers NodeKind: RETURN_STATEMENT (RETURN keyword, RF 5.0+)
    and RETURN_SETTING ([Return] setting, deprecated since RF 5.0).
    """

    return_values: List[SemanticToken] = field(default_factory=list)


# --- Import statements ---


@dataclass(slots=True)
class ImportStatement(SemanticStatement):
    """Library / Resource / Variables import.

    Completable: import path, WITH NAME alias, library arguments.
    """

    import_type: Optional[ImportType] = None
    import_name: Optional[str] = None
    alias: Optional[str] = None
    arguments: List[SemanticToken] = field(default_factory=list)
    lib_entry: Optional["LibraryEntry"] = None


# --- Settings ---


@dataclass(slots=True)
class SettingStatement(SemanticStatement):
    """A setting line: [Tags], [Documentation], [Timeout], [Arguments], etc."""

    setting_name: Optional[str] = None
    argument_definitions: List[SemanticToken] = field(default_factory=list)
    tag_values: List[str] = field(default_factory=list)


# --- Definitions ---


@dataclass(slots=True)
class DefinitionStatement(SemanticStatement):
    """Test case, task, or keyword definition header.

    Covers NodeKind: TEST_CASE_DEF, KEYWORD_DEF.
    Tasks and test cases share the same AST node class (TestCase)
    in Robot Framework, so both use TEST_CASE_DEF.

    Also carries the block-local variable scope — replaces ScopeTree's LocalScope.
    Robot Framework has no nested function scopes: FOR/IF/TRY variables "leak"
    to the containing Keyword/TestCase, so one flat list per DefinitionStatement
    is sufficient.
    """

    name: Optional[str] = None
    arguments_spec: Optional["ArgumentSpec"] = None
    return_type: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    # Block-local variables with visibility positions (replaces LocalScope).
    # Each entry is (VariableDefinition, visible_from_line: int).
    # Variables are visible from their definition line to the end of this block.
    local_variables: List[Tuple["VariableDefinition", int]] = field(default_factory=list)


# --- Template data ---


@dataclass(slots=True)
class TemplateDataStatement(SemanticStatement):
    """Template argument row — not a keyword call, just argument values.

    The template keyword is in the parent test/keyword definition.
    Covers NodeKind: TEMPLATE_DATA.
    """

    template_keyword_doc: Optional["KeywordDoc"] = None


# --- Blocks (structural containers) ---


@dataclass(slots=True)
class SemanticBlock(SemanticNode):
    """Container node — structural nesting in the SemanticModel.

    Represents RF AST blocks: File, Sections, TestCase, Keyword,
    and control flow containers (FOR, WHILE, IF, TRY, GROUP).

    The `header` is the block's opening statement (e.g. ForHeader,
    IfHeader, SectionHeader). For File blocks, header is None.

    The `body` contains the block's children — a mix of statements
    and nested blocks.

    Subclass hierarchy:
        SemanticBlock (base)
        ├── DefinitionBlock  — TestCase / Keyword with scope data
        └── (base used directly for File, Sections, control flow)
    """

    header: Optional[SemanticStatement] = None
    body: List[SemanticNode] = field(default_factory=list)


@dataclass(slots=True)
class DefinitionBlock(SemanticBlock):
    """TestCase or Keyword block — carries scope and definition metadata.

    Covers NodeKind: TESTCASE, KEYWORD.

    The header is a DefinitionStatement (TEST_CASE_DEF or KEYWORD_DEF).
    Block-local variables live here because RF has no nested function scopes:
    FOR/IF/TRY variables \"leak\" to the containing Keyword/TestCase.
    """

    name: Optional[str] = None
    arguments_spec: Optional["ArgumentSpec"] = None
    return_type: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    # Block-local variables with visibility positions (replaces LocalScope).
    # Each entry is (VariableDefinition, visible_from_line: int).
    # Variables are visible from their definition line to the end of this block.
    local_variables: List[Tuple["VariableDefinition", int]] = field(default_factory=list)
