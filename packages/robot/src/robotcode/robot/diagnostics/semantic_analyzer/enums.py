from enum import Enum


class NodeKind(Enum):
    """What kind of semantic node this is — determines valid queries.

    Covers both structural blocks (FILE, sections, control flow containers)
    and leaf statements (keyword calls, settings, imports, etc.).

    Every concrete RF AST node maps to a dedicated NodeKind — there is no
    catch-all UNKNOWN value. The analyzer is expected to know what every
    statement is.
    """

    # --- Block kinds (structural containers) ---
    # Built during Phase 2 — visit_File / visit_*Section / visit_TestCase /
    # visit_Keyword / visit_For / visit_While / visit_If / visit_Try / visit_Group
    # produce SemanticBlock / DefinitionBlock entries hooked into the parent
    # block's body; `model.root` is always populated.
    FILE = "file"
    SETTING_SECTION = "setting_section"
    TESTCASE_SECTION = "testcase_section"
    KEYWORD_SECTION = "keyword_section"
    VARIABLE_SECTION = "variable_section"
    COMMENT_SECTION = "comment_section"
    INVALID_SECTION = "invalid_section"
    TESTCASE = "testcase"
    KEYWORD = "keyword"
    FOR = "for"
    WHILE = "while"
    IF = "if"
    TRY = "try"
    GROUP = "group"

    # --- Statement kinds (leaf nodes) ---

    # Definitions
    TEST_CASE_DEF = "test_case_def"  # TestCaseName (covers tasks too)
    KEYWORD_DEF = "keyword_def"  # KeywordName
    VARIABLE_DEF = "variable_def"  # Var (RF 7.0+) and Variable (Variables section)

    # Keyword calls
    KEYWORD_CALL = "keyword_call"  # KeywordCall
    TEMPLATE_KEYWORD = "template_keyword"  # TestTemplate / Template
    TEMPLATE_DATA = "template_data"  # TemplateArguments
    SETUP = "setup"  # Fixture/Setup/TestSetup/SuiteSetup
    TEARDOWN = "teardown"  # Fixture/Teardown/TestTeardown/SuiteTeardown

    # Control flow headers
    FOR_HEADER = "for_header"  # ForHeader
    IF_HEADER = "if_header"  # IfHeader
    ELSE_IF_HEADER = "else_if_header"  # ElseIfHeader
    ELSE_HEADER = "else_header"  # ElseHeader
    INLINE_IF_HEADER = "inline_if_header"  # InlineIfHeader (no END, optional assign)
    WHILE_HEADER = "while_header"  # WhileHeader
    TRY_HEADER = "try_header"  # TryHeader
    EXCEPT_HEADER = "except_header"  # ExceptHeader
    FINALLY_HEADER = "finally_header"  # FinallyHeader
    GROUP_HEADER = "group_header"  # GroupHeader (RF 7.3+)

    # Control flow body statements
    END = "end"  # End (closes FOR/IF/WHILE/TRY/GROUP)
    RETURN_STATEMENT = "return_statement"  # ReturnStatement (RETURN keyword, RF 5.0+)
    RETURN_SETTING = "return_setting"  # Return / ReturnSetting ([Return] setting)
    BREAK_STATEMENT = "break_statement"  # Break
    CONTINUE_STATEMENT = "continue_statement"  # Continue

    # Imports
    IMPORT = "import"  # LibraryImport / ResourceImport / VariablesImport

    # Settings — every concrete RF setting statement has its own NodeKind.
    # The SettingStatement subclass still carries setting_name for display
    # (e.g. "Test Tags") but downstream code should branch on NodeKind.
    SETTING_TAGS = "setting_tags"  # [Tags] (test- or keyword-level)
    SETTING_KEYWORD_TAGS = "setting_keyword_tags"  # *** Settings *** Keyword Tags
    SETTING_DEFAULT_TAGS = "setting_default_tags"  # Default Tags (deprecated, RF < 6.0)
    SETTING_FORCE_TAGS = "setting_force_tags"  # Force Tags (deprecated)
    SETTING_TEST_TAGS = "setting_test_tags"  # Test Tags
    SETTING_DOCUMENTATION = "setting_documentation"  # [Documentation] / Documentation
    SETTING_METADATA = "setting_metadata"  # Metadata
    SETTING_TIMEOUT = "setting_timeout"  # [Timeout] / Test Timeout
    SETTING_ARGUMENTS = "setting_arguments"  # [Arguments]
    SETTING_SUITE_NAME = "setting_suite_name"  # Name (RF 7.0+)
    SETTING_OTHER = "setting_other"  # Fallback for unrecognized
    # SingleValue/MultiValue subclasses

    # Document structure
    SECTION_HEADER = "section_header"  # SectionHeader (*** Test Cases *** etc.)
    COMMENT = "comment"  # Comment lines
    EMPTY_LINE = "empty_line"  # EmptyLine
    CONFIG = "config"  # Config (RF 7.3+)
    ERROR = "error"  # Error statement (parse error)


