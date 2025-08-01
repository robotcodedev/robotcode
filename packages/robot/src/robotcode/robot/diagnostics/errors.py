from typing import final

DIAGNOSTICS_SOURCE_NAME = "robotcode"


@final
class Error:
    VARIABLE_NOT_FOUND = "VariableNotFound"
    VARIABLE_NOT_REPLACED = "VariableNotReplaced"
    ENVIRONMENT_VARIABLE_NOT_FOUND = "EnvironmentVariableNotFound"
    ENVIRONMENT_VARIABLE_NOT_REPLACED = "EnvironmentVariableNotReplaced"
    KEYWORD_NOT_FOUND = "KeywordNotFound"
    LIBRARY_CONTAINS_NO_KEYWORDS = "LibraryContainsNoKeywords"
    POSSIBLE_CIRCULAR_IMPORT = "PossibleCircularImport"
    CIRCULAR_IMPORT = "CircularImport"
    RESOURCE_EMPTY = "ResourceEmpty"
    IMPORT_CONTAINS_ERRORS = "ImportContainsErrors"
    RECURSIVE_IMPORT = "RecursiveImport"
    RESOURCE_ALREADY_IMPORTED = "ResourceAlreadyImported"
    VARIABLES_ALREADY_IMPORTED = "VariablesAlreadyImported"
    LIBRARY_ALREADY_IMPORTED = "LibraryAlreadyImported"
    LIBRARY_OVERRIDES_BUILTIN = "LibraryOverridesBuiltIn"
    DEPRECATED_KEYWORD = "DeprecatedKeyword"
    KEYWORD_CONTAINS_ERRORS = "KeywordContainsErrors"
    RESERVED_KEYWORD = "ReservedKeyword"
    PRIVATE_KEYWORD = "PrivateKeyword"
    INCORRECT_USE = "IncorrectUse"
    KEYWORD_NAME_EMPTY = "KeywordNameEmpty"
    CODE_UNREACHABLE = "CodeUnreachable"
    TESTCASE_NAME_EMPTY = "TestCaseNameEmpty"
    KEYWORD_CONTAINS_NORMAL_AND_EMBBEDED_ARGUMENTS = "KeywordContainsNormalAndEmbbededArguments"
    DEPRECATED_HYPHEN_TAG = "DeprecatedHyphenTag"
    DEPRECATED_RETURN_SETTING = "DeprecatedReturnSetting"
    DEPRECATED_FORCE_TAG = "DeprecatedForceTag"
    IMPORT_REQUIRES_VALUE = "ImportRequiresValue"
    KEYWORD_ERROR = "KeywordError"
    MULTIPLE_KEYWORDS = "MultipleKeywords"
    CONFLICTING_LIBRARY_KEYWORDS = "ConflictingLibraryKeywords"
    INVALID_HEADER = "InvalidHeader"
    DEPRECATED_HEADER = "DeprecatedHeader"
    OVERRIDDEN_BY_COMMANDLINE = "OverriddenByCommandLine"
    OVERRIDES_IMPORTED_VARIABLE = "OverridesImportedVariable"
    VARIABLE_ALREADY_DEFINED = "VariableAlreadyDefined"
    VARIABLE_OVERRIDDEN = "VariableOverridden"
    MODEL_ERROR = "ModelError"
    TOKEN_ERROR = "TokenError"
    ASSIGN_MARK_ALLOWED_ONLY_ON_LAST_VAR = "AssignmentMarkAllowedOnlyOnLastVariable"
