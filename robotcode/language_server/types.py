import re
from enum import Enum, IntEnum
from typing import Any, Dict, Iterator, List, Literal, Optional, Union

from pydantic import BaseModel, Field

ProgressToken = Union[str, int]
DocumentUri = str
URI = str


class Model(BaseModel):
    def __init__(self, **data: Any) -> None:
        super().__init__(**data)

    class Config:

        allow_population_by_field_name = True
        # use_enum_values = True

        @classmethod
        def alias_generator(cls, string: str) -> str:
            string = re.sub(r"^[\-_\.]", "", str(string))
            if not string:
                return string
            return str(string[0]).lower() + re.sub(
                r"[\-_\.\s]([a-z])",
                lambda matched: str(matched.group(1)).upper(),
                string[1:],
            )


class CancelParams(Model):
    id: Union[int, str] = Field(...)


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
        range: Union[bool, Dict[Any, Any], None]

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
    workspace_folders: Optional[List[WorkspaceFolder]] = None


class InitializeError(Model):
    retry: bool


class WorkspaceFoldersServerCapabilities(Model):
    supported: Optional[bool] = None
    change_notifications: Union[str, bool, None] = None


class FileOperationPatternKind(Enum):
    FILE = "file"
    FOLDER = "folder"


class FileOperationPatternOptions(Model):
    ignore_case: Optional[bool] = None


class FileOperationPattern(Model):
    glob: str
    matches: Optional[FileOperationPatternKind]
    options: Optional[FileOperationPatternOptions]


class FileOperationFilter(Model):
    scheme: Optional[str] = None
    pattern: FileOperationPattern


class FileOperationRegistrationOptions(Model):
    filters: List[FileOperationFilter]


class TextDocumentSyncKind(Enum):
    NONE = 0
    FULL = 1
    INCREMENTAL = 2


class SaveOptions(Model):
    include_text: Optional[bool]


class TextDocumentSyncOptions(Model):
    def __init__(
        self,
        open_close: Optional[bool] = None,
        change: Optional[TextDocumentSyncKind] = None,
        will_save: Optional[bool] = None,
        will_save_wait_until: Optional[bool] = None,
        save: Union[bool, SaveOptions, None] = None,
    ) -> None:
        super().__init__(  # type: ignore
            open_close=open_close,
            change=change,
            will_save=will_save,
            will_save_wait_until=will_save_wait_until,
            save=save,
        )

    open_close: Optional[bool] = None
    change: Optional[TextDocumentSyncKind] = None
    will_save: Optional[bool] = None
    will_save_wait_until: Optional[bool] = None
    save: Union[bool, SaveOptions, None] = None


class WorkDoneProgressOptions(Model):
    work_done_progress: Optional[bool] = None


class DocumentFilter(Model):
    language: Optional[str] = None
    scheme: Optional[str] = None
    pattern: Optional[str] = None


DocumentSelector = List[DocumentFilter]


class TextDocumentRegistrationOptions(Model):
    document_selector: Optional[DocumentSelector] = None


class StaticRegistrationOptions(Model):
    id: Optional[str] = None


class FoldingRangeOptions(WorkDoneProgressOptions):
    pass


class FoldingRangeRegistrationOptions(
    TextDocumentRegistrationOptions, FoldingRangeOptions, StaticRegistrationOptions, Model
):
    pass


class DefinitionOptions(WorkDoneProgressOptions):
    pass