class TokenKind(Enum):
    """What this token represents — already resolved.

    Kinds are fine-grained enough that rendering is a static table lookup:
    consumers never need Robot Framework version checks, token-value parsing,
    or statement-type inspection to decide what a token is.
    """

    # Keyword-related
    KEYWORD = "keyword"
    KEYWORD_INNER = "keyword_inner"  # inner keyword name of a Run Keyword variant
    BDD_PREFIX = "bdd_prefix"
    NAMESPACE = "namespace"

    # Variable-related
    VARIABLE = "variable"
    VARIABLE_NOT_FOUND = "variable_not_found"

    # Variable sub-parts
    VARIABLE_PREFIX = "variable_prefix"
    VARIABLE_OPEN_BRACE = "variable_open_brace"
    VARIABLE_CLOSE_BRACE = "variable_close_brace"
    VARIABLE_BASE = "variable_base"
    VARIABLE_EXTENDED = "variable_extended"
    VARIABLE_TYPE_SEPARATOR = "variable_type_separator"
    VARIABLE_TYPE_HINT = "variable_type_hint"
    VARIABLE_DEFAULT_SEPARATOR = "variable_default_separator"
    VARIABLE_DEFAULT_VALUE = "variable_default_value"
    VARIABLE_PATTERN_SEPARATOR = "variable_pattern_separator"
    VARIABLE_PATTERN = "variable_pattern"
    VARIABLE_ASSIGN_MARK = "variable_assign_mark"

    # Inline Python expression sub-parts
    VARIABLE_EXPRESSION_OPEN = "variable_expression_open"
    VARIABLE_EXPRESSION_CLOSE = "variable_expression_close"
    PYTHON_EXPRESSION = "python_expression"
    PYTHON_VARIABLE_REF = "python_variable_ref"

    # Index access sub-parts
    VARIABLE_INDEX = "variable_index"
    VARIABLE_INDEX_OPEN = "variable_index_open"
    VARIABLE_INDEX_CLOSE = "variable_index_close"
    VARIABLE_INDEX_CONTENT = "variable_index_content"

    # Text fragments
    TEXT_FRAGMENT = "text_fragment"

    # Arguments
    ARGUMENT = "argument"
    NAMED_ARGUMENT_NAME = "named_argument_name"
    NAMED_ARGUMENT_VALUE = "named_argument_value"
    PARAMETER = "parameter"  # [Arguments] definition with a default value

    # Control flow
    CONTROL_FLOW = "control_flow"
    CONDITION = "condition"
    FOR_SEPARATOR = "for_separator"  # IN / IN RANGE / IN ENUMERATE / IN ZIP
    VAR_MARKER = "var_marker"  # the VAR word (RF 7.0+)

    # Options (name=value cells on VAR / FOR / WHILE / EXCEPT)
    OPTION = "option"  # whole name=value option (VAR / FOR)
    OPTION_NAME = "option_name"  # option name half (WHILE / EXCEPT)
    OPTION_VALUE = "option_value"  # option value half (WHILE / EXCEPT)

    # Definitions
    TEST_NAME = "test_name"
    KEYWORD_NAME = "keyword_name"
    VARIABLE_NAME = "variable_name"

    # Structure
    SETTING_NAME = "setting_name"
    SETTING_IMPORT = "setting_import"  # Library / Resource / Variables, WITH NAME / AS
    IMPORT_NAME = "import_name"
    OPERATOR = "operator"  # "." in Namespace.Keyword, "=" in named args, "[" / "]"
    HEADER = "header"
    HEADER_SETTINGS = "header_settings"
    HEADER_VARIABLE = "header_variable"
    HEADER_TESTCASE = "header_testcase"
    HEADER_TASK = "header_task"
    HEADER_KEYWORD = "header_keyword"
    HEADER_COMMENT = "header_comment"
    SEPARATOR = "separator"
    CONTINUATION = "continuation"
    EOL = "eol"  # line break incl. preceding trailing whitespace — layout only, never rendered
    COMMENT = "comment"
    TAG = "tag"
    CONFIG = "config"
    ERROR = "error"


class TokenModifier(Enum):
    """Pre-computed semantic modifiers carried on a SemanticToken.

    Filled by the SemanticAnalyzer from data it already holds (keyword docs,
    embedded-argument matches, statement kind) — consumers map them to their
    output format without any re-resolution.
    """

    BUILTIN = "builtin"
    EMBEDDED = "embedded"
    DECLARATION = "declaration"
    DOCUMENTATION = "documentation"


class ForFlavor(Enum):
    """FOR loop variant."""

    IN = "IN"
    IN_RANGE = "IN RANGE"
    IN_ENUMERATE = "IN ENUMERATE"
    IN_ZIP = "IN ZIP"


class ForZipMode(Enum):
    """IN ZIP mode= option values."""

    SHORTEST = "SHORTEST"
    LONGEST = "LONGEST"
    STRICT = "STRICT"


class OnLimitAction(Enum):
    """WHILE on_limit= option values."""

    PASS = "PASS"
    FAIL = "FAIL"


class VarScope(Enum):
    """VAR scope= option values."""

    LOCAL = "LOCAL"
    TEST = "TEST"
    TASK = "TASK"
    SUITE = "SUITE"
    GLOBAL = "GLOBAL"


class ImportType(Enum):
    """Type of import."""

    LIBRARY = "LIBRARY"
    RESOURCE = "RESOURCE"
    VARIABLES = "VARIABLES"
