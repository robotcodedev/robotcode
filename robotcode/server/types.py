import re
from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional, Union


from pydantic import BaseModel

ProgressToken = Union[str, int]
DocumentUri = str


class Model(BaseModel):
    class Config:

        allow_population_by_field_name = True
        use_enum_values = True

        @classmethod
        def alias_generator(cls, string: str) -> str:
            # this is the same as `alias_generator = to_camel` above
            string = re.sub(r"^[\-_\.]", "", str(string))
            if not string:
                return string
            return str(string[0]).lower() + re.sub(
                r"[\-_\.\s]([a-z])",
                lambda matched: str(matched.group(1)).upper(),
                string[1:],
            )


class WorkDoneProgressParams(Model):
    work_done_token: Optional[ProgressToken] = None


class ClientInfo(Model):
    name: str
    version: Optional[str] = None


class TraceValue(Enum):
    OFF = "off"
    MESSAGE = "message"
    VERBOSE = "verbose"


class WorkspaceFolder(Model):
    uri: DocumentUri
    name: str


class TextDocumentSyncClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None
    will_save: Optional[bool] = None
    will_save_wait_until: Optional[bool] = None
    did_save: Optional[bool] = None


class ResourceOperationKind(Enum):
    CREATE = "create"
    RENAME = "rename"
    DELETE = "delete"


class FailureHandlingKind(Enum):
    ABORT = "abort"
    TRANSACTIONAL = "transactional"
    TEXTONLYTRANSACTIONAL = "textOnlyTransactional"
    UNDO = "undo"


class WorkspaceEditClientCapabilities(Model):
    document_changes: Optional[bool] = None
    resource_operations: Optional[List[ResourceOperationKind]] = None
    failure_handling: Optional[FailureHandlingKind] = None
    normalizes_line_endings: Optional[bool] = None

    class _ChangeAnnotationSupport(Model):
        groups_on_label: Optional[bool] = None

    change_annotation_support: Optional[_ChangeAnnotationSupport] = None


class DidChangeConfigurationClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None


class DidChangeWatchedFilesClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None


class ExecuteCommandClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None


class SemanticTokensWorkspaceClientCapabilities(Model):
    refresh_support: Optional[bool] = None


class CodeLensWorkspaceClientCapabilities(Model):
    refresh_support: Optional[bool] = None


class SymbolKind(IntEnum):
    FILE = 1
    MODULE = 2
    NAMESPACE = 3
    PACKAGE = 4
    CLASS = 5
    METHOD = 6
    PROPERTY = 7
    FIELD = 8
    CONSTRUCTOR = 9
    ENUM = 10
    INTERFACE = 11
    FUNCTION = 12
    VARIABLE = 13
    CONSTANT = 14
    STRING = 15
    NUMBER = 16
    BOOLEAN = 17
    ARRAY = 18
    OBJECT = 19
    KEY = 20
    NULL = 21
    ENUMMEMBER = 22
    STRUCT = 23
    EVENT = 24
    OPERATOR = 25
    TYPEPARAMETER = 26


class MarkupKind(Enum):
    PLAINTEXT = "plaintext"
    MARKDOWN = "markdown"


class CompletionItemTag(IntEnum):
    Deprecated = 1


class SymbolTag(IntEnum):
    Deprecated = 1


class InsertTextMode(IntEnum):
    AS_IS = 1
    ADJUST_INDENTATION = 2


class WorkspaceSymbolClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None

    class _SymbolKind(Model):
        value_set: List[SymbolKind]

    symbol_kind: Optional[_SymbolKind] = None

    class _TagSupport(Model):
        value_set: List[SymbolTag]

    tag_support: Optional[_TagSupport] = None


class CompletionItemKind(IntEnum):
    TEXT = 1
    METHOD = 2
    FUNCTION = 3
    CONSTRUCTOR = 4
    FIELD = 5
    VARIABLE = 6
    CLASS = 7
    INTERFACE = 8
    MODULE = 9
    PROPERTY = 10
    UNIT = 11
    VALUE = 12
    ENUM = 13
    KEYWORD = 14
    SNIPPET = 15
    COLOR = 16
    FILE = 17
    REFERENCE = 18
    FOLDER = 19
    ENUMMEMBER = 20
    CONSTANT = 21
    STRUCT = 22
    EVENT = 23
    OPERATOR = 24
    TYPEPARAMETER = 25


class CompletionClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None

    class _CompletionItem(Model):
        snippet_support: Optional[bool] = None
        commit_characters_support: Optional[bool] = None
        documentation_format: Optional[List[MarkupKind]] = None
        deprecated_support: Optional[bool] = None
        preselect_support: Optional[bool] = None

        class _TagSupport(Model):
            value_set: List[CompletionItemTag]

        tag_support: Optional[_TagSupport] = None
        insert_replace_support: Optional[bool] = None

        class _ResolveSupport(Model):
            properties: List[str]

        resolve_support: Optional[_ResolveSupport]

        class _InsertTextModeSupport(Model):
            value_set: List[InsertTextMode]

        insert_text_mode_support: Optional[_InsertTextModeSupport]

    completion_item: Optional[_CompletionItem]

    class _CompletionItemKind(Model):
        value_set: Optional[List[CompletionItemKind]] = None

    completion_item_kind: Optional[_CompletionItemKind]
    context_support: Optional[bool] = None


class HoverClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None
    content_format: Optional[List[MarkupKind]] = None


class SignatureHelpClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None

    class _SignatureInformation(Model):
        documentation_format: Optional[List[MarkupKind]] = None

        class ParameterInformation(Model):
            label_offset_support: Optional[bool] = None

        parameter_information: Optional[ParameterInformation] = None
        active_parameter_support: Optional[bool] = None

    signature_information: Optional[_SignatureInformation] = None
    context_support: Optional[bool] = None


class DeclarationClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None
    link_support: Optional[bool] = None


class DefinitionClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None
    link_support: Optional[bool] = None


class TypeDefinitionClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None
    link_support: Optional[bool] = None


class ImplementationClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None
    link_support: Optional[bool] = None


class ReferenceClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None


class DocumentHighlightClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None


class DocumentSymbolClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None

    class _SymbolKind(Model):
        value_set: Optional[List[SymbolKind]] = None

    symbol_kind: Optional[_SymbolKind]
    hierarchical_document_symbol_support: Optional[bool] = None

    class _TagSupport(Model):
        value_set: List[SymbolTag]

    tag_support: Optional[_TagSupport] = None
    label_support: Optional[bool] = None


class CodeActionKind(str):
    EMPTY = ""
    QUICKFIX = "quickfix"
    REFACTOR = "refactor"
    REFACTOREXTRACT = "refactor.extract"
    REFACTORINLINE = "refactor.inline"
    REFACTORREWRITE = "refactor.rewrite"
    SOURCE = "source"
    SOURCEORGANIZEIMPORTS = "source.organizeImports"


class CodeActionClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None

    class _CodeActionLiteralSupport(Model):
        class _CodeActionKind(Model):
            value_set: Optional[List[CodeActionKind]] = None

        code_action_kind: _CodeActionKind

    code_action_literal_support: Optional[_CodeActionLiteralSupport] = None
    is_preferred_support: Optional[bool] = None
    disabled_support: Optional[bool] = None
    data_support: Optional[bool] = None

    class _ResolveSupport(Model):
        properties: List[str]

    resolve_support: Optional[_ResolveSupport] = None
    honors_change_annotations: Optional[bool] = None


class CodeLensClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None


class DocumentLinkClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None
    tooltip_support: Optional[bool] = None


class DocumentColorClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None


class DocumentFormattingClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None


class DocumentRangeFormattingClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None


class DocumentOnTypeFormattingClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None


class PrepareSupportDefaultBehavior(IntEnum):
    Identifier = 1


class RenameClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None
    prepare_support: Optional[bool] = None
    prepare_support_default_behavior: Optional[PrepareSupportDefaultBehavior] = None
    honors_change_annotations: Optional[bool] = None


class DiagnosticTag(IntEnum):
    Unnecessary = 1
    Deprecated = 2


class PublishDiagnosticsClientCapabilities(Model):
    related_information: Optional[bool] = None

    class _TagSupport(Model):
        value_set: List[DiagnosticTag]

    tag_support: Optional[_TagSupport] = None
    version_support: Optional[bool] = None
    code_description_support: Optional[bool] = None
    data_support: Optional[bool] = None


class FoldingRangeClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None
    range_limit: Optional[int] = None
    line_folding_only: Optional[bool] = None


class SelectionRangeClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None


class LinkedEditingRangeClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None


class CallHierarchyClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None


class TokenFormat(Enum):
    Relative = "relative"


class SemanticTokensClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None

    class _Requests(Model):
        range: Union[bool, Dict, None]

        class _Full(Model):
            delta: Optional[bool] = None

        full: Union[_Full, bool, None] = None

    requests: _Requests

    token_types: List[str]
    token_modifiers: List[str]
    formats: List[TokenFormat]
    overlapping_token_support: Optional[bool] = None
    multiline_token_support: Optional[bool] = None