class ServerCapabilities(Model):
    text_document_sync: Union[TextDocumentSyncOptions, TextDocumentSyncKind, None]
    # completion_provider: Optional[CompletionOptions] = None
    # hover_provider: Optional[boolean, HoverOptions] = None
    # signature_help_provider: Optional[SignatureHelpOptions] = None
    # declaration_provider: Union[bool, DeclarationOptions, DeclarationRegistrationOptions, None] = None
    definition_provider: Union[bool, DefinitionOptions, None] = None
    # implementation_provider: Union[bool, ImplementationOptions, ImplementationRegistrationOptions, None] = None
    # references_provider: Union[bool, ReferenceOptions, None] = None
    # document_highlight_provider: Union[bool, DocumentHighlightOptions, None] = None
    # document_symbol_provider: Union[bool, DocumentSymbolOptions] = None
    # code_action_provider: Union[bool, CodeActionOptions] = None
    # code_lens_provider: Optional[CodeLensOptions] = None
    # document_link_provider: Optional[DocumentLinkOptions] = None
    # color_provider: Union[bool, DocumentColorOptions, DocumentColorRegistrationOptions, None] = None
    # document_formatting_provider: Union[bool, DocumentFormattingOptions, None] = None
    # document_range_formatting_provider: Union[bool, DocumentRangeFormattingOptions, None] = None
    # document_on_type_formatting_provider: Optional[DocumentOnTypeFormattingOptions] = None
    # rename_provider: Union[bool, RenameOptions, None] = None
    folding_range_provider: Union[bool, FoldingRangeOptions, FoldingRangeRegistrationOptions, None] = None
    # selection_range_provider: Union[bool, SelectionRangeOptions, SelectionRangeRegistrationOptions, None] = None
    # linked_editing_range_provider: Union[
    #     boolean, LinkedEditingRangeOptions, LinkedEditingRangeRegistrationOptions, None
    # ] = None
    # call_hierarchy_provider: Union[boolean, CallHierarchyOptions, CallHierarchyRegistrationOptions, None] = None
    # semantic_tokens_provider: Union[SemanticTokensOptions, SemanticTokensRegistrationOptions, None] = None
    # moniker_provider: Union[bool, MonikerOptions, MonikerRegistrationOptions, None] = None
    # workspace_symbol_provider: Union[boolean, WorkspaceSymbolOptions, None] = None

    class Workspace(Model):
        workspace_folders: Optional[WorkspaceFoldersServerCapabilities] = None

        class FileOperations(Model):
            did_create: Optional[FileOperationRegistrationOptions] = None
            will_create: Optional[FileOperationRegistrationOptions] = None
            did_rename: Optional[FileOperationRegistrationOptions] = None
            will_rename: Optional[FileOperationRegistrationOptions] = None
            did_delete: Optional[FileOperationRegistrationOptions] = None
            will_delete: Optional[FileOperationRegistrationOptions] = None

        file_operations: Optional[FileOperations] = None

    workspace: Optional[Workspace] = None
    experimental: Optional[Any] = None


class InitializeResult(Model):
    capabilities: ServerCapabilities

    class ServerInfo(Model):
        name: str
        version: Optional[str] = None

    server_info: Optional[ServerInfo] = None


class InitializedParams(Model):
    pass


class DidChangeConfigurationParams(Model):
    settings: Any


class Position(Model):
    line: int
    character: int

    def __ge__(self, other: "Position") -> bool:
        line_gt = self.line > other.line

        if line_gt:
            return line_gt

        if self.line == other.line:
            return self.character >= other.character

        return False

    def __gt__(self, other: "Position") -> bool:
        line_gt = self.line > other.line

        if line_gt:
            return line_gt

        if self.line == other.line:
            return self.character > other.character

        return False

    def __le__(self, other: "Position") -> bool:
        line_lt = self.line < other.line

        if line_lt:
            return line_lt

        if self.line == other.line:
            return self.character <= other.character

        return False

    def __lt__(self, other: "Position") -> bool:
        line_lt = self.line < other.line

        if line_lt:
            return line_lt

        if self.line == other.line:
            return self.character < other.character

        return False

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __iter__(self) -> Iterator[int]:  # type: ignore
        return iter((self.line, self.character))

    def is_in_range(self, range: "Range") -> bool:
        return self >= range.start and self <= range.end


class Range(Model):
    start: Position
    end: Position

    def __iter__(self) -> Iterator[Position]:  # type: ignore
        return iter((self.start, self.end))


class TextDocumentItem(Model):
    uri: DocumentUri
    language_id: str
    version: int
    text: str


class DidOpenTextDocumentParams(Model):
    text_document: TextDocumentItem


class TextDocumentIdentifier(Model):
    uri: DocumentUri


class OptionalVersionedTextDocumentIdentifier(TextDocumentIdentifier):
    version: Optional[int] = None


class VersionedTextDocumentIdentifier(TextDocumentIdentifier):
    version: int


class DidCloseTextDocumentParams(Model):
    text_document: TextDocumentIdentifier


class TextDocumentContentRangeChangeEvent(Model):
    range: Range
    range_length: Optional[int] = None

    text: str


class TextDocumentContentTextChangeEvent(Model):
    text: str


TextDocumentContentChangeEvent = Union[TextDocumentContentRangeChangeEvent, TextDocumentContentTextChangeEvent]


class DidChangeTextDocumentParams(Model):
    text_document: VersionedTextDocumentIdentifier
    content_changes: List[TextDocumentContentChangeEvent]


class ConfigurationItem(Model):
    scope_uri: Optional[DocumentUri]
    section: Optional[str]


class ConfigurationParams(Model):
    items: List[ConfigurationItem]


class MessageType(IntEnum):
    Error = 1
    Warning = 2
    Info = 3
    Log = 4


class ShowMessageParams(Model):
    type: MessageType
    message: str


class LogMessageParams(Model):
    type: MessageType
    message: str


class MessageActionItem(Model):
    title: str


