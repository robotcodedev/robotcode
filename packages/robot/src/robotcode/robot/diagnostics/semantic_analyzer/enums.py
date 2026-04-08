from enum import Enum


class NodeKind(Enum):
    """What kind of semantic node this is — determines valid queries.

    Covers both structural blocks (FILE, sections, control flow containers)
    and leaf statements (keyword calls, settings, imports, etc.).
    """

    # --- Block kinds (structural containers) ---
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
    TEST_CASE_DEF = "test_case_def"
    KEYWORD_DEF = "keyword_def"
    VARIABLE_DEF = "variable_def"

    # Keyword calls
    KEYWORD_CALL = "keyword_call"
    TEMPLATE_KEYWORD = "template_keyword"
    TEMPLATE_DATA = "template_data"
    SETUP = "setup"
    TEARDOWN = "teardown"

    # Control flow
    FOR_HEADER = "for_header"
    IF_HEADER = "if_header"
    ELSE_IF_HEADER = "else_if_header"
    ELSE_HEADER = "else_header"
    WHILE_HEADER = "while_header"
    TRY_HEADER = "try_header"
    EXCEPT_HEADER = "except_header"
    FINALLY_HEADER = "finally_header"
    END = "end"
    RETURN_STATEMENT = "return_statement"
    RETURN_SETTING = "return_setting"
    BREAK_STATEMENT = "break_statement"
    CONTINUE_STATEMENT = "continue_statement"

    # Imports and settings
    IMPORT = "import"
    SETTING = "setting"
    COMMENT = "comment"

    # Unknown / unresolvable
    UNKNOWN = "unknown"


# Backward-compatible alias during migration.
StatementKind = NodeKind


class TokenKind(Enum):
    """What this token represents — already resolved."""

    # Keyword-related
    KEYWORD = "keyword"
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

    # Control flow
    CONTROL_FLOW = "control_flow"
    CONDITION = "condition"

    # Definitions
    TEST_NAME = "test_name"
    KEYWORD_NAME = "keyword_name"
    VARIABLE_NAME = "variable_name"

    # Structure
    SETTING_NAME = "setting_name"
    IMPORT_NAME = "import_name"
    HEADER = "header"
    SEPARATOR = "separator"
    CONTINUATION = "continuation"
    COMMENT = "comment"
    TAG = "tag"
    CONFIG = "config"
    ERROR = "error"


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