class MonikerClientCapabilities(Model):
    dynamic_registration: Optional[bool] = None


class TextDocumentClientCapabilities(Model):
    synchronization: Optional[TextDocumentSyncClientCapabilities] = None
    completion: Optional[CompletionClientCapabilities] = None
    hover: Optional[HoverClientCapabilities] = None
    signature_help: Optional[SignatureHelpClientCapabilities] = None
    declaration: Optional[DeclarationClientCapabilities] = None
    definition: Optional[DefinitionClientCapabilities] = None
    type_definition: Optional[TypeDefinitionClientCapabilities] = None
    implementation: Optional[ImplementationClientCapabilities] = None
    references: Optional[ReferenceClientCapabilities] = None
    document_highlight: Optional[DocumentHighlightClientCapabilities] = None
    document_symbol: Optional[DocumentSymbolClientCapabilities] = None
    code_action: Optional[CodeActionClientCapabilities] = None
    code_lens: Optional[CodeLensClientCapabilities] = None
    document_link: Optional[DocumentLinkClientCapabilities] = None
    color_provider: Optional[DocumentColorClientCapabilities] = None
    formatting: Optional[DocumentFormattingClientCapabilities] = None
    range_formatting: Optional[DocumentRangeFormattingClientCapabilities] = None
    on_type_formatting: Optional[DocumentOnTypeFormattingClientCapabilities] = None
    rename: Optional[RenameClientCapabilities] = None
    publish_diagnostics: Optional[PublishDiagnosticsClientCapabilities] = None
    folding_range: Optional[FoldingRangeClientCapabilities] = None
    selection_range: Optional[SelectionRangeClientCapabilities] = None
    linked_editing_range: Optional[LinkedEditingRangeClientCapabilities] = None
    call_hierarchy: Optional[CallHierarchyClientCapabilities] = None
    semantic_tokens: Optional[SemanticTokensClientCapabilities] = None
    moniker: Optional[MonikerClientCapabilities] = None


class ShowMessageRequestClientCapabilities(Model):
    class _MessageActionItem(Model):
        additional_properties_support: Optional[bool] = None

    message_action_item: Optional[_MessageActionItem] = None


class ShowDocumentClientCapabilities(Model):
    support: bool


class RegularExpressionsClientCapabilities(Model):
    engine: str
    version: Optional[str] = None


class MarkdownClientCapabilities(Model):
    parser: str
    version: Optional[str] = None


class ClientCapabilities(Model):
    class _Workspace(Model):
        apply_edit: Optional[bool] = None
        workspace_edit: Optional[WorkspaceEditClientCapabilities] = None
        did_change_configuration: Optional[DidChangeConfigurationClientCapabilities] = None
        did_change_watched_files: Optional[DidChangeWatchedFilesClientCapabilities] = None
        symbol: Optional[WorkspaceSymbolClientCapabilities] = None
        execute_command: Optional[ExecuteCommandClientCapabilities] = None
        workspace_folders: Optional[bool] = None
        configuration: Optional[bool] = None
        semantic_tokens: Optional[SemanticTokensWorkspaceClientCapabilities] = None
        code_lens: Optional[CodeLensWorkspaceClientCapabilities] = None

        class _FileOperationsWorkspaceClientCapabilities(Model):
            dynamic_registration: Optional[bool] = None
            did_create: Optional[bool] = None
            will_create: Optional[bool] = None
            did_rename: Optional[bool] = None
            will_rename: Optional[bool] = None
            did_delete: Optional[bool] = None
            will_delete: Optional[bool] = None

        file_operations: Optional[_FileOperationsWorkspaceClientCapabilities]

    workspace: Optional[_Workspace] = None
    text_document: Optional[TextDocumentClientCapabilities] = None

    class _Window(Model):
        work_done_progress: Optional[bool] = None
        show_message: Optional[ShowMessageRequestClientCapabilities] = None
        show_document: Optional[ShowDocumentClientCapabilities] = None

    window: Optional[_Window] = None

    class _General(Model):
        regular_expressions: Optional[RegularExpressionsClientCapabilities] = None
        markdown: Optional[MarkdownClientCapabilities] = None

    general: Optional[_General] = None
    experimental: Optional[Any] = None


class InitializeParams(WorkDoneProgressParams):
    process_id: Optional[int] = None
    client_info: Optional[ClientInfo] = None
    locale: Optional[str] = None
    root_path: Optional[str] = None
    root_uri: Optional[DocumentUri] = None
    initialization_options: Optional[Any] = None
    capabilities: ClientCapabilities
    trace: Optional[TraceValue] = None
    workspace_folders: List[WorkspaceFolder] = []