class ShowMessageRequestParams(ShowMessageParams):
    actions: Optional[List[MessageActionItem]] = None


class ShowDocumentParams(Model):
    uri: URI
    external: Optional[bool] = None
    take_focus: Optional[bool] = None
    selection: Optional[Range] = None


class ShowDocumentResult(Model):
    success: bool


class TextDocumentSaveReason(IntEnum):
    Manual = 1
    AfterDelay = 2
    FocusOut = 3


class WillSaveTextDocumentParams(Model):
    text_document: TextDocumentIdentifier
    reason: TextDocumentSaveReason


class TextEdit(Model):
    range: Range
    new_text: str


class DidSaveTextDocumentParams(Model):
    text_document: TextDocumentIdentifier
    text: Optional[str] = None


class DiagnosticSeverity(Enum):
    ERROR = 1
    WARNING = 2
    INFORMATION = 3
    HINT = 4


class CodeDescription(Model):
    href: URI


class Location(Model):
    uri: DocumentUri
    range: Range


class LocationLink(Model):
    origin_selection_range: Optional[Range]
    target_uri: DocumentUri
    target_range: Range
    target_selection_range: Range


class DiagnosticRelatedInformation(Model):
    location: Location
    message: str


class Diagnostic(Model):
    range: Range
    message: str
    severity: Optional[DiagnosticSeverity] = None
    code: Union[int, str, None] = None
    code_description: Optional[CodeDescription] = None
    source: Optional[str] = None
    tags: Optional[List[DiagnosticTag]] = None
    related_information: Optional[List[DiagnosticRelatedInformation]] = None
    data: Optional[Any] = None


class PublishDiagnosticsParams(Model):
    uri: DocumentUri
    version: Optional[int] = None
    diagnostics: List[Diagnostic]


class SetTraceParams(Model):
    value: TraceValue


class FoldingRangeParams(WorkDoneProgressParams):
    text_document: TextDocumentIdentifier


class FoldingRangeKind(Enum):
    Comment = "comment"
    Imports = "imports"
    Region = "region"


class FoldingRange(Model):
    start_line: int
    start_character: Optional[int] = None
    end_line: int
    end_character: Optional[int] = None
    kind: Union[FoldingRangeKind, str, None] = None


class FileCreate(Model):
    uri: str


class CreateFilesParams(Model):
    files: List[FileCreate]


class FileRename(Model):
    old_uri: str
    new_uri: str


class RenameFilesParams(Model):
    files: List[FileRename]


class FileDelete(Model):
    uri: str


class DeleteFilesParams(Model):
    files: List[FileDelete]


ChangeAnnotationIdentifier = str


class CreateFileOptions(Model):
    overwrite: Optional[bool] = None
    ignore_if_exists: Optional[bool] = None


class CreateFile(Model):
    kind: Literal["create"]
    uri: DocumentUri
    options: Optional[CreateFileOptions]
    annotation_id: ChangeAnnotationIdentifier


class RenameFileOptions(Model):
    overwrite: Optional[bool] = None
    ignore_if_exists: Optional[bool] = None


class RenameFile(Model):
    kind: Literal["rename"]
    old_uri: DocumentUri
    new_uri: DocumentUri
    options: Optional[RenameFileOptions]
    annotation_id: ChangeAnnotationIdentifier


class DeleteFileOptions(Model):
    recursive: Optional[bool] = None
    ignore_if_exists: Optional[bool] = None


class DeleteFile(Model):
    kind: Literal["delete"]
    uri: DocumentUri
    options: Optional[DeleteFileOptions]
    annotation_id: ChangeAnnotationIdentifier


class AnnotatedTextEdit(TextEdit):
    annotation_id: ChangeAnnotationIdentifier


class TextDocumentEdit(Model):
    text_document: OptionalVersionedTextDocumentIdentifier
    edits: Union[TextEdit, AnnotatedTextEdit]


class ChangeAnnotation(Model):
    label: str
    needs_confirmation: Optional[bool] = None
    description: Optional[str] = None


class WorkspaceEdit(Model):
    changes: Optional[Dict[DocumentUri, List[TextEdit]]] = None
    document_changes: Union[List[TextDocumentEdit], TextDocumentEdit, CreateFile, RenameFile, DeleteFile, None] = None
    change_annotations: Optional[Dict[ChangeAnnotationIdentifier, ChangeAnnotation]] = None


class PartialResultParams(Model):
    partial_result_token: Optional[ProgressToken]


class TextDocumentPositionParams(Model):
    text_document: TextDocumentIdentifier
    position: Position


class DefinitionParams(TextDocumentPositionParams, WorkDoneProgressParams, PartialResultParams):
    pass
