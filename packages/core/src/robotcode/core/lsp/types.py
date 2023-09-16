# ****** THIS IS A GENERATED FILE, DO NOT EDIT. ******
# Steps to generate:
# 1. Checkout https://github.com/microsoft/lsprotocol
# 2. Install nox: `python -m pip install nox`
# 3. Run command: `python -m nox --session build_lsp`

# ruff: noqa: E501

from __future__ import annotations

import enum
import functools
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Literal, Optional, Tuple, Union

from robotcode.core.dataclasses import CamelSnakeMixin

__lsp_version__ = "3.17.0"

DocumentUri = str
URI = str


@enum.unique
class SemanticTokenTypes(str, enum.Enum):
    """A set of predefined token types. This set is not fixed
    an clients can specify additional token types via the
    corresponding client capabilities.

    @since 3.16.0"""

    # Since: 3.16.0
    NAMESPACE = "namespace"
    TYPE = "type"
    """Represents a generic type. Acts as a fallback for types which can't be mapped to
    a specific type like class or enum."""
    CLASS_ = "class"
    ENUM = "enum"
    INTERFACE = "interface"
    STRUCT = "struct"
    TYPE_PARAMETER = "typeParameter"
    PARAMETER = "parameter"
    VARIABLE = "variable"
    PROPERTY = "property"
    ENUM_MEMBER = "enumMember"
    EVENT = "event"
    FUNCTION = "function"
    METHOD = "method"
    MACRO = "macro"
    KEYWORD = "keyword"
    MODIFIER = "modifier"
    COMMENT = "comment"
    STRING = "string"
    NUMBER = "number"
    REGEXP = "regexp"
    OPERATOR = "operator"
    DECORATOR = "decorator"
    """@since 3.17.0"""
    # Since: 3.17.0


@enum.unique
class SemanticTokenModifiers(str, enum.Enum):
    """A set of predefined token modifiers. This set is not fixed
    an clients can specify additional token types via the
    corresponding client capabilities.

    @since 3.16.0"""

    # Since: 3.16.0
    DECLARATION = "declaration"
    DEFINITION = "definition"
    READONLY = "readonly"
    STATIC = "static"
    DEPRECATED = "deprecated"
    ABSTRACT = "abstract"
    ASYNC_ = "async"
    MODIFICATION = "modification"
    DOCUMENTATION = "documentation"
    DEFAULT_LIBRARY = "defaultLibrary"


@enum.unique
class DocumentDiagnosticReportKind(str, enum.Enum):
    """The document diagnostic report kinds.

    @since 3.17.0"""

    # Since: 3.17.0
    FULL = "full"
    """A diagnostic report with a full
    set of problems."""
    UNCHANGED = "unchanged"
    """A report indicating that the last
    returned report is still accurate."""


class ErrorCodes(enum.IntEnum):
    """Predefined error codes."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    SERVER_NOT_INITIALIZED = -32002
    """Error code indicating that a server received a notification or
    request before the server has received the `initialize` request."""
    UNKNOWN_ERROR_CODE = -32001


class LSPErrorCodes(enum.IntEnum):
    REQUEST_FAILED = -32803
    """A request failed but it was syntactically correct, e.g the
    method name was known and the parameters were valid. The error
    message should contain human readable information about why
    the request failed.

    @since 3.17.0"""
    # Since: 3.17.0
    SERVER_CANCELLED = -32802
    """The server cancelled the request. This error code should
    only be used for requests that explicitly support being
    server cancellable.

    @since 3.17.0"""
    # Since: 3.17.0
    CONTENT_MODIFIED = -32801
    """The server detected that the content of a document got
    modified outside normal conditions. A server should
    NOT send this error code if it detects a content change
    in it unprocessed messages. The result even computed
    on an older state might still be useful for the client.

    If a client decides that a result is not of any use anymore
    the client should cancel the request."""
    REQUEST_CANCELLED = -32800
    """The client has canceled a request and a server as detected
    the cancel."""


@enum.unique
class FoldingRangeKind(str, enum.Enum):
    """A set of predefined range kinds."""

    COMMENT = "comment"
    """Folding range for a comment"""
    IMPORTS = "imports"
    """Folding range for an import or include"""
    REGION = "region"
    """Folding range for a region (e.g. `#region`)"""


@enum.unique
class SymbolKind(enum.IntEnum):
    """A symbol kind."""

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
    ENUM_MEMBER = 22
    STRUCT = 23
    EVENT = 24
    OPERATOR = 25
    TYPE_PARAMETER = 26


@enum.unique
class SymbolTag(enum.IntEnum):
    """Symbol tags are extra annotations that tweak the rendering of a symbol.

    @since 3.16"""

    # Since: 3.16
    DEPRECATED = 1
    """Render a symbol as obsolete, usually using a strike-out."""


@enum.unique
class UniquenessLevel(str, enum.Enum):
    """Moniker uniqueness level to define scope of the moniker.

    @since 3.16.0"""

    # Since: 3.16.0
    DOCUMENT = "document"
    """The moniker is only unique inside a document"""
    PROJECT = "project"
    """The moniker is unique inside a project for which a dump got created"""
    GROUP = "group"
    """The moniker is unique inside the group to which a project belongs"""
    SCHEME = "scheme"
    """The moniker is unique inside the moniker scheme."""
    GLOBAL_ = "global"
    """The moniker is globally unique"""


@enum.unique
class MonikerKind(str, enum.Enum):
    """The moniker kind.

    @since 3.16.0"""

    # Since: 3.16.0
    IMPORT_ = "import"
    """The moniker represent a symbol that is imported into a project"""
    EXPORT = "export"
    """The moniker represents a symbol that is exported from a project"""
    LOCAL = "local"
    """The moniker represents a symbol that is local to a project (e.g. a local
    variable of a function, a class not visible outside the project, ...)"""


@enum.unique
class InlayHintKind(enum.IntEnum):
    """Inlay hint kinds.

    @since 3.17.0"""

    # Since: 3.17.0
    TYPE = 1
    """An inlay hint that for a type annotation."""
    PARAMETER = 2
    """An inlay hint that is for a parameter."""


@enum.unique
class MessageType(enum.IntEnum):
    """The message type"""

    ERROR = 1
    """An error message."""
    WARNING = 2
    """A warning message."""
    INFO = 3
    """An information message."""
    LOG = 4
    """A log message."""


@enum.unique
class TextDocumentSyncKind(enum.IntEnum):
    """Defines how the host (editor) should sync
    document changes to the language server."""

    NONE_ = 0
    """Documents should not be synced at all."""
    FULL = 1
    """Documents are synced by always sending the full content
    of the document."""
    INCREMENTAL = 2
    """Documents are synced by sending the full content on open.
    After that only incremental updates to the document are
    send."""


@enum.unique
class TextDocumentSaveReason(enum.IntEnum):
    """Represents reasons why a text document is saved."""

    MANUAL = 1
    """Manually triggered, e.g. by the user pressing save, by starting debugging,
    or by an API call."""
    AFTER_DELAY = 2
    """Automatic after a delay."""
    FOCUS_OUT = 3
    """When the editor lost focus."""


@enum.unique
class CompletionItemKind(enum.IntEnum):
    """The kind of a completion entry."""

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
    ENUM_MEMBER = 20
    CONSTANT = 21
    STRUCT = 22
    EVENT = 23
    OPERATOR = 24
    TYPE_PARAMETER = 25


@enum.unique
class CompletionItemTag(enum.IntEnum):
    """Completion item tags are extra annotations that tweak the rendering of a completion
    item.

    @since 3.15.0"""

    # Since: 3.15.0
    DEPRECATED = 1
    """Render a completion as obsolete, usually using a strike-out."""


@enum.unique
class InsertTextFormat(enum.IntEnum):
    """Defines whether the insert text in a completion item should be interpreted as
    plain text or a snippet."""

    PLAIN_TEXT = 1
    """The primary text to be inserted is treated as a plain string."""
    SNIPPET = 2
    """The primary text to be inserted is treated as a snippet.

    A snippet can define tab stops and placeholders with `$1`, `$2`
    and `${3:foo}`. `$0` defines the final tab stop, it defaults to
    the end of the snippet. Placeholders with equal identifiers are linked,
    that is typing in one will update others too.

    See also: https://microsoft.github.io/language-server-protocol/specifications/specification-current/#snippet_syntax"""


@enum.unique
class InsertTextMode(enum.IntEnum):
    """How whitespace and indentation is handled during completion
    item insertion.

    @since 3.16.0"""

    # Since: 3.16.0
    AS_IS = 1
    """The insertion or replace strings is taken as it is. If the
    value is multi line the lines below the cursor will be
    inserted using the indentation defined in the string value.
    The client will not apply any kind of adjustments to the
    string."""
    ADJUST_INDENTATION = 2
    """The editor adjusts leading whitespace of new lines so that
    they match the indentation up to the cursor of the line for
    which the item is accepted.

    Consider a line like this: <2tabs><cursor><3tabs>foo. Accepting a
    multi line completion item is indented using 2 tabs and all
    following lines inserted will be indented using 2 tabs as well."""


@enum.unique
class DocumentHighlightKind(enum.IntEnum):
    """A document highlight kind."""

    TEXT = 1
    """A textual occurrence."""
    READ = 2
    """Read-access of a symbol, like reading a variable."""
    WRITE = 3
    """Write-access of a symbol, like writing to a variable."""


@enum.unique
class CodeActionKind(str, enum.Enum):
    """A set of predefined code action kinds"""

    EMPTY = ""
    """Empty kind."""
    QUICK_FIX = "quickfix"
    """Base kind for quickfix actions: 'quickfix'"""
    REFACTOR = "refactor"
    """Base kind for refactoring actions: 'refactor'"""
    REFACTOR_EXTRACT = "refactor.extract"
    """Base kind for refactoring extraction actions: 'refactor.extract'

    Example extract actions:

    - Extract method
    - Extract function
    - Extract variable
    - Extract interface from class
    - ..."""
    REFACTOR_INLINE = "refactor.inline"
    """Base kind for refactoring inline actions: 'refactor.inline'

    Example inline actions:

    - Inline function
    - Inline variable
    - Inline constant
    - ..."""
    REFACTOR_REWRITE = "refactor.rewrite"
    """Base kind for refactoring rewrite actions: 'refactor.rewrite'

    Example rewrite actions:

    - Convert JavaScript function to class
    - Add or remove parameter
    - Encapsulate field
    - Make method static
    - Move method to base class
    - ..."""
    SOURCE = "source"
    """Base kind for source actions: `source`

    Source code actions apply to the entire file."""
    SOURCE_ORGANIZE_IMPORTS = "source.organizeImports"
    """Base kind for an organize imports source action: `source.organizeImports`"""
    SOURCE_FIX_ALL = "source.fixAll"
    """Base kind for auto-fix source actions: `source.fixAll`.

    Fix all actions automatically fix errors that have a clear fix that do not require user input.
    They should not suppress errors or perform unsafe fixes such as generating new types or classes.

    @since 3.15.0"""
    # Since: 3.15.0


@enum.unique
class TraceValues(str, enum.Enum):
    OFF = "off"
    """Turn tracing off."""
    MESSAGES = "messages"
    """Trace messages only."""
    VERBOSE = "verbose"
    """Verbose message tracing."""


@enum.unique
class MarkupKind(str, enum.Enum):
    """Describes the content type that a client supports in various
    result literals like `Hover`, `ParameterInfo` or `CompletionItem`.

    Please note that `MarkupKinds` must not start with a `$`. This kinds
    are reserved for internal usage."""

    PLAIN_TEXT = "plaintext"
    """Plain text is supported as a content format"""
    MARKDOWN = "markdown"
    """Markdown is supported as a content format"""


@enum.unique
class PositionEncodingKind(str, enum.Enum):
    """A set of predefined position encoding kinds.

    @since 3.17.0"""

    # Since: 3.17.0
    UTF8 = "utf-8"
    """Character offsets count UTF-8 code units."""
    UTF16 = "utf-16"
    """Character offsets count UTF-16 code units.

    This is the default and must always be supported
    by servers"""
    UTF32 = "utf-32"
    """Character offsets count UTF-32 code units.

    Implementation note: these are the same as Unicode code points,
    so this `PositionEncodingKind` may also be used for an
    encoding-agnostic representation of character offsets."""


@enum.unique
class FileChangeType(enum.IntEnum):
    """The file event type"""

    CREATED = 1
    """The file got created."""
    CHANGED = 2
    """The file got changed."""
    DELETED = 3
    """The file got deleted."""


@enum.unique
class WatchKind(enum.IntFlag):
    CREATE = 1
    """Interested in create events."""
    CHANGE = 2
    """Interested in change events"""
    DELETE = 4
    """Interested in delete events"""


@enum.unique
class DiagnosticSeverity(enum.IntEnum):
    """The diagnostic's severity."""

    ERROR = 1
    """Reports an error."""
    WARNING = 2
    """Reports a warning."""
    INFORMATION = 3
    """Reports an information."""
    HINT = 4
    """Reports a hint."""


@enum.unique
class DiagnosticTag(enum.IntEnum):
    """The diagnostic tags.

    @since 3.15.0"""

    # Since: 3.15.0
    UNNECESSARY = 1
    """Unused or unnecessary code.

    Clients are allowed to render diagnostics with this tag faded out instead of having
    an error squiggle."""
    DEPRECATED = 2
    """Deprecated or obsolete code.

    Clients are allowed to rendered diagnostics with this tag strike through."""


@enum.unique
class CompletionTriggerKind(enum.IntEnum):
    """How a completion was triggered"""

    INVOKED = 1
    """Completion was triggered by typing an identifier (24x7 code
    complete), manual invocation (e.g Ctrl+Space) or via API."""
    TRIGGER_CHARACTER = 2
    """Completion was triggered by a trigger character specified by
    the `triggerCharacters` properties of the `CompletionRegistrationOptions`."""
    TRIGGER_FOR_INCOMPLETE_COMPLETIONS = 3
    """Completion was re-triggered as current completion list is incomplete"""


@enum.unique
class SignatureHelpTriggerKind(enum.IntEnum):
    """How a signature help was triggered.

    @since 3.15.0"""

    # Since: 3.15.0
    INVOKED = 1
    """Signature help was invoked manually by the user or by a command."""
    TRIGGER_CHARACTER = 2
    """Signature help was triggered by a trigger character."""
    CONTENT_CHANGE = 3
    """Signature help was triggered by the cursor moving or by the document content changing."""


@enum.unique
class CodeActionTriggerKind(enum.IntEnum):
    """The reason why code actions were requested.

    @since 3.17.0"""

    # Since: 3.17.0
    INVOKED = 1
    """Code actions were explicitly requested by the user or by an extension."""
    AUTOMATIC = 2
    """Code actions were requested automatically.

    This typically happens when current selection in a file changes, but can
    also be triggered when file content changes."""


@enum.unique
class FileOperationPatternKind(str, enum.Enum):
    """A pattern kind describing if a glob pattern matches a file a folder or
    both.

    @since 3.16.0"""

    # Since: 3.16.0
    FILE = "file"
    """The pattern matches a file only."""
    FOLDER = "folder"
    """The pattern matches a folder only."""


@enum.unique
class NotebookCellKind(enum.IntEnum):
    """A notebook cell kind.

    @since 3.17.0"""

    # Since: 3.17.0
    MARKUP = 1
    """A markup-cell is formatted source that is used for display."""
    CODE = 2
    """A code-cell is source code."""


@enum.unique
class ResourceOperationKind(str, enum.Enum):
    CREATE = "create"
    """Supports creating new files and folders."""
    RENAME = "rename"
    """Supports renaming existing files and folders."""
    DELETE = "delete"
    """Supports deleting existing files and folders."""


@enum.unique
class FailureHandlingKind(str, enum.Enum):
    ABORT = "abort"
    """Applying the workspace change is simply aborted if one of the changes provided
    fails. All operations executed before the failing operation stay executed."""
    TRANSACTIONAL = "transactional"
    """All operations are executed transactional. That means they either all
    succeed or no changes at all are applied to the workspace."""
    TEXT_ONLY_TRANSACTIONAL = "textOnlyTransactional"
    """If the workspace edit contains only textual file changes they are executed transactional.
    If resource changes (create, rename or delete file) are part of the change the failure
    handling strategy is abort."""
    UNDO = "undo"
    """The client tries to undo the operations already executed. But there is no
    guarantee that this is succeeding."""


@enum.unique
class PrepareSupportDefaultBehavior(enum.IntEnum):
    IDENTIFIER = 1
    """The client's default behavior is to select the identifier
    according the to language's syntax rule."""


@enum.unique
class TokenFormat(str, enum.Enum):
    RELATIVE = "relative"


LSPObject = object
"""LSP object definition.
@since 3.17.0"""
# Since: 3.17.0


@dataclass
class TextDocumentPositionParams(CamelSnakeMixin):
    """A parameter literal used in requests to pass a text document and a position inside that
    document."""

    text_document: TextDocumentIdentifier
    """The text document."""

    position: Position
    """The position inside the text document."""


@dataclass
class WorkDoneProgressParams(CamelSnakeMixin):
    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""


@dataclass
class PartialResultParams(CamelSnakeMixin):
    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class ImplementationParams(CamelSnakeMixin):
    text_document: TextDocumentIdentifier
    """The text document."""

    position: Position
    """The position inside the text document."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class Location(CamelSnakeMixin):
    """Represents a location inside a resource, such as a line
    inside a text file."""

    uri: DocumentUri

    range: Range

    def __hash__(self) -> int:
        return hash((self.uri, self.range))


@dataclass
class TextDocumentRegistrationOptions(CamelSnakeMixin):
    """General text document registration options."""

    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""


@dataclass
class WorkDoneProgressOptions(CamelSnakeMixin):
    work_done_progress: Optional[bool] = None


@dataclass
class ImplementationOptions(CamelSnakeMixin):
    work_done_progress: Optional[bool] = None


@dataclass
class StaticRegistrationOptions(CamelSnakeMixin):
    """Static registration options to be returned in the initialize
    request."""

    id: Optional[str] = None
    """The id used to register the request. The id can be used to deregister
    the request again. See also Registration#id."""


@dataclass
class ImplementationRegistrationOptions(CamelSnakeMixin):
    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    work_done_progress: Optional[bool] = None

    id: Optional[str] = None
    """The id used to register the request. The id can be used to deregister
    the request again. See also Registration#id."""


@dataclass
class TypeDefinitionParams(CamelSnakeMixin):
    text_document: TextDocumentIdentifier
    """The text document."""

    position: Position
    """The position inside the text document."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class TypeDefinitionOptions(CamelSnakeMixin):
    work_done_progress: Optional[bool] = None


@dataclass
class TypeDefinitionRegistrationOptions(CamelSnakeMixin):
    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    work_done_progress: Optional[bool] = None

    id: Optional[str] = None
    """The id used to register the request. The id can be used to deregister
    the request again. See also Registration#id."""


@dataclass
class WorkspaceFolder(CamelSnakeMixin):
    """A workspace folder inside a client."""

    uri: URI
    """The associated URI for this workspace folder."""

    name: str
    """The name of the workspace folder. Used to refer to this
    workspace folder in the user interface."""


@dataclass
class DidChangeWorkspaceFoldersParams(CamelSnakeMixin):
    """The parameters of a `workspace/didChangeWorkspaceFolders` notification."""

    event: WorkspaceFoldersChangeEvent
    """The actual workspace folder change event."""


@dataclass
class ConfigurationParams(CamelSnakeMixin):
    """The parameters of a configuration request."""

    items: List[ConfigurationItem]


@dataclass
class DocumentColorParams(CamelSnakeMixin):
    """Parameters for a {@link DocumentColorRequest}."""

    text_document: TextDocumentIdentifier
    """The text document."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class ColorInformation(CamelSnakeMixin):
    """Represents a color range from a document."""

    range: Range
    """The range in the document where this color appears."""

    color: Color
    """The actual color value for this color range."""


@dataclass
class DocumentColorOptions(CamelSnakeMixin):
    work_done_progress: Optional[bool] = None


@dataclass
class DocumentColorRegistrationOptions(CamelSnakeMixin):
    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    work_done_progress: Optional[bool] = None

    id: Optional[str] = None
    """The id used to register the request. The id can be used to deregister
    the request again. See also Registration#id."""


@dataclass
class ColorPresentationParams(CamelSnakeMixin):
    """Parameters for a {@link ColorPresentationRequest}."""

    text_document: TextDocumentIdentifier
    """The text document."""

    color: Color
    """The color to request presentations for."""

    range: Range
    """The range where the color would be inserted. Serves as a context."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class ColorPresentation(CamelSnakeMixin):
    label: str
    """The label of this color presentation. It will be shown on the color
    picker header. By default this is also the text that is inserted when selecting
    this color presentation."""

    text_edit: Optional[TextEdit] = None
    """An {@link TextEdit edit} which is applied to a document when selecting
    this presentation for the color.  When `falsy` the {@link ColorPresentation.label label}
    is used."""

    additional_text_edits: Optional[List[TextEdit]] = None
    """An optional array of additional {@link TextEdit text edits} that are applied when
    selecting this color presentation. Edits must not overlap with the main {@link ColorPresentation.textEdit edit} nor with themselves."""


@dataclass
class FoldingRangeParams(CamelSnakeMixin):
    """Parameters for a {@link FoldingRangeRequest}."""

    text_document: TextDocumentIdentifier
    """The text document."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class FoldingRange(CamelSnakeMixin):
    """Represents a folding range. To be valid, start and end line must be bigger than zero and smaller
    than the number of lines in the document. Clients are free to ignore invalid ranges.
    """

    start_line: int
    """The zero-based start line of the range to fold. The folded area starts after the line's last character.
    To be valid, the end must be zero or larger and smaller than the number of lines in the document."""

    end_line: int
    """The zero-based end line of the range to fold. The folded area ends with the line's last character.
    To be valid, the end must be zero or larger and smaller than the number of lines in the document."""

    start_character: Optional[int] = None
    """The zero-based character offset from where the folded range starts. If not defined, defaults to the length of the start line."""

    end_character: Optional[int] = None
    """The zero-based character offset before the folded range ends. If not defined, defaults to the length of the end line."""

    kind: Optional[Union[FoldingRangeKind, str]] = None
    """Describes the kind of the folding range such as `comment' or 'region'. The kind
    is used to categorize folding ranges and used by commands like 'Fold all comments'.
    See {@link FoldingRangeKind} for an enumeration of standardized kinds."""

    collapsed_text: Optional[str] = None
    """The text that the client should show when the specified range is
    collapsed. If not defined or not supported by the client, a default
    will be chosen by the client.

    @since 3.17.0"""
    # Since: 3.17.0


@dataclass
class FoldingRangeOptions(CamelSnakeMixin):
    work_done_progress: Optional[bool] = None


@dataclass
class FoldingRangeRegistrationOptions(CamelSnakeMixin):
    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    work_done_progress: Optional[bool] = None

    id: Optional[str] = None
    """The id used to register the request. The id can be used to deregister
    the request again. See also Registration#id."""


@dataclass
class DeclarationParams(CamelSnakeMixin):
    text_document: TextDocumentIdentifier
    """The text document."""

    position: Position
    """The position inside the text document."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class DeclarationOptions(CamelSnakeMixin):
    work_done_progress: Optional[bool] = None


@dataclass
class DeclarationRegistrationOptions(CamelSnakeMixin):
    work_done_progress: Optional[bool] = None

    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    id: Optional[str] = None
    """The id used to register the request. The id can be used to deregister
    the request again. See also Registration#id."""


@dataclass
class SelectionRangeParams(CamelSnakeMixin):
    """A parameter literal used in selection range requests."""

    text_document: TextDocumentIdentifier
    """The text document."""

    positions: List[Position]
    """The positions inside the text document."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class SelectionRange(CamelSnakeMixin):
    """A selection range represents a part of a selection hierarchy. A selection range
    may have a parent selection range that contains it."""

    range: Range
    """The {@link Range range} of this selection range."""

    parent: Optional[SelectionRange] = None
    """The parent selection range containing this range. Therefore `parent.range` must contain `this.range`."""


@dataclass
class SelectionRangeOptions(CamelSnakeMixin):
    work_done_progress: Optional[bool] = None


@dataclass
class SelectionRangeRegistrationOptions(CamelSnakeMixin):
    work_done_progress: Optional[bool] = None

    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    id: Optional[str] = None
    """The id used to register the request. The id can be used to deregister
    the request again. See also Registration#id."""


@dataclass
class WorkDoneProgressCreateParams(CamelSnakeMixin):
    token: ProgressToken
    """The token to be used to report progress."""


@dataclass
class WorkDoneProgressCancelParams(CamelSnakeMixin):
    token: ProgressToken
    """The token to be used to report progress."""


@dataclass
class CallHierarchyPrepareParams(CamelSnakeMixin):
    """The parameter of a `textDocument/prepareCallHierarchy` request.

    @since 3.16.0"""

    # Since: 3.16.0

    text_document: TextDocumentIdentifier
    """The text document."""

    position: Position
    """The position inside the text document."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""


@dataclass
class CallHierarchyItem(CamelSnakeMixin):
    """Represents programming constructs like functions or constructors in the context
    of call hierarchy.

    @since 3.16.0"""

    # Since: 3.16.0

    name: str
    """The name of this item."""

    kind: SymbolKind
    """The kind of this item."""

    uri: DocumentUri
    """The resource identifier of this item."""

    range: Range
    """The range enclosing this symbol not including leading/trailing whitespace but everything else, e.g. comments and code."""

    selection_range: Range
    """The range that should be selected and revealed when this symbol is being picked, e.g. the name of a function.
    Must be contained by the {@link CallHierarchyItem.range `range`}."""

    tags: Optional[List[SymbolTag]] = None
    """Tags for this item."""

    detail: Optional[str] = None
    """More detail for this item, e.g. the signature of a function."""

    data: Optional[LSPAny] = None
    """A data entry field that is preserved between a call hierarchy prepare and
    incoming calls or outgoing calls requests."""


@dataclass
class CallHierarchyOptions(CamelSnakeMixin):
    """Call hierarchy options used during static registration.

    @since 3.16.0"""

    # Since: 3.16.0

    work_done_progress: Optional[bool] = None


@dataclass
class CallHierarchyRegistrationOptions(CamelSnakeMixin):
    """Call hierarchy options used during static or dynamic registration.

    @since 3.16.0"""

    # Since: 3.16.0

    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    work_done_progress: Optional[bool] = None

    id: Optional[str] = None
    """The id used to register the request. The id can be used to deregister
    the request again. See also Registration#id."""


@dataclass
class CallHierarchyIncomingCallsParams(CamelSnakeMixin):
    """The parameter of a `callHierarchy/incomingCalls` request.

    @since 3.16.0"""

    # Since: 3.16.0

    item: CallHierarchyItem

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class CallHierarchyIncomingCall(CamelSnakeMixin):
    """Represents an incoming call, e.g. a caller of a method or constructor.

    @since 3.16.0"""

    # Since: 3.16.0

    from_: CallHierarchyItem
    """The item that makes the call."""

    from_ranges: List[Range]
    """The ranges at which the calls appear. This is relative to the caller
    denoted by {@link CallHierarchyIncomingCall.from `this.from`}."""


@dataclass
class CallHierarchyOutgoingCallsParams(CamelSnakeMixin):
    """The parameter of a `callHierarchy/outgoingCalls` request.

    @since 3.16.0"""

    # Since: 3.16.0

    item: CallHierarchyItem

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class CallHierarchyOutgoingCall(CamelSnakeMixin):
    """Represents an outgoing call, e.g. calling a getter from a method or a method from a constructor etc.

    @since 3.16.0"""

    # Since: 3.16.0

    to: CallHierarchyItem
    """The item that is called."""

    from_ranges: List[Range]
    """The range at which this item is called. This is the range relative to the caller, e.g the item
    passed to {@link CallHierarchyItemProvider.provideCallHierarchyOutgoingCalls `provideCallHierarchyOutgoingCalls`}
    and not {@link CallHierarchyOutgoingCall.to `this.to`}."""


@dataclass
class SemanticTokensParams(CamelSnakeMixin):
    """@since 3.16.0"""

    # Since: 3.16.0

    text_document: TextDocumentIdentifier
    """The text document."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class SemanticTokens(CamelSnakeMixin):
    """@since 3.16.0"""

    # Since: 3.16.0

    data: List[int]
    """The actual tokens."""

    result_id: Optional[str] = None
    """An optional result id. If provided and clients support delta updating
    the client will include the result id in the next semantic token request.
    A server can then instead of computing all semantic tokens again simply
    send a delta."""


@dataclass
class SemanticTokensPartialResult(CamelSnakeMixin):
    """@since 3.16.0"""

    # Since: 3.16.0

    data: List[int]


@dataclass
class SemanticTokensOptionsFullType1(CamelSnakeMixin):
    delta: Optional[bool] = None
    """The server supports deltas for full documents."""


@dataclass
class SemanticTokensOptions(CamelSnakeMixin):
    """@since 3.16.0"""

    # Since: 3.16.0

    legend: SemanticTokensLegend
    """The legend used by the server"""

    range: Optional[Union[bool, Any]] = None
    """Server supports providing semantic tokens for a specific range
    of a document."""

    full: Optional[Union[bool, SemanticTokensOptionsFullType1]] = None
    """Server supports providing semantic tokens for a full document."""

    work_done_progress: Optional[bool] = None


@dataclass
class SemanticTokensRegistrationOptionsFullType1(CamelSnakeMixin):
    delta: Optional[bool] = None
    """The server supports deltas for full documents."""


@dataclass
class SemanticTokensRegistrationOptions(CamelSnakeMixin):
    """@since 3.16.0"""

    # Since: 3.16.0

    legend: SemanticTokensLegend
    """The legend used by the server"""

    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    range: Optional[Union[bool, Any]] = None
    """Server supports providing semantic tokens for a specific range
    of a document."""

    full: Optional[Union[bool, SemanticTokensRegistrationOptionsFullType1]] = None
    """Server supports providing semantic tokens for a full document."""

    work_done_progress: Optional[bool] = None

    id: Optional[str] = None
    """The id used to register the request. The id can be used to deregister
    the request again. See also Registration#id."""


@dataclass
class SemanticTokensDeltaParams(CamelSnakeMixin):
    """@since 3.16.0"""

    # Since: 3.16.0

    text_document: TextDocumentIdentifier
    """The text document."""

    previous_result_id: str
    """The result id of a previous response. The result Id can either point to a full response
    or a delta response depending on what was received last."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class SemanticTokensDelta(CamelSnakeMixin):
    """@since 3.16.0"""

    # Since: 3.16.0

    edits: List[SemanticTokensEdit]
    """The semantic token edits to transform a previous result into a new result."""

    result_id: Optional[str] = None


@dataclass
class SemanticTokensDeltaPartialResult(CamelSnakeMixin):
    """@since 3.16.0"""

    # Since: 3.16.0

    edits: List[SemanticTokensEdit]


@dataclass
class SemanticTokensRangeParams(CamelSnakeMixin):
    """@since 3.16.0"""

    # Since: 3.16.0

    text_document: TextDocumentIdentifier
    """The text document."""

    range: Range
    """The range the semantic tokens are requested for."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class ShowDocumentParams(CamelSnakeMixin):
    """Params to show a document.

    @since 3.16.0"""

    # Since: 3.16.0

    uri: URI
    """The document uri to show."""

    external: Optional[bool] = None
    """Indicates to show the resource in an external program.
    To show for example `https://code.visualstudio.com/`
    in the default WEB browser set `external` to `true`."""

    take_focus: Optional[bool] = None
    """An optional property to indicate whether the editor
    showing the document should take focus or not.
    Clients might ignore this property if an external
    program is started."""

    selection: Optional[Range] = None
    """An optional selection range if the document is a text
    document. Clients might ignore the property if an
    external program is started or the file is not a text
    file."""


@dataclass
class ShowDocumentResult(CamelSnakeMixin):
    """The result of a showDocument request.

    @since 3.16.0"""

    # Since: 3.16.0

    success: bool
    """A boolean indicating if the show was successful."""


@dataclass
class LinkedEditingRangeParams(CamelSnakeMixin):
    text_document: TextDocumentIdentifier
    """The text document."""

    position: Position
    """The position inside the text document."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""


@dataclass
class LinkedEditingRanges(CamelSnakeMixin):
    """The result of a linked editing range request.

    @since 3.16.0"""

    # Since: 3.16.0

    ranges: List[Range]
    """A list of ranges that can be edited together. The ranges must have
    identical length and contain identical text content. The ranges cannot overlap."""

    word_pattern: Optional[str] = None
    """An optional word pattern (regular expression) that describes valid contents for
    the given ranges. If no pattern is provided, the client configuration's word
    pattern will be used."""


@dataclass
class LinkedEditingRangeOptions(CamelSnakeMixin):
    work_done_progress: Optional[bool] = None


@dataclass
class LinkedEditingRangeRegistrationOptions(CamelSnakeMixin):
    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    work_done_progress: Optional[bool] = None

    id: Optional[str] = None
    """The id used to register the request. The id can be used to deregister
    the request again. See also Registration#id."""


@dataclass
class CreateFilesParams(CamelSnakeMixin):
    """The parameters sent in notifications/requests for user-initiated creation of
    files.

    @since 3.16.0"""

    # Since: 3.16.0

    files: List[FileCreate]
    """An array of all files/folders created in this operation."""


@dataclass
class WorkspaceEdit(CamelSnakeMixin):
    """A workspace edit represents changes to many resources managed in the workspace. The edit
    should either provide `changes` or `documentChanges`. If documentChanges are present
    they are preferred over `changes` if the client can handle versioned document edits.

    Since version 3.13.0 a workspace edit can contain resource operations as well. If resource
    operations are present clients need to execute the operations in the order in which they
    are provided. So a workspace edit for example can consist of the following two changes:
    (1) a create file a.txt and (2) a text document edit which insert text into file a.txt.

    An invalid sequence (e.g. (1) delete file a.txt and (2) insert text into file a.txt) will
    cause failure of the operation. How the client recovers from the failure is described by
    the client capability: `workspace.workspaceEdit.failureHandling`"""

    changes: Optional[Dict[DocumentUri, List[TextEdit]]] = None
    """Holds changes to existing resources."""

    document_changes: Optional[List[Union[TextDocumentEdit, CreateFile, RenameFile, DeleteFile]]] = None
    """Depending on the client capability `workspace.workspaceEdit.resourceOperations` document changes
    are either an array of `TextDocumentEdit`s to express changes to n different text documents
    where each text document edit addresses a specific version of a text document. Or it can contain
    above `TextDocumentEdit`s mixed with create, rename and delete file / folder operations.

    Whether a client supports versioned document edits is expressed via
    `workspace.workspaceEdit.documentChanges` client capability.

    If a client neither supports `documentChanges` nor `workspace.workspaceEdit.resourceOperations` then
    only plain `TextEdit`s using the `changes` property are supported."""

    change_annotations: Optional[Dict[ChangeAnnotationIdentifier, ChangeAnnotation]] = None
    """A map of change annotations that can be referenced in `AnnotatedTextEdit`s or create, rename and
    delete file / folder operations.

    Whether clients honor this property depends on the client capability `workspace.changeAnnotationSupport`.

    @since 3.16.0"""
    # Since: 3.16.0


@dataclass
class FileOperationRegistrationOptions(CamelSnakeMixin):
    """The options to register for file operations.

    @since 3.16.0"""

    # Since: 3.16.0

    filters: List[FileOperationFilter]
    """The actual filters."""


@dataclass
class RenameFilesParams(CamelSnakeMixin):
    """The parameters sent in notifications/requests for user-initiated renames of
    files.

    @since 3.16.0"""

    # Since: 3.16.0

    files: List[FileRename]
    """An array of all files/folders renamed in this operation. When a folder is renamed, only
    the folder will be included, and not its children."""


@dataclass
class DeleteFilesParams(CamelSnakeMixin):
    """The parameters sent in notifications/requests for user-initiated deletes of
    files.

    @since 3.16.0"""

    # Since: 3.16.0

    files: List[FileDelete]
    """An array of all files/folders deleted in this operation."""


@dataclass
class MonikerParams(CamelSnakeMixin):
    text_document: TextDocumentIdentifier
    """The text document."""

    position: Position
    """The position inside the text document."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class Moniker(CamelSnakeMixin):
    """Moniker definition to match LSIF 0.5 moniker definition.

    @since 3.16.0"""

    # Since: 3.16.0

    scheme: str
    """The scheme of the moniker. For example tsc or .Net"""

    identifier: str
    """The identifier of the moniker. The value is opaque in LSIF however
    schema owners are allowed to define the structure if they want."""

    unique: UniquenessLevel
    """The scope in which the moniker is unique"""

    kind: Optional[MonikerKind] = None
    """The moniker kind if known."""


@dataclass
class MonikerOptions(CamelSnakeMixin):
    work_done_progress: Optional[bool] = None


@dataclass
class MonikerRegistrationOptions(CamelSnakeMixin):
    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    work_done_progress: Optional[bool] = None


@dataclass
class TypeHierarchyPrepareParams(CamelSnakeMixin):
    """The parameter of a `textDocument/prepareTypeHierarchy` request.

    @since 3.17.0"""

    # Since: 3.17.0

    text_document: TextDocumentIdentifier
    """The text document."""

    position: Position
    """The position inside the text document."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""


@dataclass
class TypeHierarchyItem(CamelSnakeMixin):
    """@since 3.17.0"""

    # Since: 3.17.0

    name: str
    """The name of this item."""

    kind: SymbolKind
    """The kind of this item."""

    uri: DocumentUri
    """The resource identifier of this item."""

    range: Range
    """The range enclosing this symbol not including leading/trailing whitespace
    but everything else, e.g. comments and code."""

    selection_range: Range
    """The range that should be selected and revealed when this symbol is being
    picked, e.g. the name of a function. Must be contained by the
    {@link TypeHierarchyItem.range `range`}."""

    tags: Optional[List[SymbolTag]] = None
    """Tags for this item."""

    detail: Optional[str] = None
    """More detail for this item, e.g. the signature of a function."""

    data: Optional[LSPAny] = None
    """A data entry field that is preserved between a type hierarchy prepare and
    supertypes or subtypes requests. It could also be used to identify the
    type hierarchy in the server, helping improve the performance on
    resolving supertypes and subtypes."""


@dataclass
class TypeHierarchyOptions(CamelSnakeMixin):
    """Type hierarchy options used during static registration.

    @since 3.17.0"""

    # Since: 3.17.0

    work_done_progress: Optional[bool] = None


@dataclass
class TypeHierarchyRegistrationOptions(CamelSnakeMixin):
    """Type hierarchy options used during static or dynamic registration.

    @since 3.17.0"""

    # Since: 3.17.0

    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    work_done_progress: Optional[bool] = None

    id: Optional[str] = None
    """The id used to register the request. The id can be used to deregister
    the request again. See also Registration#id."""


@dataclass
class TypeHierarchySupertypesParams(CamelSnakeMixin):
    """The parameter of a `typeHierarchy/supertypes` request.

    @since 3.17.0"""

    # Since: 3.17.0

    item: TypeHierarchyItem

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class TypeHierarchySubtypesParams(CamelSnakeMixin):
    """The parameter of a `typeHierarchy/subtypes` request.

    @since 3.17.0"""

    # Since: 3.17.0

    item: TypeHierarchyItem

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class InlineValueParams(CamelSnakeMixin):
    """A parameter literal used in inline value requests.

    @since 3.17.0"""

    # Since: 3.17.0

    text_document: TextDocumentIdentifier
    """The text document."""

    range: Range
    """The document range for which inline values should be computed."""

    context: InlineValueContext
    """Additional information about the context in which inline values were
    requested."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""


@dataclass
class InlineValueOptions(CamelSnakeMixin):
    """Inline value options used during static registration.

    @since 3.17.0"""

    # Since: 3.17.0

    work_done_progress: Optional[bool] = None


@dataclass
class InlineValueRegistrationOptions(CamelSnakeMixin):
    """Inline value options used during static or dynamic registration.

    @since 3.17.0"""

    # Since: 3.17.0

    work_done_progress: Optional[bool] = None

    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    id: Optional[str] = None
    """The id used to register the request. The id can be used to deregister
    the request again. See also Registration#id."""


@dataclass
class InlayHintParams(CamelSnakeMixin):
    """A parameter literal used in inlay hint requests.

    @since 3.17.0"""

    # Since: 3.17.0

    text_document: TextDocumentIdentifier
    """The text document."""

    range: Range
    """The document range for which inlay hints should be computed."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""


@dataclass
class InlayHint(CamelSnakeMixin):
    """Inlay hint information.

    @since 3.17.0"""

    # Since: 3.17.0

    position: Position
    """The position of this hint."""

    label: Union[str, List[InlayHintLabelPart]]
    """The label of this hint. A human readable string or an array of
    InlayHintLabelPart label parts.

    *Note* that neither the string nor the label part can be empty."""

    kind: Optional[InlayHintKind] = None
    """The kind of this hint. Can be omitted in which case the client
    should fall back to a reasonable default."""

    text_edits: Optional[List[TextEdit]] = None
    """Optional text edits that are performed when accepting this inlay hint.

    *Note* that edits are expected to change the document so that the inlay
    hint (or its nearest variant) is now part of the document and the inlay
    hint itself is now obsolete."""

    tooltip: Optional[Union[str, MarkupContent]] = None
    """The tooltip text when you hover over this item."""

    padding_left: Optional[bool] = None
    """Render padding before the hint.

    Note: Padding should use the editor's background color, not the
    background color of the hint itself. That means padding can be used
    to visually align/separate an inlay hint."""

    padding_right: Optional[bool] = None
    """Render padding after the hint.

    Note: Padding should use the editor's background color, not the
    background color of the hint itself. That means padding can be used
    to visually align/separate an inlay hint."""

    data: Optional[LSPAny] = None
    """A data entry field that is preserved on an inlay hint between
    a `textDocument/inlayHint` and a `inlayHint/resolve` request."""


@dataclass
class InlayHintOptions(CamelSnakeMixin):
    """Inlay hint options used during static registration.

    @since 3.17.0"""

    # Since: 3.17.0

    resolve_provider: Optional[bool] = None
    """The server provides support to resolve additional
    information for an inlay hint item."""

    work_done_progress: Optional[bool] = None


@dataclass
class InlayHintRegistrationOptions(CamelSnakeMixin):
    """Inlay hint options used during static or dynamic registration.

    @since 3.17.0"""

    # Since: 3.17.0

    resolve_provider: Optional[bool] = None
    """The server provides support to resolve additional
    information for an inlay hint item."""

    work_done_progress: Optional[bool] = None

    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    id: Optional[str] = None
    """The id used to register the request. The id can be used to deregister
    the request again. See also Registration#id."""


@dataclass
class DocumentDiagnosticParams(CamelSnakeMixin):
    """Parameters of the document diagnostic request.

    @since 3.17.0"""

    # Since: 3.17.0

    text_document: TextDocumentIdentifier
    """The text document."""

    identifier: Optional[str] = None
    """The additional identifier  provided during registration."""

    previous_result_id: Optional[str] = None
    """The result id of a previous response if provided."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class DocumentDiagnosticReportPartialResult(CamelSnakeMixin):
    """A partial result for a document diagnostic report.

    @since 3.17.0"""

    # Since: 3.17.0

    related_documents: Dict[
        DocumentUri,
        Union[FullDocumentDiagnosticReport, UnchangedDocumentDiagnosticReport],
    ]


@dataclass
class DiagnosticServerCancellationData(CamelSnakeMixin):
    """Cancellation data returned from a diagnostic request.

    @since 3.17.0"""

    # Since: 3.17.0

    retrigger_request: bool


@dataclass
class DiagnosticOptions(CamelSnakeMixin):
    """Diagnostic options.

    @since 3.17.0"""

    # Since: 3.17.0

    inter_file_dependencies: bool
    """Whether the language has inter file dependencies meaning that
    editing code in one file can result in a different diagnostic
    set in another file. Inter file dependencies are common for
    most programming languages and typically uncommon for linters."""

    workspace_diagnostics: bool
    """The server provides support for workspace diagnostics as well."""

    identifier: Optional[str] = None
    """An optional identifier under which the diagnostics are
    managed by the client."""

    work_done_progress: Optional[bool] = None


@dataclass
class DiagnosticRegistrationOptions(CamelSnakeMixin):
    """Diagnostic registration options.

    @since 3.17.0"""

    # Since: 3.17.0

    inter_file_dependencies: bool
    """Whether the language has inter file dependencies meaning that
    editing code in one file can result in a different diagnostic
    set in another file. Inter file dependencies are common for
    most programming languages and typically uncommon for linters."""

    workspace_diagnostics: bool
    """The server provides support for workspace diagnostics as well."""

    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    identifier: Optional[str] = None
    """An optional identifier under which the diagnostics are
    managed by the client."""

    work_done_progress: Optional[bool] = None

    id: Optional[str] = None
    """The id used to register the request. The id can be used to deregister
    the request again. See also Registration#id."""


@dataclass
class WorkspaceDiagnosticParams(CamelSnakeMixin):
    """Parameters of the workspace diagnostic request.

    @since 3.17.0"""

    # Since: 3.17.0

    previous_result_ids: List[PreviousResultId]
    """The currently known diagnostic reports with their
    previous result ids."""

    identifier: Optional[str] = None
    """The additional identifier provided during registration."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class WorkspaceDiagnosticReport(CamelSnakeMixin):
    """A workspace diagnostic report.

    @since 3.17.0"""

    # Since: 3.17.0

    items: List[WorkspaceDocumentDiagnosticReport]


@dataclass
class WorkspaceDiagnosticReportPartialResult(CamelSnakeMixin):
    """A partial result for a workspace diagnostic report.

    @since 3.17.0"""

    # Since: 3.17.0

    items: List[WorkspaceDocumentDiagnosticReport]


@dataclass
class DidOpenNotebookDocumentParams(CamelSnakeMixin):
    """The params sent in an open notebook document notification.

    @since 3.17.0"""

    # Since: 3.17.0

    notebook_document: NotebookDocument
    """The notebook document that got opened."""

    cell_text_documents: List[TextDocumentItem]
    """The text documents that represent the content
    of a notebook cell."""


@dataclass
class DidChangeNotebookDocumentParams(CamelSnakeMixin):
    """The params sent in a change notebook document notification.

    @since 3.17.0"""

    # Since: 3.17.0

    notebook_document: VersionedNotebookDocumentIdentifier
    """The notebook document that did change. The version number points
    to the version after all provided changes have been applied. If
    only the text document content of a cell changes the notebook version
    doesn't necessarily have to change."""

    change: NotebookDocumentChangeEvent
    """The actual changes to the notebook document.

    The changes describe single state changes to the notebook document.
    So if there are two changes c1 (at array index 0) and c2 (at array
    index 1) for a notebook in state S then c1 moves the notebook from
    S to S' and c2 from S' to S''. So c1 is computed on the state S and
    c2 is computed on the state S'.

    To mirror the content of a notebook using change events use the following approach:
    - start with the same initial content
    - apply the 'notebookDocument/didChange' notifications in the order you receive them.
    - apply the `NotebookChangeEvent`s in a single notification in the order
      you receive them."""


@dataclass
class DidSaveNotebookDocumentParams(CamelSnakeMixin):
    """The params sent in a save notebook document notification.

    @since 3.17.0"""

    # Since: 3.17.0

    notebook_document: NotebookDocumentIdentifier
    """The notebook document that got saved."""


@dataclass
class DidCloseNotebookDocumentParams(CamelSnakeMixin):
    """The params sent in a close notebook document notification.

    @since 3.17.0"""

    # Since: 3.17.0

    notebook_document: NotebookDocumentIdentifier
    """The notebook document that got closed."""

    cell_text_documents: List[TextDocumentIdentifier]
    """The text documents that represent the content
    of a notebook cell that got closed."""


@dataclass
class RegistrationParams(CamelSnakeMixin):
    registrations: List[Registration]


@dataclass
class UnregistrationParams(CamelSnakeMixin):
    unregisterations: List[Unregistration]


@dataclass
class InitializeParamsClientInfoType(CamelSnakeMixin):
    name: str
    """The name of the client as defined by the client."""

    version: Optional[str] = None
    """The client's version as defined by the client."""


@dataclass
class WorkspaceFoldersInitializeParams(CamelSnakeMixin):
    workspace_folders: Optional[List[WorkspaceFolder]] = None
    """The workspace folders configured in the client when the server starts.

    This property is only available if the client supports workspace folders.
    It can be `null` if the client supports workspace folders but none are
    configured.

    @since 3.6.0"""
    # Since: 3.6.0


@dataclass
class InitializeParams(CamelSnakeMixin):
    capabilities: ClientCapabilities
    """The capabilities provided by the client (editor or tool)"""

    process_id: Optional[int] = None
    """The process Id of the parent process that started
    the server.

    Is `null` if the process has not been started by another process.
    If the parent process is not alive then the server should exit."""

    client_info: Optional[InitializeParamsClientInfoType] = None
    """Information about the client

    @since 3.15.0"""
    # Since: 3.15.0

    locale: Optional[str] = None
    """The locale the client is currently showing the user interface
    in. This must not necessarily be the locale of the operating
    system.

    Uses IETF language tags as the value's syntax
    (See https://en.wikipedia.org/wiki/IETF_language_tag)

    @since 3.16.0"""
    # Since: 3.16.0

    root_path: Optional[str] = None
    """The rootPath of the workspace. Is null
    if no folder is open.

    @deprecated in favour of rootUri."""

    root_uri: Optional[DocumentUri] = None
    """The rootUri of the workspace. Is null if no
    folder is open. If both `rootPath` and `rootUri` are set
    `rootUri` wins.

    @deprecated in favour of workspaceFolders."""

    initialization_options: Optional[LSPAny] = None
    """User provided initialization options."""

    trace: Optional[TraceValues] = None
    """The initial trace setting. If omitted trace is disabled ('off')."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    workspace_folders: Optional[List[WorkspaceFolder]] = None
    """The workspace folders configured in the client when the server starts.

    This property is only available if the client supports workspace folders.
    It can be `null` if the client supports workspace folders but none are
    configured.

    @since 3.6.0"""
    # Since: 3.6.0


@dataclass
class InitializeResultServerInfoType(CamelSnakeMixin):
    name: str
    """The name of the server as defined by the server."""

    version: Optional[str] = None
    """The server's version as defined by the server."""


@dataclass
class InitializeResult(CamelSnakeMixin):
    """The result returned from an initialize request."""

    capabilities: ServerCapabilities
    """The capabilities the language server provides."""

    server_info: Optional[InitializeResultServerInfoType] = None
    """Information about the server.

    @since 3.15.0"""
    # Since: 3.15.0


@dataclass
class InitializeError(CamelSnakeMixin):
    """The data type of the ResponseError if the
    initialize request fails."""

    retry: bool
    """Indicates whether the client execute the following retry logic:
    (1) show the message provided by the ResponseError to the user
    (2) user selects retry or cancel
    (3) if user selected retry the initialize method is sent again."""


@dataclass
class InitializedParams(CamelSnakeMixin):
    pass


@dataclass
class DidChangeConfigurationParams(CamelSnakeMixin):
    """The parameters of a change configuration notification."""

    settings: LSPAny
    """The actual changed settings"""


@dataclass
class DidChangeConfigurationRegistrationOptions(CamelSnakeMixin):
    section: Optional[Union[str, List[str]]] = None


@dataclass
class ShowMessageParams(CamelSnakeMixin):
    """The parameters of a notification message."""

    type: MessageType
    """The message type. See {@link MessageType}"""

    message: str
    """The actual message."""


@dataclass
class ShowMessageRequestParams(CamelSnakeMixin):
    type: MessageType
    """The message type. See {@link MessageType}"""

    message: str
    """The actual message."""

    actions: Optional[List[MessageActionItem]] = None
    """The message action items to present."""


@dataclass
class MessageActionItem(CamelSnakeMixin):
    title: str
    """A short title like 'Retry', 'Open Log' etc."""


@dataclass
class LogMessageParams(CamelSnakeMixin):
    """The log message parameters."""

    type: MessageType
    """The message type. See {@link MessageType}"""

    message: str
    """The actual message."""


@dataclass
class DidOpenTextDocumentParams(CamelSnakeMixin):
    """The parameters sent in an open text document notification"""

    text_document: TextDocumentItem
    """The document that was opened."""


@dataclass
class DidChangeTextDocumentParams(CamelSnakeMixin):
    """The change text document notification's parameters."""

    text_document: VersionedTextDocumentIdentifier
    """The document that did change. The version number points
    to the version after all provided content changes have
    been applied."""

    content_changes: List[TextDocumentContentChangeEvent]
    """The actual content changes. The content changes describe single state changes
    to the document. So if there are two content changes c1 (at array index 0) and
    c2 (at array index 1) for a document in state S then c1 moves the document from
    S to S' and c2 from S' to S''. So c1 is computed on the state S and c2 is computed
    on the state S'.

    To mirror the content of a document using change events use the following approach:
    - start with the same initial content
    - apply the 'textDocument/didChange' notifications in the order you receive them.
    - apply the `TextDocumentContentChangeEvent`s in a single notification in the order
      you receive them."""


@dataclass
class TextDocumentChangeRegistrationOptions(CamelSnakeMixin):
    """Describe options to be used when registered for text document change events."""

    sync_kind: TextDocumentSyncKind
    """How documents are synced to the server."""

    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""


@dataclass
class DidCloseTextDocumentParams(CamelSnakeMixin):
    """The parameters sent in a close text document notification"""

    text_document: TextDocumentIdentifier
    """The document that was closed."""


@dataclass
class DidSaveTextDocumentParams(CamelSnakeMixin):
    """The parameters sent in a save text document notification"""

    text_document: TextDocumentIdentifier
    """The document that was saved."""

    text: Optional[str] = None
    """Optional the content when saved. Depends on the includeText value
    when the save notification was requested."""


@dataclass
class SaveOptions(CamelSnakeMixin):
    """Save options."""

    include_text: Optional[bool] = None
    """The client is supposed to include the content on save."""


@dataclass
class TextDocumentSaveRegistrationOptions(CamelSnakeMixin):
    """Save registration options."""

    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    include_text: Optional[bool] = None
    """The client is supposed to include the content on save."""


@dataclass
class WillSaveTextDocumentParams(CamelSnakeMixin):
    """The parameters sent in a will save text document notification."""

    text_document: TextDocumentIdentifier
    """The document that will be saved."""

    reason: TextDocumentSaveReason
    """The 'TextDocumentSaveReason'."""


@dataclass
class TextEdit(CamelSnakeMixin):
    """A text edit applicable to a text document."""

    range: Range
    """The range of the text document to be manipulated. To insert
    text into a document create a range where start === end."""

    new_text: str
    """The string to be inserted. For delete operations use an
    empty string."""


@dataclass
class DidChangeWatchedFilesParams(CamelSnakeMixin):
    """The watched files change notification's parameters."""

    changes: List[FileEvent]
    """The actual file events."""


@dataclass
class DidChangeWatchedFilesRegistrationOptions(CamelSnakeMixin):
    """Describe options to be used when registered for text document change events."""

    watchers: List[FileSystemWatcher]
    """The watchers to register."""


@dataclass
class PublishDiagnosticsParams(CamelSnakeMixin):
    """The publish diagnostic notification's parameters."""

    uri: DocumentUri
    """The URI for which diagnostic information is reported."""

    diagnostics: List[Diagnostic]
    """An array of diagnostic information items."""

    version: Optional[int] = None
    """Optional the version number of the document the diagnostics are published for.

    @since 3.15.0"""
    # Since: 3.15.0


@dataclass
class CompletionParams(CamelSnakeMixin):
    """Completion parameters"""

    text_document: TextDocumentIdentifier
    """The text document."""

    position: Position
    """The position inside the text document."""

    context: Optional[CompletionContext] = None
    """The completion context. This is only available it the client specifies
    to send this using the client capability `textDocument.completion.contextSupport === true`"""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class CompletionItem(CamelSnakeMixin):
    """A completion item represents a text snippet that is
    proposed to complete text that is being typed."""

    label: str
    """The label of this completion item.

    The label property is also by default the text that
    is inserted when selecting this completion.

    If label details are provided the label itself should
    be an unqualified name of the completion item."""

    label_details: Optional[CompletionItemLabelDetails] = None
    """Additional details for the label

    @since 3.17.0"""
    # Since: 3.17.0

    kind: Optional[CompletionItemKind] = None
    """The kind of this completion item. Based of the kind
    an icon is chosen by the editor."""

    tags: Optional[List[CompletionItemTag]] = None
    """Tags for this completion item.

    @since 3.15.0"""
    # Since: 3.15.0

    detail: Optional[str] = None
    """A human-readable string with additional information
    about this item, like type or symbol information."""

    documentation: Optional[Union[str, MarkupContent]] = None
    """A human-readable string that represents a doc-comment."""

    deprecated: Optional[bool] = None
    """Indicates if this item is deprecated.
    @deprecated Use `tags` instead."""

    preselect: Optional[bool] = None
    """Select this item when showing.

    *Note* that only one completion item can be selected and that the
    tool / client decides which item that is. The rule is that the *first*
    item of those that match best is selected."""

    sort_text: Optional[str] = None
    """A string that should be used when comparing this item
    with other items. When `falsy` the {@link CompletionItem.label label}
    is used."""

    filter_text: Optional[str] = None
    """A string that should be used when filtering a set of
    completion items. When `falsy` the {@link CompletionItem.label label}
    is used."""

    insert_text: Optional[str] = None
    """A string that should be inserted into a document when selecting
    this completion. When `falsy` the {@link CompletionItem.label label}
    is used.

    The `insertText` is subject to interpretation by the client side.
    Some tools might not take the string literally. For example
    VS Code when code complete is requested in this example
    `con<cursor position>` and a completion item with an `insertText` of
    `console` is provided it will only insert `sole`. Therefore it is
    recommended to use `textEdit` instead since it avoids additional client
    side interpretation."""

    insert_text_format: Optional[InsertTextFormat] = None
    """The format of the insert text. The format applies to both the
    `insertText` property and the `newText` property of a provided
    `textEdit`. If omitted defaults to `InsertTextFormat.PlainText`.

    Please note that the insertTextFormat doesn't apply to
    `additionalTextEdits`."""

    insert_text_mode: Optional[InsertTextMode] = None
    """How whitespace and indentation is handled during completion
    item insertion. If not provided the clients default value depends on
    the `textDocument.completion.insertTextMode` client capability.

    @since 3.16.0"""
    # Since: 3.16.0

    text_edit: Optional[Union[TextEdit, InsertReplaceEdit]] = None
    """An {@link TextEdit edit} which is applied to a document when selecting
    this completion. When an edit is provided the value of
    {@link CompletionItem.insertText insertText} is ignored.

    Most editors support two different operations when accepting a completion
    item. One is to insert a completion text and the other is to replace an
    existing text with a completion text. Since this can usually not be
    predetermined by a server it can report both ranges. Clients need to
    signal support for `InsertReplaceEdits` via the
    `textDocument.completion.insertReplaceSupport` client capability
    property.

    *Note 1:* The text edit's range as well as both ranges from an insert
    replace edit must be a [single line] and they must contain the position
    at which completion has been requested.
    *Note 2:* If an `InsertReplaceEdit` is returned the edit's insert range
    must be a prefix of the edit's replace range, that means it must be
    contained and starting at the same position.

    @since 3.16.0 additional type `InsertReplaceEdit`"""
    # Since: 3.16.0 additional type `InsertReplaceEdit`

    text_edit_text: Optional[str] = None
    """The edit text used if the completion item is part of a CompletionList and
    CompletionList defines an item default for the text edit range.

    Clients will only honor this property if they opt into completion list
    item defaults using the capability `completionList.itemDefaults`.

    If not provided and a list's default range is provided the label
    property is used as a text.

    @since 3.17.0"""
    # Since: 3.17.0

    additional_text_edits: Optional[List[TextEdit]] = None
    """An optional array of additional {@link TextEdit text edits} that are applied when
    selecting this completion. Edits must not overlap (including the same insert position)
    with the main {@link CompletionItem.textEdit edit} nor with themselves.

    Additional text edits should be used to change text unrelated to the current cursor position
    (for example adding an import statement at the top of the file if the completion item will
    insert an unqualified type)."""

    commit_characters: Optional[List[str]] = None
    """An optional set of characters that when pressed while this completion is active will accept it first and
    then type that character. *Note* that all commit characters should have `length=1` and that superfluous
    characters will be ignored."""

    command: Optional[Command] = None
    """An optional {@link Command command} that is executed *after* inserting this completion. *Note* that
    additional modifications to the current document should be described with the
    {@link CompletionItem.additionalTextEdits additionalTextEdits}-property."""

    data: Optional[LSPAny] = None
    """A data entry field that is preserved on a completion item between a
    {@link CompletionRequest} and a {@link CompletionResolveRequest}."""


@dataclass
class CompletionListItemDefaultsTypeEditRangeType1(CamelSnakeMixin):
    insert: Range

    replace: Range


@dataclass
class CompletionListItemDefaultsType(CamelSnakeMixin):
    commit_characters: Optional[List[str]] = None
    """A default commit character set.

    @since 3.17.0"""
    # Since: 3.17.0

    edit_range: Optional[Union[Range, CompletionListItemDefaultsTypeEditRangeType1]] = None
    """A default edit range.

    @since 3.17.0"""
    # Since: 3.17.0

    insert_text_format: Optional[InsertTextFormat] = None
    """A default insert text format.

    @since 3.17.0"""
    # Since: 3.17.0

    insert_text_mode: Optional[InsertTextMode] = None
    """A default insert text mode.

    @since 3.17.0"""
    # Since: 3.17.0

    data: Optional[LSPAny] = None
    """A default data value.

    @since 3.17.0"""
    # Since: 3.17.0


@dataclass
class CompletionList(CamelSnakeMixin):
    """Represents a collection of {@link CompletionItem completion items} to be presented
    in the editor."""

    is_incomplete: bool
    """This list it not complete. Further typing results in recomputing this list.

    Recomputed lists have all their items replaced (not appended) in the
    incomplete completion sessions."""

    items: List[CompletionItem]
    """The completion items."""

    item_defaults: Optional[CompletionListItemDefaultsType] = None
    """In many cases the items of an actual completion result share the same
    value for properties like `commitCharacters` or the range of a text
    edit. A completion list can therefore define item defaults which will
    be used if a completion item itself doesn't specify the value.

    If a completion list specifies a default value and a completion item
    also specifies a corresponding value the one from the item is used.

    Servers are only allowed to return default values if the client
    signals support for this via the `completionList.itemDefaults`
    capability.

    @since 3.17.0"""
    # Since: 3.17.0


@dataclass
class CompletionOptionsCompletionItemType(CamelSnakeMixin):
    label_details_support: Optional[bool] = None
    """The server has support for completion item label
    details (see also `CompletionItemLabelDetails`) when
    receiving a completion item in a resolve call.

    @since 3.17.0"""
    # Since: 3.17.0


@dataclass
class CompletionOptions(CamelSnakeMixin):
    """Completion options."""

    trigger_characters: Optional[List[str]] = None
    """Most tools trigger completion request automatically without explicitly requesting
    it using a keyboard shortcut (e.g. Ctrl+Space). Typically they do so when the user
    starts to type an identifier. For example if the user types `c` in a JavaScript file
    code complete will automatically pop up present `console` besides others as a
    completion item. Characters that make up identifiers don't need to be listed here.

    If code complete should automatically be trigger on characters not being valid inside
    an identifier (for example `.` in JavaScript) list them in `triggerCharacters`."""

    all_commit_characters: Optional[List[str]] = None
    """The list of all possible characters that commit a completion. This field can be used
    if clients don't support individual commit characters per completion item. See
    `ClientCapabilities.textDocument.completion.completionItem.commitCharactersSupport`

    If a server provides both `allCommitCharacters` and commit characters on an individual
    completion item the ones on the completion item win.

    @since 3.2.0"""
    # Since: 3.2.0

    resolve_provider: Optional[bool] = None
    """The server provides support to resolve additional
    information for a completion item."""

    completion_item: Optional[CompletionOptionsCompletionItemType] = None
    """The server supports the following `CompletionItem` specific
    capabilities.

    @since 3.17.0"""
    # Since: 3.17.0

    work_done_progress: Optional[bool] = None


@dataclass
class CompletionRegistrationOptionsCompletionItemType(CamelSnakeMixin):
    label_details_support: Optional[bool] = None
    """The server has support for completion item label
    details (see also `CompletionItemLabelDetails`) when
    receiving a completion item in a resolve call.

    @since 3.17.0"""
    # Since: 3.17.0


@dataclass
class CompletionRegistrationOptions(CamelSnakeMixin):
    """Registration options for a {@link CompletionRequest}."""

    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    trigger_characters: Optional[List[str]] = None
    """Most tools trigger completion request automatically without explicitly requesting
    it using a keyboard shortcut (e.g. Ctrl+Space). Typically they do so when the user
    starts to type an identifier. For example if the user types `c` in a JavaScript file
    code complete will automatically pop up present `console` besides others as a
    completion item. Characters that make up identifiers don't need to be listed here.

    If code complete should automatically be trigger on characters not being valid inside
    an identifier (for example `.` in JavaScript) list them in `triggerCharacters`."""

    all_commit_characters: Optional[List[str]] = None
    """The list of all possible characters that commit a completion. This field can be used
    if clients don't support individual commit characters per completion item. See
    `ClientCapabilities.textDocument.completion.completionItem.commitCharactersSupport`

    If a server provides both `allCommitCharacters` and commit characters on an individual
    completion item the ones on the completion item win.

    @since 3.2.0"""
    # Since: 3.2.0

    resolve_provider: Optional[bool] = None
    """The server provides support to resolve additional
    information for a completion item."""

    completion_item: Optional[CompletionRegistrationOptionsCompletionItemType] = None
    """The server supports the following `CompletionItem` specific
    capabilities.

    @since 3.17.0"""
    # Since: 3.17.0

    work_done_progress: Optional[bool] = None


@dataclass
class HoverParams(CamelSnakeMixin):
    """Parameters for a {@link HoverRequest}."""

    text_document: TextDocumentIdentifier
    """The text document."""

    position: Position
    """The position inside the text document."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""


@dataclass
class Hover(CamelSnakeMixin):
    """The result of a hover request."""

    contents: Union[MarkupContent, MarkedString, List[MarkedString]]
    """The hover's content"""

    range: Optional[Range] = None
    """An optional range inside the text document that is used to
    visualize the hover, e.g. by changing the background color."""


@dataclass
class HoverOptions(CamelSnakeMixin):
    """Hover options."""

    work_done_progress: Optional[bool] = None


@dataclass
class HoverRegistrationOptions(CamelSnakeMixin):
    """Registration options for a {@link HoverRequest}."""

    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    work_done_progress: Optional[bool] = None


@dataclass
class SignatureHelpParams(CamelSnakeMixin):
    """Parameters for a {@link SignatureHelpRequest}."""

    text_document: TextDocumentIdentifier
    """The text document."""

    position: Position
    """The position inside the text document."""

    context: Optional[SignatureHelpContext] = None
    """The signature help context. This is only available if the client specifies
    to send this using the client capability `textDocument.signatureHelp.contextSupport === true`

    @since 3.15.0"""
    # Since: 3.15.0

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""


@dataclass
class SignatureHelp(CamelSnakeMixin):
    """Signature help represents the signature of something
    callable. There can be multiple signature but only one
    active and only one active parameter."""

    signatures: List[SignatureInformation]
    """One or more signatures."""

    active_signature: Optional[int] = None
    """The active signature. If omitted or the value lies outside the
    range of `signatures` the value defaults to zero or is ignored if
    the `SignatureHelp` has no signatures.

    Whenever possible implementors should make an active decision about
    the active signature and shouldn't rely on a default value.

    In future version of the protocol this property might become
    mandatory to better express this."""

    active_parameter: Optional[int] = None
    """The active parameter of the active signature. If omitted or the value
    lies outside the range of `signatures[activeSignature].parameters`
    defaults to 0 if the active signature has parameters. If
    the active signature has no parameters it is ignored.
    In future version of the protocol this property might become
    mandatory to better express the active parameter if the
    active signature does have any."""


@dataclass
class SignatureHelpOptions(CamelSnakeMixin):
    """Server Capabilities for a {@link SignatureHelpRequest}."""

    trigger_characters: Optional[List[str]] = None
    """List of characters that trigger signature help automatically."""

    retrigger_characters: Optional[List[str]] = None
    """List of characters that re-trigger signature help.

    These trigger characters are only active when signature help is already showing. All trigger characters
    are also counted as re-trigger characters.

    @since 3.15.0"""
    # Since: 3.15.0

    work_done_progress: Optional[bool] = None


@dataclass
class SignatureHelpRegistrationOptions(CamelSnakeMixin):
    """Registration options for a {@link SignatureHelpRequest}."""

    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    trigger_characters: Optional[List[str]] = None
    """List of characters that trigger signature help automatically."""

    retrigger_characters: Optional[List[str]] = None
    """List of characters that re-trigger signature help.

    These trigger characters are only active when signature help is already showing. All trigger characters
    are also counted as re-trigger characters.

    @since 3.15.0"""
    # Since: 3.15.0

    work_done_progress: Optional[bool] = None


@dataclass
class DefinitionParams(CamelSnakeMixin):
    """Parameters for a {@link DefinitionRequest}."""

    text_document: TextDocumentIdentifier
    """The text document."""

    position: Position
    """The position inside the text document."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class DefinitionOptions(CamelSnakeMixin):
    """Server Capabilities for a {@link DefinitionRequest}."""

    work_done_progress: Optional[bool] = None


@dataclass
class DefinitionRegistrationOptions(CamelSnakeMixin):
    """Registration options for a {@link DefinitionRequest}."""

    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    work_done_progress: Optional[bool] = None


@dataclass
class ReferenceParams(CamelSnakeMixin):
    """Parameters for a {@link ReferencesRequest}."""

    context: ReferenceContext

    text_document: TextDocumentIdentifier
    """The text document."""

    position: Position
    """The position inside the text document."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class ReferenceOptions(CamelSnakeMixin):
    """Reference options."""

    work_done_progress: Optional[bool] = None


@dataclass
class ReferenceRegistrationOptions(CamelSnakeMixin):
    """Registration options for a {@link ReferencesRequest}."""

    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    work_done_progress: Optional[bool] = None


@dataclass
class DocumentHighlightParams(CamelSnakeMixin):
    """Parameters for a {@link DocumentHighlightRequest}."""

    text_document: TextDocumentIdentifier
    """The text document."""

    position: Position
    """The position inside the text document."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class DocumentHighlight(CamelSnakeMixin):
    """A document highlight is a range inside a text document which deserves
    special attention. Usually a document highlight is visualized by changing
    the background color of its range."""

    range: Range
    """The range this highlight applies to."""

    kind: Optional[DocumentHighlightKind] = None
    """The highlight kind, default is {@link DocumentHighlightKind.Text text}."""


@dataclass
class DocumentHighlightOptions(CamelSnakeMixin):
    """Provider options for a {@link DocumentHighlightRequest}."""

    work_done_progress: Optional[bool] = None


@dataclass
class DocumentHighlightRegistrationOptions(CamelSnakeMixin):
    """Registration options for a {@link DocumentHighlightRequest}."""

    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    work_done_progress: Optional[bool] = None


@dataclass
class DocumentSymbolParams(CamelSnakeMixin):
    """Parameters for a {@link DocumentSymbolRequest}."""

    text_document: TextDocumentIdentifier
    """The text document."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class BaseSymbolInformation(CamelSnakeMixin):
    """A base for all symbol information."""

    name: str
    """The name of this symbol."""

    kind: SymbolKind
    """The kind of this symbol."""

    tags: Optional[List[SymbolTag]] = None
    """Tags for this symbol.

    @since 3.16.0"""
    # Since: 3.16.0

    container_name: Optional[str] = None
    """The name of the symbol containing this symbol. This information is for
    user interface purposes (e.g. to render a qualifier in the user interface
    if necessary). It can't be used to re-infer a hierarchy for the document
    symbols."""


@dataclass
class SymbolInformation(CamelSnakeMixin):
    """Represents information about programming constructs like variables, classes,
    interfaces etc."""

    location: Location
    """The location of this symbol. The location's range is used by a tool
    to reveal the location in the editor. If the symbol is selected in the
    tool the range's start information is used to position the cursor. So
    the range usually spans more than the actual symbol's name and does
    normally include things like visibility modifiers.

    The range doesn't have to denote a node range in the sense of an abstract
    syntax tree. It can therefore not be used to re-construct a hierarchy of
    the symbols."""

    name: str
    """The name of this symbol."""

    kind: SymbolKind
    """The kind of this symbol."""

    deprecated: Optional[bool] = None
    """Indicates if this symbol is deprecated.

    @deprecated Use tags instead"""

    tags: Optional[List[SymbolTag]] = None
    """Tags for this symbol.

    @since 3.16.0"""
    # Since: 3.16.0

    container_name: Optional[str] = None
    """The name of the symbol containing this symbol. This information is for
    user interface purposes (e.g. to render a qualifier in the user interface
    if necessary). It can't be used to re-infer a hierarchy for the document
    symbols."""


@dataclass
class DocumentSymbol(CamelSnakeMixin):
    """Represents programming constructs like variables, classes, interfaces etc.
    that appear in a document. Document symbols can be hierarchical and they
    have two ranges: one that encloses its definition and one that points to
    its most interesting range, e.g. the range of an identifier."""

    name: str
    """The name of this symbol. Will be displayed in the user interface and therefore must not be
    an empty string or a string only consisting of white spaces."""

    kind: SymbolKind
    """The kind of this symbol."""

    range: Range
    """The range enclosing this symbol not including leading/trailing whitespace but everything else
    like comments. This information is typically used to determine if the clients cursor is
    inside the symbol to reveal in the symbol in the UI."""

    selection_range: Range
    """The range that should be selected and revealed when this symbol is being picked, e.g the name of a function.
    Must be contained by the `range`."""

    detail: Optional[str] = None
    """More detail for this symbol, e.g the signature of a function."""

    tags: Optional[List[SymbolTag]] = None
    """Tags for this document symbol.

    @since 3.16.0"""
    # Since: 3.16.0

    deprecated: Optional[bool] = None
    """Indicates if this symbol is deprecated.

    @deprecated Use tags instead"""

    children: Optional[List[DocumentSymbol]] = None
    """Children of this symbol, e.g. properties of a class."""


@dataclass
class DocumentSymbolOptions(CamelSnakeMixin):
    """Provider options for a {@link DocumentSymbolRequest}."""

    label: Optional[str] = None
    """A human-readable string that is shown when multiple outlines trees
    are shown for the same document.

    @since 3.16.0"""
    # Since: 3.16.0

    work_done_progress: Optional[bool] = None


@dataclass
class DocumentSymbolRegistrationOptions(CamelSnakeMixin):
    """Registration options for a {@link DocumentSymbolRequest}."""

    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    label: Optional[str] = None
    """A human-readable string that is shown when multiple outlines trees
    are shown for the same document.

    @since 3.16.0"""
    # Since: 3.16.0

    work_done_progress: Optional[bool] = None


@dataclass
class CodeActionParams(CamelSnakeMixin):
    """The parameters of a {@link CodeActionRequest}."""

    text_document: TextDocumentIdentifier
    """The document in which the command was invoked."""

    range: Range
    """The range for which the command was invoked."""

    context: CodeActionContext
    """Context carrying additional information."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class Command(CamelSnakeMixin):
    """Represents a reference to a command. Provides a title which
    will be used to represent a command in the UI and, optionally,
    an array of arguments which will be passed to the command handler
    function when invoked."""

    title: str
    """Title of the command, like `save`."""

    command: str
    """The identifier of the actual command handler."""

    arguments: Optional[List[LSPAny]] = None
    """Arguments that the command handler should be
    invoked with."""


@dataclass
class CodeActionDisabledType(CamelSnakeMixin):
    reason: str
    """Human readable description of why the code action is currently disabled.

    This is displayed in the code actions UI."""


@dataclass
class CodeAction(CamelSnakeMixin):
    """A code action represents a change that can be performed in code, e.g. to fix a problem or
    to refactor code.

    A CodeAction must set either `edit` and/or a `command`. If both are supplied, the `edit` is applied first, then the `command` is executed.
    """

    title: str
    """A short, human-readable, title for this code action."""

    kind: Optional[Union[CodeActionKind, str]] = None
    """The kind of the code action.

    Used to filter code actions."""

    diagnostics: Optional[List[Diagnostic]] = None
    """The diagnostics that this code action resolves."""

    is_preferred: Optional[bool] = None
    """Marks this as a preferred action. Preferred actions are used by the `auto fix` command and can be targeted
    by keybindings.

    A quick fix should be marked preferred if it properly addresses the underlying error.
    A refactoring should be marked preferred if it is the most reasonable choice of actions to take.

    @since 3.15.0"""
    # Since: 3.15.0

    disabled: Optional[CodeActionDisabledType] = None
    """Marks that the code action cannot currently be applied.

    Clients should follow the following guidelines regarding disabled code actions:

      - Disabled code actions are not shown in automatic [lightbulbs](https://code.visualstudio.com/docs/editor/editingevolved#_code-action)
        code action menus.

      - Disabled actions are shown as faded out in the code action menu when the user requests a more specific type
        of code action, such as refactorings.

      - If the user has a [keybinding](https://code.visualstudio.com/docs/editor/refactoring#_keybindings-for-code-actions)
        that auto applies a code action and only disabled code actions are returned, the client should show the user an
        error message with `reason` in the editor.

    @since 3.16.0"""
    # Since: 3.16.0

    edit: Optional[WorkspaceEdit] = None
    """The workspace edit this code action performs."""

    command: Optional[Command] = None
    """A command this code action executes. If a code action
    provides an edit and a command, first the edit is
    executed and then the command."""

    data: Optional[LSPAny] = None
    """A data entry field that is preserved on a code action between
    a `textDocument/codeAction` and a `codeAction/resolve` request.

    @since 3.16.0"""
    # Since: 3.16.0


@dataclass
class CodeActionOptions(CamelSnakeMixin):
    """Provider options for a {@link CodeActionRequest}."""

    code_action_kinds: Optional[List[Union[CodeActionKind, str]]] = None
    """CodeActionKinds that this server may return.

    The list of kinds may be generic, such as `CodeActionKind.Refactor`, or the server
    may list out every specific kind they provide."""

    resolve_provider: Optional[bool] = None
    """The server provides support to resolve additional
    information for a code action.

    @since 3.16.0"""
    # Since: 3.16.0

    work_done_progress: Optional[bool] = None


@dataclass
class CodeActionRegistrationOptions(CamelSnakeMixin):
    """Registration options for a {@link CodeActionRequest}."""

    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    code_action_kinds: Optional[List[Union[CodeActionKind, str]]] = None
    """CodeActionKinds that this server may return.

    The list of kinds may be generic, such as `CodeActionKind.Refactor`, or the server
    may list out every specific kind they provide."""

    resolve_provider: Optional[bool] = None
    """The server provides support to resolve additional
    information for a code action.

    @since 3.16.0"""
    # Since: 3.16.0

    work_done_progress: Optional[bool] = None


@dataclass
class WorkspaceSymbolParams(CamelSnakeMixin):
    """The parameters of a {@link WorkspaceSymbolRequest}."""

    query: str
    """A query string to filter symbols by. Clients may send an empty
    string here to request all symbols."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class WorkspaceSymbolLocationType1(CamelSnakeMixin):
    uri: DocumentUri


@dataclass
class WorkspaceSymbol(CamelSnakeMixin):
    """A special workspace symbol that supports locations without a range.

    See also SymbolInformation.

    @since 3.17.0"""

    # Since: 3.17.0

    location: Union[Location, WorkspaceSymbolLocationType1]
    """The location of the symbol. Whether a server is allowed to
    return a location without a range depends on the client
    capability `workspace.symbol.resolveSupport`.

    See SymbolInformation#location for more details."""

    name: str
    """The name of this symbol."""

    kind: SymbolKind
    """The kind of this symbol."""

    data: Optional[LSPAny] = None
    """A data entry field that is preserved on a workspace symbol between a
    workspace symbol request and a workspace symbol resolve request."""

    tags: Optional[List[SymbolTag]] = None
    """Tags for this symbol.

    @since 3.16.0"""
    # Since: 3.16.0

    container_name: Optional[str] = None
    """The name of the symbol containing this symbol. This information is for
    user interface purposes (e.g. to render a qualifier in the user interface
    if necessary). It can't be used to re-infer a hierarchy for the document
    symbols."""


@dataclass
class WorkspaceSymbolOptions(CamelSnakeMixin):
    """Server capabilities for a {@link WorkspaceSymbolRequest}."""

    resolve_provider: Optional[bool] = None
    """The server provides support to resolve additional
    information for a workspace symbol.

    @since 3.17.0"""
    # Since: 3.17.0

    work_done_progress: Optional[bool] = None


@dataclass
class WorkspaceSymbolRegistrationOptions(CamelSnakeMixin):
    """Registration options for a {@link WorkspaceSymbolRequest}."""

    resolve_provider: Optional[bool] = None
    """The server provides support to resolve additional
    information for a workspace symbol.

    @since 3.17.0"""
    # Since: 3.17.0

    work_done_progress: Optional[bool] = None


@dataclass
class CodeLensParams(CamelSnakeMixin):
    """The parameters of a {@link CodeLensRequest}."""

    text_document: TextDocumentIdentifier
    """The document to request code lens for."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class CodeLens(CamelSnakeMixin):
    """A code lens represents a {@link Command command} that should be shown along with
    source text, like the number of references, a way to run tests, etc.

    A code lens is _unresolved_ when no command is associated to it. For performance
    reasons the creation of a code lens and resolving should be done in two stages."""

    range: Range
    """The range in which this code lens is valid. Should only span a single line."""

    command: Optional[Command] = None
    """The command this code lens represents."""

    data: Optional[LSPAny] = None
    """A data entry field that is preserved on a code lens item between
    a {@link CodeLensRequest} and a [CodeLensResolveRequest]
    (#CodeLensResolveRequest)"""


@dataclass
class CodeLensOptions(CamelSnakeMixin):
    """Code Lens provider options of a {@link CodeLensRequest}."""

    resolve_provider: Optional[bool] = None
    """Code lens has a resolve provider as well."""

    work_done_progress: Optional[bool] = None


@dataclass
class CodeLensRegistrationOptions(CamelSnakeMixin):
    """Registration options for a {@link CodeLensRequest}."""

    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    resolve_provider: Optional[bool] = None
    """Code lens has a resolve provider as well."""

    work_done_progress: Optional[bool] = None


@dataclass
class DocumentLinkParams(CamelSnakeMixin):
    """The parameters of a {@link DocumentLinkRequest}."""

    text_document: TextDocumentIdentifier
    """The document to provide document links for."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""

    partial_result_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report partial results (e.g. streaming) to
    the client."""


@dataclass
class DocumentLink(CamelSnakeMixin):
    """A document link is a range in a text document that links to an internal or external resource, like another
    text document or a web site."""

    range: Range
    """The range this link applies to."""

    target: Optional[str] = None
    """The uri this link points to. If missing a resolve request is sent later."""

    tooltip: Optional[str] = None
    """The tooltip text when you hover over this link.

    If a tooltip is provided, is will be displayed in a string that includes instructions on how to
    trigger the link, such as `{0} (ctrl + click)`. The specific instructions vary depending on OS,
    user settings, and localization.

    @since 3.15.0"""
    # Since: 3.15.0

    data: Optional[LSPAny] = None
    """A data entry field that is preserved on a document link between a
    DocumentLinkRequest and a DocumentLinkResolveRequest."""


@dataclass
class DocumentLinkOptions(CamelSnakeMixin):
    """Provider options for a {@link DocumentLinkRequest}."""

    resolve_provider: Optional[bool] = None
    """Document links have a resolve provider as well."""

    work_done_progress: Optional[bool] = None


@dataclass
class DocumentLinkRegistrationOptions(CamelSnakeMixin):
    """Registration options for a {@link DocumentLinkRequest}."""

    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    resolve_provider: Optional[bool] = None
    """Document links have a resolve provider as well."""

    work_done_progress: Optional[bool] = None


@dataclass
class DocumentFormattingParams(CamelSnakeMixin):
    """The parameters of a {@link DocumentFormattingRequest}."""

    text_document: TextDocumentIdentifier
    """The document to format."""

    options: FormattingOptions
    """The format options."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""


@dataclass
class DocumentFormattingOptions(CamelSnakeMixin):
    """Provider options for a {@link DocumentFormattingRequest}."""

    work_done_progress: Optional[bool] = None


@dataclass
class DocumentFormattingRegistrationOptions(CamelSnakeMixin):
    """Registration options for a {@link DocumentFormattingRequest}."""

    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    work_done_progress: Optional[bool] = None


@dataclass
class DocumentRangeFormattingParams(CamelSnakeMixin):
    """The parameters of a {@link DocumentRangeFormattingRequest}."""

    text_document: TextDocumentIdentifier
    """The document to format."""

    range: Range
    """The range to format"""

    options: FormattingOptions
    """The format options"""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""


@dataclass
class DocumentRangeFormattingOptions(CamelSnakeMixin):
    """Provider options for a {@link DocumentRangeFormattingRequest}."""

    work_done_progress: Optional[bool] = None


@dataclass
class DocumentRangeFormattingRegistrationOptions(CamelSnakeMixin):
    """Registration options for a {@link DocumentRangeFormattingRequest}."""

    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    work_done_progress: Optional[bool] = None


@dataclass
class DocumentOnTypeFormattingParams(CamelSnakeMixin):
    """The parameters of a {@link DocumentOnTypeFormattingRequest}."""

    text_document: TextDocumentIdentifier
    """The document to format."""

    position: Position
    """The position around which the on type formatting should happen.
    This is not necessarily the exact position where the character denoted
    by the property `ch` got typed."""

    ch: str
    """The character that has been typed that triggered the formatting
    on type request. That is not necessarily the last character that
    got inserted into the document since the client could auto insert
    characters as well (e.g. like automatic brace completion)."""

    options: FormattingOptions
    """The formatting options."""


@dataclass
class DocumentOnTypeFormattingOptions(CamelSnakeMixin):
    """Provider options for a {@link DocumentOnTypeFormattingRequest}."""

    first_trigger_character: str
    """A character on which formatting should be triggered, like `{`."""

    more_trigger_character: Optional[List[str]] = None
    """More trigger characters."""


@dataclass
class DocumentOnTypeFormattingRegistrationOptions(CamelSnakeMixin):
    """Registration options for a {@link DocumentOnTypeFormattingRequest}."""

    first_trigger_character: str
    """A character on which formatting should be triggered, like `{`."""

    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    more_trigger_character: Optional[List[str]] = None
    """More trigger characters."""


@dataclass
class RenameParams(CamelSnakeMixin):
    """The parameters of a {@link RenameRequest}."""

    text_document: TextDocumentIdentifier
    """The document to rename."""

    position: Position
    """The position at which this request was sent."""

    new_name: str
    """The new name of the symbol. If the given name is not valid the
    request must return a {@link ResponseError} with an
    appropriate message set."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""


@dataclass
class RenameOptions(CamelSnakeMixin):
    """Provider options for a {@link RenameRequest}."""

    prepare_provider: Optional[bool] = None
    """Renames should be checked and tested before being executed.

    @since version 3.12.0"""
    # Since: version 3.12.0

    work_done_progress: Optional[bool] = None


@dataclass
class RenameRegistrationOptions(CamelSnakeMixin):
    """Registration options for a {@link RenameRequest}."""

    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""

    prepare_provider: Optional[bool] = None
    """Renames should be checked and tested before being executed.

    @since version 3.12.0"""
    # Since: version 3.12.0

    work_done_progress: Optional[bool] = None


@dataclass
class PrepareRenameParams(CamelSnakeMixin):
    text_document: TextDocumentIdentifier
    """The text document."""

    position: Position
    """The position inside the text document."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""


@dataclass
class ExecuteCommandParams(CamelSnakeMixin):
    """The parameters of a {@link ExecuteCommandRequest}."""

    command: str
    """The identifier of the actual command handler."""

    arguments: Optional[List[LSPAny]] = None
    """Arguments that the command should be invoked with."""

    work_done_token: Optional[ProgressToken] = None
    """An optional token that a server can use to report work done progress."""


@dataclass
class ExecuteCommandOptions(CamelSnakeMixin):
    """The server capabilities of a {@link ExecuteCommandRequest}."""

    commands: List[str]
    """The commands to be executed on the server"""

    work_done_progress: Optional[bool] = None


@dataclass
class ExecuteCommandRegistrationOptions(CamelSnakeMixin):
    """Registration options for a {@link ExecuteCommandRequest}."""

    commands: List[str]
    """The commands to be executed on the server"""

    work_done_progress: Optional[bool] = None


@dataclass
class ApplyWorkspaceEditParams(CamelSnakeMixin):
    """The parameters passed via a apply workspace edit request."""

    edit: WorkspaceEdit
    """The edits to apply."""

    label: Optional[str] = None
    """An optional label of the workspace edit. This label is
    presented in the user interface for example on an undo
    stack to undo the workspace edit."""


@dataclass
class ApplyWorkspaceEditResult(CamelSnakeMixin):
    """The result returned from the apply workspace edit request.

    @since 3.17 renamed from ApplyWorkspaceEditResponse"""

    # Since: 3.17 renamed from ApplyWorkspaceEditResponse

    applied: bool
    """Indicates whether the edit was applied or not."""

    failure_reason: Optional[str] = None
    """An optional textual description for why the edit was not applied.
    This may be used by the server for diagnostic logging or to provide
    a suitable error for a request that triggered the edit."""

    failed_change: Optional[int] = None
    """Depending on the client's failure handling strategy `failedChange` might
    contain the index of the change that failed. This property is only available
    if the client signals a `failureHandlingStrategy` in its client capabilities."""


@dataclass
class WorkDoneProgressBegin(CamelSnakeMixin):
    title: str
    """Mandatory title of the progress operation. Used to briefly inform about
    the kind of operation being performed.

    Examples: "Indexing" or "Linking dependencies"."""

    kind: Literal["begin"] = "begin"

    cancellable: Optional[bool] = None
    """Controls if a cancel button should show to allow the user to cancel the
    long running operation. Clients that don't support cancellation are allowed
    to ignore the setting."""

    message: Optional[str] = None
    """Optional, more detailed associated progress message. Contains
    complementary information to the `title`.

    Examples: "3/25 files", "project/src/module2", "node_modules/some_dep".
    If unset, the previous progress message (if any) is still valid."""

    percentage: Optional[int] = None
    """Optional progress percentage to display (value 100 is considered 100%).
    If not provided infinite progress is assumed and clients are allowed
    to ignore the `percentage` value in subsequent in report notifications.

    The value should be steadily rising. Clients are free to ignore values
    that are not following this rule. The value range is [0, 100]."""


@dataclass
class WorkDoneProgressReport(CamelSnakeMixin):
    kind: Literal["report"] = "report"

    cancellable: Optional[bool] = None
    """Controls enablement state of a cancel button.

    Clients that don't support cancellation or don't support controlling the button's
    enablement state are allowed to ignore the property."""

    message: Optional[str] = None
    """Optional, more detailed associated progress message. Contains
    complementary information to the `title`.

    Examples: "3/25 files", "project/src/module2", "node_modules/some_dep".
    If unset, the previous progress message (if any) is still valid."""

    percentage: Optional[int] = None
    """Optional progress percentage to display (value 100 is considered 100%).
    If not provided infinite progress is assumed and clients are allowed
    to ignore the `percentage` value in subsequent in report notifications.

    The value should be steadily rising. Clients are free to ignore values
    that are not following this rule. The value range is [0, 100]"""


@dataclass
class WorkDoneProgressEnd(CamelSnakeMixin):
    kind: Literal["end"] = "end"

    message: Optional[str] = None
    """Optional, a final message indicating to for example indicate the outcome
    of the operation."""


@dataclass
class SetTraceParams(CamelSnakeMixin):
    value: TraceValues


@dataclass
class LogTraceParams(CamelSnakeMixin):
    message: str

    verbose: Optional[str] = None


@dataclass
class CancelParams(CamelSnakeMixin):
    id: Union[int, str]
    """The request id to cancel."""


@dataclass
class ProgressParams(CamelSnakeMixin):
    token: ProgressToken
    """The progress token provided by the client or server."""

    value: LSPAny
    """The progress data."""


@dataclass
class LocationLink(CamelSnakeMixin):
    """Represents the connection of two locations. Provides additional metadata over normal {@link Location locations},
    including an origin range."""

    target_uri: DocumentUri
    """The target resource identifier of this link."""

    target_range: Range
    """The full target range of this link. If the target for example is a symbol then target range is the
    range enclosing this symbol not including leading/trailing whitespace but everything else
    like comments. This information is typically used to highlight the range in the editor."""

    target_selection_range: Range
    """The range that should be selected and revealed when this link is being followed, e.g the name of a function.
    Must be contained by the `targetRange`. See also `DocumentSymbol#range`"""

    origin_selection_range: Optional[Range] = None
    """Span of the origin of this link.

    Used as the underlined span for mouse interaction. Defaults to the word range at
    the definition position."""


@dataclass
class Range(CamelSnakeMixin):
    """A range in a text document expressed as (zero-based) start and end positions.

    If you want to specify a range that contains a line including the line ending
    character(s) then use an end position denoting the start of the next line.
    For example:
    ```ts
    {
        start: { line: 5, character: 23 }
        end : { line 6, character : 0 }
    }
    ```"""

    start: Position
    """The range's start position."""

    end: Position
    """The range's end position."""

    def __iter__(self) -> Iterator[Position]:
        return iter((self.start, self.end))

    @staticmethod
    def zero() -> Range:
        return Range(
            start=Position(
                line=0,
                character=0,
            ),
            end=Position(
                line=0,
                character=0,
            ),
        )

    @staticmethod
    def invalid() -> Range:
        return Range(
            start=Position(
                line=-1,
                character=-1,
            ),
            end=Position(
                line=-1,
                character=-1,
            ),
        )

    def extend(
        self,
        start_line: int = 0,
        start_character: int = 0,
        end_line: int = 0,
        end_character: int = 0,
    ) -> Range:
        return Range(
            start=Position(
                line=self.start.line + start_line,
                character=self.start.character + start_character,
            ),
            end=Position(
                line=self.end.line + end_line,
                character=self.end.character + end_character,
            ),
        )

    def __bool__(self) -> bool:
        return self.start != self.end

    def __contains__(self, x: object) -> bool:
        if isinstance(x, (Position, Range)):
            return x.is_in_range(self)
        return False

    def is_in_range(self, range: Range, include_end: bool = True) -> bool:
        return self.start.is_in_range(range, include_end) and self.end.is_in_range(range, include_end)

    def __hash__(self) -> int:
        return hash((self.start, self.end))


@dataclass
class WorkspaceFoldersChangeEvent(CamelSnakeMixin):
    """The workspace folder change event."""

    added: List[WorkspaceFolder]
    """The array of added workspace folders"""

    removed: List[WorkspaceFolder]
    """The array of the removed workspace folders"""


@dataclass
class ConfigurationItem(CamelSnakeMixin):
    scope_uri: Optional[str] = None
    """The scope to get the configuration section for."""

    section: Optional[str] = None
    """The configuration section asked for."""


@dataclass
class TextDocumentIdentifier(CamelSnakeMixin):
    """A literal to identify a text document in the client."""

    uri: DocumentUri
    """The text document's uri."""


@dataclass
class Color(CamelSnakeMixin):
    """Represents a color in RGBA space."""

    red: float
    """The red component of this color in the range [0-1]."""

    green: float
    """The green component of this color in the range [0-1]."""

    blue: float
    """The blue component of this color in the range [0-1]."""

    alpha: float
    """The alpha component of this color in the range [0-1]."""


@dataclass
@functools.total_ordering
class Position(CamelSnakeMixin):
    """Position in a text document expressed as zero-based line and character
    offset. Prior to 3.17 the offsets were always based on a UTF-16 string
    representation. So a string of the form `a𐐀b` the character offset of the
    character `a` is 0, the character offset of `𐐀` is 1 and the character
    offset of b is 3 since `𐐀` is represented using two code units in UTF-16.
    Since 3.17 clients and servers can agree on a different string encoding
    representation (e.g. UTF-8). The client announces it's supported encoding
    via the client capability [`general.positionEncodings`](#clientCapabilities).
    The value is an array of position encodings the client supports, with
    decreasing preference (e.g. the encoding at index `0` is the most preferred
    one). To stay backwards compatible the only mandatory encoding is UTF-16
    represented via the string `utf-16`. The server can pick one of the
    encodings offered by the client and signals that encoding back to the
    client via the initialize result's property
    [`capabilities.positionEncoding`](#serverCapabilities). If the string value
    `utf-16` is missing from the client's capability `general.positionEncodings`
    servers can safely assume that the client supports UTF-16. If the server
    omits the position encoding in its initialize result the encoding defaults
    to the string value `utf-16`. Implementation considerations: since the
    conversion from one encoding into another requires the content of the
    file / line the conversion is best done where the file is read which is
    usually on the server side.

    Positions are line end character agnostic. So you can not specify a position
    that denotes `\r|\n` or `\n|` where `|` represents the character offset.

    @since 3.17.0 - support for negotiated position encoding."""

    # Since: 3.17.0 - support for negotiated position encoding.

    line: int
    """Line position in a document (zero-based).

    If a line number is greater than the number of lines in a document, it defaults back to the number of lines in the document.
    If a line number is negative, it defaults to 0."""

    character: int
    """Character offset on a line in a document (zero-based).

    The meaning of this offset is determined by the negotiated
    `PositionEncodingKind`.

    If the character value is greater than the line length it defaults back to the
    line length."""

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Position):
            return NotImplemented
        return (self.line, self.character) == (o.line, o.character)

    def __gt__(self, o: object) -> bool:
        if not isinstance(o, Position):
            return NotImplemented
        return (self.line, self.character) > (o.line, o.character)

    def __iter__(self) -> Iterator[int]:
        return iter((self.line, self.character))

    def is_in_range(self, range: Range, include_end: bool = True) -> bool:
        if include_end:
            return range.start <= self <= range.end
        return range.start <= self < range.end

    def __hash__(self) -> int:
        return hash((self.line, self.character))


@dataclass
class SemanticTokensEdit(CamelSnakeMixin):
    """@since 3.16.0"""

    # Since: 3.16.0

    start: int
    """The start offset of the edit."""

    delete_count: int
    """The count of elements to remove."""

    data: Optional[List[int]] = None
    """The elements to insert."""


@dataclass
class FileCreate(CamelSnakeMixin):
    """Represents information on a file/folder create.

    @since 3.16.0"""

    # Since: 3.16.0

    uri: str
    """A file:// URI for the location of the file/folder being created."""


@dataclass
class TextDocumentEdit(CamelSnakeMixin):
    """Describes textual changes on a text document. A TextDocumentEdit describes all changes
    on a document version Si and after they are applied move the document to version Si+1.
    So the creator of a TextDocumentEdit doesn't need to sort the array of edits or do any
    kind of ordering. However the edits must be non overlapping."""

    text_document: OptionalVersionedTextDocumentIdentifier
    """The text document to change."""

    edits: List[Union[TextEdit, AnnotatedTextEdit]]
    """The edits to be applied.

    @since 3.16.0 - support for AnnotatedTextEdit. This is guarded using a
    client capability."""
    # Since: 3.16.0 - support for AnnotatedTextEdit. This is guarded using aclient capability.


@dataclass
class ResourceOperation(CamelSnakeMixin):
    """A generic resource operation."""

    kind: str
    """The resource operation kind."""

    annotation_id: Optional[ChangeAnnotationIdentifier] = None
    """An optional annotation identifier describing the operation.

    @since 3.16.0"""
    # Since: 3.16.0


@dataclass
class CreateFile(CamelSnakeMixin):
    """Create file operation."""

    uri: DocumentUri
    """The resource to create."""

    kind: Literal["create"] = "create"
    """A create"""

    options: Optional[CreateFileOptions] = None
    """Additional options"""

    annotation_id: Optional[ChangeAnnotationIdentifier] = None
    """An optional annotation identifier describing the operation.

    @since 3.16.0"""
    # Since: 3.16.0


@dataclass
class RenameFile(CamelSnakeMixin):
    """Rename file operation"""

    old_uri: DocumentUri
    """The old (existing) location."""

    new_uri: DocumentUri
    """The new location."""

    kind: Literal["rename"] = "rename"
    """A rename"""

    options: Optional[RenameFileOptions] = None
    """Rename options."""

    annotation_id: Optional[ChangeAnnotationIdentifier] = None
    """An optional annotation identifier describing the operation.

    @since 3.16.0"""
    # Since: 3.16.0


@dataclass
class DeleteFile(CamelSnakeMixin):
    """Delete file operation"""

    uri: DocumentUri
    """The file to delete."""

    kind: Literal["delete"] = "delete"
    """A delete"""

    options: Optional[DeleteFileOptions] = None
    """Delete options."""

    annotation_id: Optional[ChangeAnnotationIdentifier] = None
    """An optional annotation identifier describing the operation.

    @since 3.16.0"""
    # Since: 3.16.0


@dataclass
class ChangeAnnotation(CamelSnakeMixin):
    """Additional information that describes document changes.

    @since 3.16.0"""

    # Since: 3.16.0

    label: str
    """A human-readable string describing the actual change. The string
    is rendered prominent in the user interface."""

    needs_confirmation: Optional[bool] = None
    """A flag which indicates that user confirmation is needed
    before applying the change."""

    description: Optional[str] = None
    """A human-readable string which is rendered less prominent in
    the user interface."""


@dataclass
class FileOperationFilter(CamelSnakeMixin):
    """A filter to describe in which file operation requests or notifications
    the server is interested in receiving.

    @since 3.16.0"""

    # Since: 3.16.0

    pattern: FileOperationPattern
    """The actual file operation pattern."""

    scheme: Optional[str] = None
    """A Uri scheme like `file` or `untitled`."""


@dataclass
class FileRename(CamelSnakeMixin):
    """Represents information on a file/folder rename.

    @since 3.16.0"""

    # Since: 3.16.0

    old_uri: str
    """A file:// URI for the original location of the file/folder being renamed."""

    new_uri: str
    """A file:// URI for the new location of the file/folder being renamed."""


@dataclass
class FileDelete(CamelSnakeMixin):
    """Represents information on a file/folder delete.

    @since 3.16.0"""

    # Since: 3.16.0

    uri: str
    """A file:// URI for the location of the file/folder being deleted."""


@dataclass
class InlineValueContext(CamelSnakeMixin):
    """@since 3.17.0"""

    # Since: 3.17.0

    frame_id: int
    """The stack frame (as a DAP Id) where the execution has stopped."""

    stopped_location: Range
    """The document range where execution has stopped.
    Typically the end position of the range denotes the line where the inline values are shown."""


@dataclass
class InlineValueText(CamelSnakeMixin):
    """Provide inline value as text.

    @since 3.17.0"""

    # Since: 3.17.0

    range: Range
    """The document range for which the inline value applies."""

    text: str
    """The text of the inline value."""


@dataclass
class InlineValueVariableLookup(CamelSnakeMixin):
    """Provide inline value through a variable lookup.
    If only a range is specified, the variable name will be extracted from the underlying document.
    An optional variable name can be used to override the extracted name.

    @since 3.17.0"""

    # Since: 3.17.0

    range: Range
    """The document range for which the inline value applies.
    The range is used to extract the variable name from the underlying document."""

    case_sensitive_lookup: bool
    """How to perform the lookup."""

    variable_name: Optional[str] = None
    """If specified the name of the variable to look up."""


@dataclass
class InlineValueEvaluatableExpression(CamelSnakeMixin):
    """Provide an inline value through an expression evaluation.
    If only a range is specified, the expression will be extracted from the underlying document.
    An optional expression can be used to override the extracted expression.

    @since 3.17.0"""

    # Since: 3.17.0

    range: Range
    """The document range for which the inline value applies.
    The range is used to extract the evaluatable expression from the underlying document."""

    expression: Optional[str] = None
    """If specified the expression overrides the extracted expression."""


@dataclass
class InlayHintLabelPart(CamelSnakeMixin):
    """An inlay hint label part allows for interactive and composite labels
    of inlay hints.

    @since 3.17.0"""

    # Since: 3.17.0

    value: str
    """The value of this label part."""

    tooltip: Optional[Union[str, MarkupContent]] = None
    """The tooltip text when you hover over this label part. Depending on
    the client capability `inlayHint.resolveSupport` clients might resolve
    this property late using the resolve request."""

    location: Optional[Location] = None
    """An optional source code location that represents this
    label part.

    The editor will use this location for the hover and for code navigation
    features: This part will become a clickable link that resolves to the
    definition of the symbol at the given location (not necessarily the
    location itself), it shows the hover that shows at the given location,
    and it shows a context menu with further code navigation commands.

    Depending on the client capability `inlayHint.resolveSupport` clients
    might resolve this property late using the resolve request."""

    command: Optional[Command] = None
    """An optional command for this label part.

    Depending on the client capability `inlayHint.resolveSupport` clients
    might resolve this property late using the resolve request."""


@dataclass
class MarkupContent(CamelSnakeMixin):
    """A `MarkupContent` literal represents a string value which content is interpreted base on its
    kind flag. Currently the protocol supports `plaintext` and `markdown` as markup kinds.

    If the kind is `markdown` then the value can contain fenced code blocks like in GitHub issues.
    See https://help.github.com/articles/creating-and-highlighting-code-blocks/#syntax-highlighting

    Here is an example how such a string can be constructed using JavaScript / TypeScript:
    ```ts
    let markdown: MarkdownContent = {
     kind: MarkupKind.Markdown,
     value: [
       '# Header',
       'Some text',
       '```typescript',
       'someCode();',
       '```'
     ].join('\n')
    };
    ```

    *Please Note* that clients might sanitize the return markdown. A client could decide to
    remove HTML from the markdown to avoid script execution."""

    kind: MarkupKind
    """The type of the Markup"""

    value: str
    """The content itself"""


@dataclass
class FullDocumentDiagnosticReport(CamelSnakeMixin):
    """A diagnostic report with a full set of problems.

    @since 3.17.0"""

    # Since: 3.17.0

    items: List[Diagnostic]
    """The actual items."""

    kind: Literal["full"] = "full"
    """A full document diagnostic report."""

    result_id: Optional[str] = None
    """An optional result id. If provided it will
    be sent on the next diagnostic request for the
    same document."""


@dataclass
class RelatedFullDocumentDiagnosticReport(CamelSnakeMixin):
    """A full diagnostic report with a set of related documents.

    @since 3.17.0"""

    # Since: 3.17.0

    items: List[Diagnostic]
    """The actual items."""

    related_documents: Optional[
        Dict[
            DocumentUri,
            Union[FullDocumentDiagnosticReport, UnchangedDocumentDiagnosticReport],
        ]
    ] = None
    """Diagnostics of related documents. This information is useful
    in programming languages where code in a file A can generate
    diagnostics in a file B which A depends on. An example of
    such a language is C/C++ where marco definitions in a file
    a.cpp and result in errors in a header file b.hpp.

    @since 3.17.0"""
    # Since: 3.17.0

    kind: Literal["full"] = "full"
    """A full document diagnostic report."""

    result_id: Optional[str] = None
    """An optional result id. If provided it will
    be sent on the next diagnostic request for the
    same document."""


@dataclass
class UnchangedDocumentDiagnosticReport(CamelSnakeMixin):
    """A diagnostic report indicating that the last returned
    report is still accurate.

    @since 3.17.0"""

    # Since: 3.17.0

    result_id: str
    """A result id which will be sent on the next
    diagnostic request for the same document."""

    kind: Literal["unchanged"] = "unchanged"
    """A document diagnostic report indicating
    no changes to the last result. A server can
    only return `unchanged` if result ids are
    provided."""


@dataclass
class RelatedUnchangedDocumentDiagnosticReport(CamelSnakeMixin):
    """An unchanged diagnostic report with a set of related documents.

    @since 3.17.0"""

    # Since: 3.17.0

    result_id: str
    """A result id which will be sent on the next
    diagnostic request for the same document."""

    related_documents: Optional[
        Dict[
            DocumentUri,
            Union[FullDocumentDiagnosticReport, UnchangedDocumentDiagnosticReport],
        ]
    ] = None
    """Diagnostics of related documents. This information is useful
    in programming languages where code in a file A can generate
    diagnostics in a file B which A depends on. An example of
    such a language is C/C++ where marco definitions in a file
    a.cpp and result in errors in a header file b.hpp.

    @since 3.17.0"""
    # Since: 3.17.0

    kind: Literal["unchanged"] = "unchanged"
    """A document diagnostic report indicating
    no changes to the last result. A server can
    only return `unchanged` if result ids are
    provided."""


@dataclass
class PreviousResultId(CamelSnakeMixin):
    """A previous result id in a workspace pull request.

    @since 3.17.0"""

    # Since: 3.17.0

    uri: DocumentUri
    """The URI for which the client knowns a
    result id."""

    value: str
    """The value of the previous result id."""


@dataclass
class NotebookDocument(CamelSnakeMixin):
    """A notebook document.

    @since 3.17.0"""

    # Since: 3.17.0

    uri: URI
    """The notebook document's uri."""

    notebook_type: str
    """The type of the notebook."""

    version: int
    """The version number of this document (it will increase after each
    change, including undo/redo)."""

    cells: List[NotebookCell]
    """The cells of a notebook."""

    metadata: Optional[LSPObject] = None
    """Additional metadata stored with the notebook
    document.

    Note: should always be an object literal (e.g. LSPObject)"""


@dataclass
class TextDocumentItem(CamelSnakeMixin):
    """An item to transfer a text document from the client to the
    server."""

    uri: DocumentUri
    """The text document's uri."""

    language_id: str
    """The text document's language identifier."""

    version: int
    """The version number of this document (it will increase after each
    change, including undo/redo)."""

    text: str
    """The content of the opened text document."""


@dataclass
class VersionedNotebookDocumentIdentifier(CamelSnakeMixin):
    """A versioned notebook document identifier.

    @since 3.17.0"""

    # Since: 3.17.0

    version: int
    """The version number of this notebook document."""

    uri: URI
    """The notebook document's uri."""


@dataclass
class NotebookDocumentChangeEventCellsTypeStructureType(CamelSnakeMixin):
    array: NotebookCellArrayChange
    """The change to the cell array."""

    did_open: Optional[List[TextDocumentItem]] = None
    """Additional opened cell text documents."""

    did_close: Optional[List[TextDocumentIdentifier]] = None
    """Additional closed cell text documents."""


@dataclass
class NotebookDocumentChangeEventCellsTypeTextContentType(CamelSnakeMixin):
    document: VersionedTextDocumentIdentifier

    changes: List[TextDocumentContentChangeEvent]


@dataclass
class NotebookDocumentChangeEventCellsType(CamelSnakeMixin):
    structure: Optional[NotebookDocumentChangeEventCellsTypeStructureType] = None
    """Changes to the cell structure to add or
    remove cells."""

    data: Optional[List[NotebookCell]] = None
    """Changes to notebook cells properties like its
    kind, execution summary or metadata."""

    text_content: Optional[List[NotebookDocumentChangeEventCellsTypeTextContentType]] = None
    """Changes to the text content of notebook cells."""


@dataclass
class NotebookDocumentChangeEvent(CamelSnakeMixin):
    """A change event for a notebook document.

    @since 3.17.0"""

    # Since: 3.17.0

    metadata: Optional[LSPObject] = None
    """The changed meta data if any.

    Note: should always be an object literal (e.g. LSPObject)"""

    cells: Optional[NotebookDocumentChangeEventCellsType] = None
    """Changes to cells"""


@dataclass
class NotebookDocumentIdentifier(CamelSnakeMixin):
    """A literal to identify a notebook document in the client.

    @since 3.17.0"""

    # Since: 3.17.0

    uri: URI
    """The notebook document's uri."""


@dataclass
class Registration(CamelSnakeMixin):
    """General parameters to to register for an notification or to register a provider."""

    id: str
    """The id used to register the request. The id can be used to deregister
    the request again."""

    method: str
    """The method / capability to register for."""

    register_options: Optional[LSPAny] = None
    """Options necessary for the registration."""


@dataclass
class Unregistration(CamelSnakeMixin):
    """General parameters to unregister a request or notification."""

    id: str
    """The id used to unregister the request or notification. Usually an id
    provided during the register request."""

    method: str
    """The method to unregister for."""


@dataclass
class ServerCapabilitiesWorkspaceType(CamelSnakeMixin):
    workspace_folders: Optional[WorkspaceFoldersServerCapabilities] = None
    """The server supports workspace folder.

    @since 3.6.0"""
    # Since: 3.6.0

    file_operations: Optional[FileOperationOptions] = None
    """The server is interested in notifications/requests for operations on files.

    @since 3.16.0"""
    # Since: 3.16.0


@dataclass
class ServerCapabilities(CamelSnakeMixin):
    """Defines the capabilities provided by a language
    server."""

    position_encoding: Optional[Union[PositionEncodingKind, str]] = None
    """The position encoding the server picked from the encodings offered
    by the client via the client capability `general.positionEncodings`.

    If the client didn't provide any position encodings the only valid
    value that a server can return is 'utf-16'.

    If omitted it defaults to 'utf-16'.

    @since 3.17.0"""
    # Since: 3.17.0

    text_document_sync: Optional[Union[TextDocumentSyncOptions, TextDocumentSyncKind]] = None
    """Defines how text documents are synced. Is either a detailed structure
    defining each notification or for backwards compatibility the
    TextDocumentSyncKind number."""

    notebook_document_sync: Optional[Union[NotebookDocumentSyncOptions, NotebookDocumentSyncRegistrationOptions]] = None
    """Defines how notebook documents are synced.

    @since 3.17.0"""
    # Since: 3.17.0

    completion_provider: Optional[CompletionOptions] = None
    """The server provides completion support."""

    hover_provider: Optional[Union[bool, HoverOptions]] = None
    """The server provides hover support."""

    signature_help_provider: Optional[SignatureHelpOptions] = None
    """The server provides signature help support."""

    declaration_provider: Optional[Union[bool, DeclarationOptions, DeclarationRegistrationOptions]] = None
    """The server provides Goto Declaration support."""

    definition_provider: Optional[Union[bool, DefinitionOptions]] = None
    """The server provides goto definition support."""

    type_definition_provider: Optional[Union[bool, TypeDefinitionOptions, TypeDefinitionRegistrationOptions]] = None
    """The server provides Goto Type Definition support."""

    implementation_provider: Optional[Union[bool, ImplementationOptions, ImplementationRegistrationOptions]] = None
    """The server provides Goto Implementation support."""

    references_provider: Optional[Union[bool, ReferenceOptions]] = None
    """The server provides find references support."""

    document_highlight_provider: Optional[Union[bool, DocumentHighlightOptions]] = None
    """The server provides document highlight support."""

    document_symbol_provider: Optional[Union[bool, DocumentSymbolOptions]] = None
    """The server provides document symbol support."""

    code_action_provider: Optional[Union[bool, CodeActionOptions]] = None
    """The server provides code actions. CodeActionOptions may only be
    specified if the client states that it supports
    `codeActionLiteralSupport` in its initial `initialize` request."""

    code_lens_provider: Optional[CodeLensOptions] = None
    """The server provides code lens."""

    document_link_provider: Optional[DocumentLinkOptions] = None
    """The server provides document link support."""

    color_provider: Optional[Union[bool, DocumentColorOptions, DocumentColorRegistrationOptions]] = None
    """The server provides color provider support."""

    workspace_symbol_provider: Optional[Union[bool, WorkspaceSymbolOptions]] = None
    """The server provides workspace symbol support."""

    document_formatting_provider: Optional[Union[bool, DocumentFormattingOptions]] = None
    """The server provides document formatting."""

    document_range_formatting_provider: Optional[Union[bool, DocumentRangeFormattingOptions]] = None
    """The server provides document range formatting."""

    document_on_type_formatting_provider: Optional[DocumentOnTypeFormattingOptions] = None
    """The server provides document formatting on typing."""

    rename_provider: Optional[Union[bool, RenameOptions]] = None
    """The server provides rename support. RenameOptions may only be
    specified if the client states that it supports
    `prepareSupport` in its initial `initialize` request."""

    folding_range_provider: Optional[Union[bool, FoldingRangeOptions, FoldingRangeRegistrationOptions]] = None
    """The server provides folding provider support."""

    selection_range_provider: Optional[Union[bool, SelectionRangeOptions, SelectionRangeRegistrationOptions]] = None
    """The server provides selection range support."""

    execute_command_provider: Optional[ExecuteCommandOptions] = None
    """The server provides execute command support."""

    call_hierarchy_provider: Optional[Union[bool, CallHierarchyOptions, CallHierarchyRegistrationOptions]] = None
    """The server provides call hierarchy support.

    @since 3.16.0"""
    # Since: 3.16.0

    linked_editing_range_provider: Optional[
        Union[bool, LinkedEditingRangeOptions, LinkedEditingRangeRegistrationOptions]
    ] = None
    """The server provides linked editing range support.

    @since 3.16.0"""
    # Since: 3.16.0

    semantic_tokens_provider: Optional[Union[SemanticTokensOptions, SemanticTokensRegistrationOptions]] = None
    """The server provides semantic tokens support.

    @since 3.16.0"""
    # Since: 3.16.0

    moniker_provider: Optional[Union[bool, MonikerOptions, MonikerRegistrationOptions]] = None
    """The server provides moniker support.

    @since 3.16.0"""
    # Since: 3.16.0

    type_hierarchy_provider: Optional[Union[bool, TypeHierarchyOptions, TypeHierarchyRegistrationOptions]] = None
    """The server provides type hierarchy support.

    @since 3.17.0"""
    # Since: 3.17.0

    inline_value_provider: Optional[Union[bool, InlineValueOptions, InlineValueRegistrationOptions]] = None
    """The server provides inline values.

    @since 3.17.0"""
    # Since: 3.17.0

    inlay_hint_provider: Optional[Union[bool, InlayHintOptions, InlayHintRegistrationOptions]] = None
    """The server provides inlay hints.

    @since 3.17.0"""
    # Since: 3.17.0

    diagnostic_provider: Optional[Union[DiagnosticOptions, DiagnosticRegistrationOptions]] = None
    """The server has support for pull model diagnostics.

    @since 3.17.0"""
    # Since: 3.17.0

    workspace: Optional[ServerCapabilitiesWorkspaceType] = None
    """Workspace specific server capabilities."""

    experimental: Optional[LSPAny] = None
    """Experimental server capabilities."""


@dataclass
class VersionedTextDocumentIdentifier(CamelSnakeMixin):
    """A text document identifier to denote a specific version of a text document."""

    version: int
    """The version number of this document."""

    uri: DocumentUri
    """The text document's uri."""


@dataclass
class FileEvent(CamelSnakeMixin):
    """An event describing a file change."""

    uri: DocumentUri
    """The file's uri."""

    type: FileChangeType
    """The change type."""


@dataclass
class FileSystemWatcher(CamelSnakeMixin):
    glob_pattern: GlobPattern
    """The glob pattern to watch. See {@link GlobPattern glob pattern} for more detail.

    @since 3.17.0 support for relative patterns."""
    # Since: 3.17.0 support for relative patterns.

    kind: Optional[Union[WatchKind, int]] = None
    """The kind of events of interest. If omitted it defaults
    to WatchKind.Create | WatchKind.Change | WatchKind.Delete
    which is 7."""


@dataclass
class Diagnostic(CamelSnakeMixin):
    """Represents a diagnostic, such as a compiler error or warning. Diagnostic objects
    are only valid in the scope of a resource."""

    range: Range
    """The range at which the message applies"""

    message: str
    """The diagnostic's message. It usually appears in the user interface"""

    severity: Optional[DiagnosticSeverity] = None
    """The diagnostic's severity. Can be omitted. If omitted it is up to the
    client to interpret diagnostics as error, warning, info or hint."""

    code: Optional[Union[int, str]] = None
    """The diagnostic's code, which usually appear in the user interface."""

    code_description: Optional[CodeDescription] = None
    """An optional property to describe the error code.
    Requires the code field (above) to be present/not null.

    @since 3.16.0"""
    # Since: 3.16.0

    source: Optional[str] = None
    """A human-readable string describing the source of this
    diagnostic, e.g. 'typescript' or 'super lint'. It usually
    appears in the user interface."""

    tags: Optional[List[DiagnosticTag]] = None
    """Additional metadata about the diagnostic.

    @since 3.15.0"""
    # Since: 3.15.0

    related_information: Optional[List[DiagnosticRelatedInformation]] = None
    """An array of related diagnostic information, e.g. when symbol-names within
    a scope collide all definitions can be marked via this property."""

    data: Optional[LSPAny] = None
    """A data entry field that is preserved between a `textDocument/publishDiagnostics`
    notification and `textDocument/codeAction` request.

    @since 3.16.0"""
    # Since: 3.16.0


@dataclass
class CompletionContext(CamelSnakeMixin):
    """Contains additional information about the context in which a completion request is triggered."""

    trigger_kind: CompletionTriggerKind
    """How the completion was triggered."""

    trigger_character: Optional[str] = None
    """The trigger character (a single character) that has trigger code complete.
    Is undefined if `triggerKind !== CompletionTriggerKind.TriggerCharacter`"""


@dataclass
class CompletionItemLabelDetails(CamelSnakeMixin):
    """Additional details for a completion item label.

    @since 3.17.0"""

    # Since: 3.17.0

    detail: Optional[str] = None
    """An optional string which is rendered less prominently directly after {@link CompletionItem.label label},
    without any spacing. Should be used for function signatures and type annotations."""

    description: Optional[str] = None
    """An optional string which is rendered less prominently after {@link CompletionItem.detail}. Should be used
    for fully qualified names and file paths."""


@dataclass
class InsertReplaceEdit(CamelSnakeMixin):
    """A special text edit to provide an insert and a replace operation.

    @since 3.16.0"""

    # Since: 3.16.0

    new_text: str
    """The string to be inserted."""

    insert: Range
    """The range if the insert is requested"""

    replace: Range
    """The range if the replace is requested."""


@dataclass
class SignatureHelpContext(CamelSnakeMixin):
    """Additional information about the context in which a signature help request was triggered.

    @since 3.15.0"""

    # Since: 3.15.0

    trigger_kind: SignatureHelpTriggerKind
    """Action that caused signature help to be triggered."""

    is_retrigger: bool
    """`true` if signature help was already showing when it was triggered.

    Retriggers occurs when the signature help is already active and can be caused by actions such as
    typing a trigger character, a cursor move, or document content changes."""

    trigger_character: Optional[str] = None
    """Character that caused signature help to be triggered.

    This is undefined when `triggerKind !== SignatureHelpTriggerKind.TriggerCharacter`"""

    active_signature_help: Optional[SignatureHelp] = None
    """The currently active `SignatureHelp`.

    The `activeSignatureHelp` has its `SignatureHelp.activeSignature` field updated based on
    the user navigating through available signatures."""


@dataclass
class SignatureInformation(CamelSnakeMixin):
    """Represents the signature of something callable. A signature
    can have a label, like a function-name, a doc-comment, and
    a set of parameters."""

    label: str
    """The label of this signature. Will be shown in
    the UI."""

    documentation: Optional[Union[str, MarkupContent]] = None
    """The human-readable doc-comment of this signature. Will be shown
    in the UI but can be omitted."""

    parameters: Optional[List[ParameterInformation]] = None
    """The parameters of this signature."""

    active_parameter: Optional[int] = None
    """The index of the active parameter.

    If provided, this is used in place of `SignatureHelp.activeParameter`.

    @since 3.16.0"""
    # Since: 3.16.0


@dataclass
class ReferenceContext(CamelSnakeMixin):
    """Value-object that contains additional information when
    requesting references."""

    include_declaration: bool
    """Include the declaration of the current symbol."""


@dataclass
class CodeActionContext(CamelSnakeMixin):
    """Contains additional diagnostic information about the context in which
    a {@link CodeActionProvider.provideCodeActions code action} is run."""

    diagnostics: List[Diagnostic]
    """An array of diagnostics known on the client side overlapping the range provided to the
    `textDocument/codeAction` request. They are provided so that the server knows which
    errors are currently presented to the user for the given range. There is no guarantee
    that these accurately reflect the error state of the resource. The primary parameter
    to compute code actions is the provided range."""

    only: Optional[List[Union[CodeActionKind, str]]] = None
    """Requested kind of actions to return.

    Actions not of this kind are filtered out by the client before being shown. So servers
    can omit computing them."""

    trigger_kind: Optional[CodeActionTriggerKind] = None
    """The reason why code actions were requested.

    @since 3.17.0"""
    # Since: 3.17.0


@dataclass
class FormattingOptions(CamelSnakeMixin):
    """Value-object describing what options formatting should use."""

    tab_size: int
    """Size of a tab in spaces."""

    insert_spaces: bool
    """Prefer spaces over tabs."""

    trim_trailing_whitespace: Optional[bool] = None
    """Trim trailing whitespace on a line.

    @since 3.15.0"""
    # Since: 3.15.0

    insert_final_newline: Optional[bool] = None
    """Insert a newline character at the end of the file if one does not exist.

    @since 3.15.0"""
    # Since: 3.15.0

    trim_final_newlines: Optional[bool] = None
    """Trim all newlines after the final newline at the end of the file.

    @since 3.15.0"""
    # Since: 3.15.0


@dataclass
class SemanticTokensLegend(CamelSnakeMixin):
    """@since 3.16.0"""

    # Since: 3.16.0

    token_types: List[str]
    """The token types a server uses."""

    token_modifiers: List[str]
    """The token modifiers a server uses."""


@dataclass
class OptionalVersionedTextDocumentIdentifier(CamelSnakeMixin):
    """A text document identifier to optionally denote a specific version of a text document."""

    uri: DocumentUri
    """The text document's uri."""

    version: Optional[int]
    """The version number of this document. If a versioned text document identifier
    is sent from the server to the client and the file is not open in the editor
    (the server has not received an open notification before) the server can send
    `null` to indicate that the version is unknown and the content on disk is the
    truth (as specified with document content ownership)."""


@dataclass
class AnnotatedTextEdit(CamelSnakeMixin):
    """A special text edit with an additional change annotation.

    @since 3.16.0."""

    # Since: 3.16.0.
    annotation_id: ChangeAnnotationIdentifier
    """The actual identifier of the change annotation"""

    range: Range
    """The range of the text document to be manipulated. To insert
    text into a document create a range where start === end."""

    new_text: str
    """The string to be inserted. For delete operations use an
    empty string."""


@dataclass
class CreateFileOptions(CamelSnakeMixin):
    """Options to create a file."""

    overwrite: Optional[bool] = None
    """Overwrite existing file. Overwrite wins over `ignoreIfExists`"""

    ignore_if_exists: Optional[bool] = None
    """Ignore if exists."""


@dataclass
class RenameFileOptions(CamelSnakeMixin):
    """Rename file options"""

    overwrite: Optional[bool] = None
    """Overwrite target if existing. Overwrite wins over `ignoreIfExists`"""

    ignore_if_exists: Optional[bool] = None
    """Ignores if target exists."""


@dataclass
class DeleteFileOptions(CamelSnakeMixin):
    """Delete file options"""

    recursive: Optional[bool] = None
    """Delete the content recursively if a folder is denoted."""

    ignore_if_not_exists: Optional[bool] = None
    """Ignore the operation if the file doesn't exist."""


@dataclass
class FileOperationPattern(CamelSnakeMixin):
    """A pattern to describe in which file operation requests or notifications
    the server is interested in receiving.

    @since 3.16.0"""

    # Since: 3.16.0

    glob: str
    """The glob pattern to match. Glob patterns can have the following syntax:
    - `*` to match one or more characters in a path segment
    - `?` to match on one character in a path segment
    - `**` to match any number of path segments, including none
    - `{}` to group sub patterns into an OR expression. (e.g. `**/*.{ts,js}` matches all TypeScript and JavaScript files)
    - `[]` to declare a range of characters to match in a path segment (e.g., `example.[0-9]` to match on `example.0`, `example.1`, …)
    - `[!...]` to negate a range of characters to match in a path segment (e.g., `example.[!0-9]` to match on `example.a`, `example.b`, but not `example.0`)"""

    matches: Optional[FileOperationPatternKind] = None
    """Whether to match files or folders with this pattern.

    Matches both if undefined."""

    options: Optional[FileOperationPatternOptions] = None
    """Additional options used during matching."""


@dataclass
class WorkspaceFullDocumentDiagnosticReport(CamelSnakeMixin):
    """A full document diagnostic report for a workspace diagnostic result.

    @since 3.17.0"""

    # Since: 3.17.0

    uri: DocumentUri
    """The URI for which diagnostic information is reported."""

    items: List[Diagnostic]
    """The actual items."""

    version: Optional[int] = None
    """The version number for which the diagnostics are reported.
    If the document is not marked as open `null` can be provided."""

    kind: Literal["full"] = "full"
    """A full document diagnostic report."""

    result_id: Optional[str] = None
    """An optional result id. If provided it will
    be sent on the next diagnostic request for the
    same document."""


@dataclass
class WorkspaceUnchangedDocumentDiagnosticReport(CamelSnakeMixin):
    """An unchanged document diagnostic report for a workspace diagnostic result.

    @since 3.17.0"""

    # Since: 3.17.0

    uri: DocumentUri
    """The URI for which diagnostic information is reported."""

    result_id: str
    """A result id which will be sent on the next
    diagnostic request for the same document."""

    version: Optional[int] = None
    """The version number for which the diagnostics are reported.
    If the document is not marked as open `null` can be provided."""

    kind: Literal["unchanged"] = "unchanged"
    """A document diagnostic report indicating
    no changes to the last result. A server can
    only return `unchanged` if result ids are
    provided."""


@dataclass
class NotebookCell(CamelSnakeMixin):
    """A notebook cell.

    A cell's document URI must be unique across ALL notebook
    cells and can therefore be used to uniquely identify a
    notebook cell or the cell's text document.

    @since 3.17.0"""

    # Since: 3.17.0

    kind: NotebookCellKind
    """The cell's kind"""

    document: DocumentUri
    """The URI of the cell's text document
    content."""

    metadata: Optional[LSPObject] = None
    """Additional metadata stored with the cell.

    Note: should always be an object literal (e.g. LSPObject)"""

    execution_summary: Optional[ExecutionSummary] = None
    """Additional execution summary information
    if supported by the client."""


@dataclass
class NotebookCellArrayChange(CamelSnakeMixin):
    """A change describing how to move a `NotebookCell`
    array from state S to S'.

    @since 3.17.0"""

    # Since: 3.17.0

    start: int
    """The start oftest of the cell that changed."""

    delete_count: int
    """The deleted cells"""

    cells: Optional[List[NotebookCell]] = None
    """The new cells, if any"""


@dataclass
class ClientCapabilities(CamelSnakeMixin):
    """Defines the capabilities provided by the client."""

    workspace: Optional[WorkspaceClientCapabilities] = None
    """Workspace specific client capabilities."""

    text_document: Optional[TextDocumentClientCapabilities] = None
    """Text document specific client capabilities."""

    notebook_document: Optional[NotebookDocumentClientCapabilities] = None
    """Capabilities specific to the notebook document support.

    @since 3.17.0"""
    # Since: 3.17.0

    window: Optional[WindowClientCapabilities] = None
    """Window specific client capabilities."""

    general: Optional[GeneralClientCapabilities] = None
    """General client capabilities.

    @since 3.16.0"""
    # Since: 3.16.0

    experimental: Optional[LSPAny] = None
    """Experimental client capabilities."""


@dataclass
class TextDocumentSyncOptions(CamelSnakeMixin):
    open_close: Optional[bool] = None
    """Open and close notifications are sent to the server. If omitted open close notification should not
    be sent."""

    change: Optional[TextDocumentSyncKind] = None
    """Change notifications are sent to the server. See TextDocumentSyncKind.None, TextDocumentSyncKind.Full
    and TextDocumentSyncKind.Incremental. If omitted it defaults to TextDocumentSyncKind.None."""

    will_save: Optional[bool] = None
    """If present will save notifications are sent to the server. If omitted the notification should not be
    sent."""

    will_save_wait_until: Optional[bool] = None
    """If present will save wait until requests are sent to the server. If omitted the request should not be
    sent."""

    save: Optional[Union[bool, SaveOptions]] = None
    """If present save notifications are sent to the server. If omitted the notification should not be
    sent."""


@dataclass
class NotebookDocumentSyncOptionsNotebookSelectorType1CellsType(CamelSnakeMixin):
    language: str


@dataclass
class NotebookDocumentSyncOptionsNotebookSelectorType1(CamelSnakeMixin):
    notebook: Union[str, NotebookDocumentFilter]
    """The notebook to be synced If a string
    value is provided it matches against the
    notebook type. '*' matches every notebook."""

    cells: Optional[List[NotebookDocumentSyncOptionsNotebookSelectorType1CellsType]] = None
    """The cells of the matching notebook to be synced."""


@dataclass
class NotebookDocumentSyncOptionsNotebookSelectorType2CellsType(CamelSnakeMixin):
    language: str


@dataclass
class NotebookDocumentSyncOptionsNotebookSelectorType2(CamelSnakeMixin):
    cells: List[NotebookDocumentSyncOptionsNotebookSelectorType2CellsType]
    """The cells of the matching notebook to be synced."""

    notebook: Optional[Union[str, NotebookDocumentFilter]] = None
    """The notebook to be synced If a string
    value is provided it matches against the
    notebook type. '*' matches every notebook."""


@dataclass
class NotebookDocumentSyncOptions(CamelSnakeMixin):
    """Options specific to a notebook plus its cells
    to be synced to the server.

    If a selector provides a notebook document
    filter but no cell selector all cells of a
    matching notebook document will be synced.

    If a selector provides no notebook document
    filter but only a cell selector all notebook
    document that contain at least one matching
    cell will be synced.

    @since 3.17.0"""

    # Since: 3.17.0

    notebook_selector: List[
        Union[
            NotebookDocumentSyncOptionsNotebookSelectorType1,
            NotebookDocumentSyncOptionsNotebookSelectorType2,
        ]
    ]
    """The notebooks to be synced"""

    save: Optional[bool] = None
    """Whether save notification should be forwarded to
    the server. Will only be honored if mode === `notebook`."""


@dataclass
class NotebookDocumentSyncRegistrationOptionsNotebookSelectorType1CellsType(CamelSnakeMixin):
    language: str


@dataclass
class NotebookDocumentSyncRegistrationOptionsNotebookSelectorType1(CamelSnakeMixin):
    notebook: Union[str, NotebookDocumentFilter]
    """The notebook to be synced If a string
    value is provided it matches against the
    notebook type. '*' matches every notebook."""

    cells: Optional[List[NotebookDocumentSyncRegistrationOptionsNotebookSelectorType1CellsType]] = None
    """The cells of the matching notebook to be synced."""


@dataclass
class NotebookDocumentSyncRegistrationOptionsNotebookSelectorType2CellsType(CamelSnakeMixin):
    language: str


@dataclass
class NotebookDocumentSyncRegistrationOptionsNotebookSelectorType2(CamelSnakeMixin):
    cells: List[NotebookDocumentSyncRegistrationOptionsNotebookSelectorType2CellsType]
    """The cells of the matching notebook to be synced."""

    notebook: Optional[Union[str, NotebookDocumentFilter]] = None
    """The notebook to be synced If a string
    value is provided it matches against the
    notebook type. '*' matches every notebook."""


@dataclass
class NotebookDocumentSyncRegistrationOptions(CamelSnakeMixin):
    """Registration options specific to a notebook.

    @since 3.17.0"""

    # Since: 3.17.0

    notebook_selector: List[
        Union[
            NotebookDocumentSyncRegistrationOptionsNotebookSelectorType1,
            NotebookDocumentSyncRegistrationOptionsNotebookSelectorType2,
        ]
    ]
    """The notebooks to be synced"""

    save: Optional[bool] = None
    """Whether save notification should be forwarded to
    the server. Will only be honored if mode === `notebook`."""

    id: Optional[str] = None
    """The id used to register the request. The id can be used to deregister
    the request again. See also Registration#id."""


@dataclass
class WorkspaceFoldersServerCapabilities(CamelSnakeMixin):
    supported: Optional[bool] = None
    """The server has support for workspace folders"""

    change_notifications: Optional[Union[str, bool]] = None
    """Whether the server wants to receive workspace folder
    change notifications.

    If a string is provided the string is treated as an ID
    under which the notification is registered on the client
    side. The ID can be used to unregister for these events
    using the `client/unregisterCapability` request."""


@dataclass
class FileOperationOptions(CamelSnakeMixin):
    """Options for notifications/requests for user operations on files.

    @since 3.16.0"""

    # Since: 3.16.0

    did_create: Optional[FileOperationRegistrationOptions] = None
    """The server is interested in receiving didCreateFiles notifications."""

    will_create: Optional[FileOperationRegistrationOptions] = None
    """The server is interested in receiving willCreateFiles requests."""

    did_rename: Optional[FileOperationRegistrationOptions] = None
    """The server is interested in receiving didRenameFiles notifications."""

    will_rename: Optional[FileOperationRegistrationOptions] = None
    """The server is interested in receiving willRenameFiles requests."""

    did_delete: Optional[FileOperationRegistrationOptions] = None
    """The server is interested in receiving didDeleteFiles file notifications."""

    will_delete: Optional[FileOperationRegistrationOptions] = None
    """The server is interested in receiving willDeleteFiles file requests."""


@dataclass
class CodeDescription(CamelSnakeMixin):
    """Structure to capture a description for an error code.

    @since 3.16.0"""

    # Since: 3.16.0

    href: URI
    """An URI to open with more information about the diagnostic error."""


@dataclass
class DiagnosticRelatedInformation(CamelSnakeMixin):
    """Represents a related message and source code location for a diagnostic. This should be
    used to point to code locations that cause or related to a diagnostics, e.g when duplicating
    a symbol in a scope."""

    location: Location
    """The location of this related diagnostic information."""

    message: str
    """The message of this related diagnostic information."""


@dataclass
class ParameterInformation(CamelSnakeMixin):
    """Represents a parameter of a callable-signature. A parameter can
    have a label and a doc-comment."""

    label: Union[str, Tuple[int, int]]
    """The label of this parameter information.

    Either a string or an inclusive start and exclusive end offsets within its containing
    signature label. (see SignatureInformation.label). The offsets are based on a UTF-16
    string representation as `Position` and `Range` does.

    *Note*: a label of type string should be a substring of its containing signature label.
    Its intended use case is to highlight the parameter label part in the `SignatureInformation.label`."""

    documentation: Optional[Union[str, MarkupContent]] = None
    """The human-readable doc-comment of this parameter. Will be shown
    in the UI but can be omitted."""


@dataclass
class NotebookCellTextDocumentFilter(CamelSnakeMixin):
    """A notebook cell text document filter denotes a cell text
    document by different properties.

    @since 3.17.0"""

    # Since: 3.17.0

    notebook: Union[str, NotebookDocumentFilter]
    """A filter that matches against the notebook
    containing the notebook cell. If a string
    value is provided it matches against the
    notebook type. '*' matches every notebook."""

    language: Optional[str] = None
    """A language id like `python`.

    Will be matched against the language id of the
    notebook cell document. '*' matches every language."""


@dataclass
class FileOperationPatternOptions(CamelSnakeMixin):
    """Matching options for the file operation pattern.

    @since 3.16.0"""

    # Since: 3.16.0

    ignore_case: Optional[bool] = None
    """The pattern should be matched ignoring casing."""


@dataclass
class ExecutionSummary(CamelSnakeMixin):
    execution_order: int
    """A strict monotonically increasing value
    indicating the execution order of a cell
    inside a notebook."""

    success: Optional[bool] = None
    """Whether the execution was successful or
    not if known by the client."""


@dataclass
class WorkspaceClientCapabilities(CamelSnakeMixin):
    """Workspace specific client capabilities."""

    apply_edit: Optional[bool] = None
    """The client supports applying batch edits
    to the workspace by supporting the request
    'workspace/applyEdit'"""

    workspace_edit: Optional[WorkspaceEditClientCapabilities] = None
    """Capabilities specific to `WorkspaceEdit`s."""

    did_change_configuration: Optional[DidChangeConfigurationClientCapabilities] = None
    """Capabilities specific to the `workspace/didChangeConfiguration` notification."""

    did_change_watched_files: Optional[DidChangeWatchedFilesClientCapabilities] = None
    """Capabilities specific to the `workspace/didChangeWatchedFiles` notification."""

    symbol: Optional[WorkspaceSymbolClientCapabilities] = None
    """Capabilities specific to the `workspace/symbol` request."""

    execute_command: Optional[ExecuteCommandClientCapabilities] = None
    """Capabilities specific to the `workspace/executeCommand` request."""

    workspace_folders: Optional[bool] = None
    """The client has support for workspace folders.

    @since 3.6.0"""
    # Since: 3.6.0

    configuration: Optional[bool] = None
    """The client supports `workspace/configuration` requests.

    @since 3.6.0"""
    # Since: 3.6.0

    semantic_tokens: Optional[SemanticTokensWorkspaceClientCapabilities] = None
    """Capabilities specific to the semantic token requests scoped to the
    workspace.

    @since 3.16.0."""
    # Since: 3.16.0.

    code_lens: Optional[CodeLensWorkspaceClientCapabilities] = None
    """Capabilities specific to the code lens requests scoped to the
    workspace.

    @since 3.16.0."""
    # Since: 3.16.0.

    file_operations: Optional[FileOperationClientCapabilities] = None
    """The client has support for file notifications/requests for user operations on files.

    Since 3.16.0"""

    inline_value: Optional[InlineValueWorkspaceClientCapabilities] = None
    """Capabilities specific to the inline values requests scoped to the
    workspace.

    @since 3.17.0."""
    # Since: 3.17.0.

    inlay_hint: Optional[InlayHintWorkspaceClientCapabilities] = None
    """Capabilities specific to the inlay hint requests scoped to the
    workspace.

    @since 3.17.0."""
    # Since: 3.17.0.

    diagnostics: Optional[DiagnosticWorkspaceClientCapabilities] = None
    """Capabilities specific to the diagnostic requests scoped to the
    workspace.

    @since 3.17.0."""
    # Since: 3.17.0.


@dataclass
class TextDocumentClientCapabilities(CamelSnakeMixin):
    """Text document specific client capabilities."""

    synchronization: Optional[TextDocumentSyncClientCapabilities] = None
    """Defines which synchronization capabilities the client supports."""

    completion: Optional[CompletionClientCapabilities] = None
    """Capabilities specific to the `textDocument/completion` request."""

    hover: Optional[HoverClientCapabilities] = None
    """Capabilities specific to the `textDocument/hover` request."""

    signature_help: Optional[SignatureHelpClientCapabilities] = None
    """Capabilities specific to the `textDocument/signatureHelp` request."""

    declaration: Optional[DeclarationClientCapabilities] = None
    """Capabilities specific to the `textDocument/declaration` request.

    @since 3.14.0"""
    # Since: 3.14.0

    definition: Optional[DefinitionClientCapabilities] = None
    """Capabilities specific to the `textDocument/definition` request."""

    type_definition: Optional[TypeDefinitionClientCapabilities] = None
    """Capabilities specific to the `textDocument/typeDefinition` request.

    @since 3.6.0"""
    # Since: 3.6.0

    implementation: Optional[ImplementationClientCapabilities] = None
    """Capabilities specific to the `textDocument/implementation` request.

    @since 3.6.0"""
    # Since: 3.6.0

    references: Optional[ReferenceClientCapabilities] = None
    """Capabilities specific to the `textDocument/references` request."""

    document_highlight: Optional[DocumentHighlightClientCapabilities] = None
    """Capabilities specific to the `textDocument/documentHighlight` request."""

    document_symbol: Optional[DocumentSymbolClientCapabilities] = None
    """Capabilities specific to the `textDocument/documentSymbol` request."""

    code_action: Optional[CodeActionClientCapabilities] = None
    """Capabilities specific to the `textDocument/codeAction` request."""

    code_lens: Optional[CodeLensClientCapabilities] = None
    """Capabilities specific to the `textDocument/codeLens` request."""

    document_link: Optional[DocumentLinkClientCapabilities] = None
    """Capabilities specific to the `textDocument/documentLink` request."""

    color_provider: Optional[DocumentColorClientCapabilities] = None
    """Capabilities specific to the `textDocument/documentColor` and the
    `textDocument/colorPresentation` request.

    @since 3.6.0"""
    # Since: 3.6.0

    formatting: Optional[DocumentFormattingClientCapabilities] = None
    """Capabilities specific to the `textDocument/formatting` request."""

    range_formatting: Optional[DocumentRangeFormattingClientCapabilities] = None
    """Capabilities specific to the `textDocument/rangeFormatting` request."""

    on_type_formatting: Optional[DocumentOnTypeFormattingClientCapabilities] = None
    """Capabilities specific to the `textDocument/onTypeFormatting` request."""

    rename: Optional[RenameClientCapabilities] = None
    """Capabilities specific to the `textDocument/rename` request."""

    folding_range: Optional[FoldingRangeClientCapabilities] = None
    """Capabilities specific to the `textDocument/foldingRange` request.

    @since 3.10.0"""
    # Since: 3.10.0

    selection_range: Optional[SelectionRangeClientCapabilities] = None
    """Capabilities specific to the `textDocument/selectionRange` request.

    @since 3.15.0"""
    # Since: 3.15.0

    publish_diagnostics: Optional[PublishDiagnosticsClientCapabilities] = None
    """Capabilities specific to the `textDocument/publishDiagnostics` notification."""

    call_hierarchy: Optional[CallHierarchyClientCapabilities] = None
    """Capabilities specific to the various call hierarchy requests.

    @since 3.16.0"""
    # Since: 3.16.0

    semantic_tokens: Optional[SemanticTokensClientCapabilities] = None
    """Capabilities specific to the various semantic token request.

    @since 3.16.0"""
    # Since: 3.16.0

    linked_editing_range: Optional[LinkedEditingRangeClientCapabilities] = None
    """Capabilities specific to the `textDocument/linkedEditingRange` request.

    @since 3.16.0"""
    # Since: 3.16.0

    moniker: Optional[MonikerClientCapabilities] = None
    """Client capabilities specific to the `textDocument/moniker` request.

    @since 3.16.0"""
    # Since: 3.16.0

    type_hierarchy: Optional[TypeHierarchyClientCapabilities] = None
    """Capabilities specific to the various type hierarchy requests.

    @since 3.17.0"""
    # Since: 3.17.0

    inline_value: Optional[InlineValueClientCapabilities] = None
    """Capabilities specific to the `textDocument/inlineValue` request.

    @since 3.17.0"""
    # Since: 3.17.0

    inlay_hint: Optional[InlayHintClientCapabilities] = None
    """Capabilities specific to the `textDocument/inlayHint` request.

    @since 3.17.0"""
    # Since: 3.17.0

    diagnostic: Optional[DiagnosticClientCapabilities] = None
    """Capabilities specific to the diagnostic pull model.

    @since 3.17.0"""
    # Since: 3.17.0


@dataclass
class NotebookDocumentClientCapabilities(CamelSnakeMixin):
    """Capabilities specific to the notebook document support.

    @since 3.17.0"""

    # Since: 3.17.0

    synchronization: NotebookDocumentSyncClientCapabilities
    """Capabilities specific to notebook document synchronization

    @since 3.17.0"""
    # Since: 3.17.0


@dataclass
class WindowClientCapabilities(CamelSnakeMixin):
    work_done_progress: Optional[bool] = None
    """It indicates whether the client supports server initiated
    progress using the `window/workDoneProgress/create` request.

    The capability also controls Whether client supports handling
    of progress notifications. If set servers are allowed to report a
    `workDoneProgress` property in the request specific server
    capabilities.

    @since 3.15.0"""
    # Since: 3.15.0

    show_message: Optional[ShowMessageRequestClientCapabilities] = None
    """Capabilities specific to the showMessage request.

    @since 3.16.0"""
    # Since: 3.16.0

    show_document: Optional[ShowDocumentClientCapabilities] = None
    """Capabilities specific to the showDocument request.

    @since 3.16.0"""
    # Since: 3.16.0


@dataclass
class GeneralClientCapabilitiesStaleRequestSupportType(CamelSnakeMixin):
    cancel: bool
    """The client will actively cancel the request."""

    retry_on_content_modified: List[str]
    """The list of requests for which the client
    will retry the request if it receives a
    response with error code `ContentModified`"""


@dataclass
class GeneralClientCapabilities(CamelSnakeMixin):
    """General client capabilities.

    @since 3.16.0"""

    # Since: 3.16.0

    stale_request_support: Optional[GeneralClientCapabilitiesStaleRequestSupportType] = None
    """Client capability that signals how the client
    handles stale requests (e.g. a request
    for which the client will not process the response
    anymore since the information is outdated).

    @since 3.17.0"""
    # Since: 3.17.0

    regular_expressions: Optional[RegularExpressionsClientCapabilities] = None
    """Client capabilities specific to regular expressions.

    @since 3.16.0"""
    # Since: 3.16.0

    markdown: Optional[MarkdownClientCapabilities] = None
    """Client capabilities specific to the client's markdown parser.

    @since 3.16.0"""
    # Since: 3.16.0

    position_encodings: Optional[List[Union[PositionEncodingKind, str]]] = None
    """The position encodings supported by the client. Client and server
    have to agree on the same position encoding to ensure that offsets
    (e.g. character position in a line) are interpreted the same on both
    sides.

    To keep the protocol backwards compatible the following applies: if
    the value 'utf-16' is missing from the array of position encodings
    servers can assume that the client supports UTF-16. UTF-16 is
    therefore a mandatory encoding.

    If omitted it defaults to ['utf-16'].

    Implementation considerations: since the conversion from one encoding
    into another requires the content of the file / line the conversion
    is best done where the file is read which is usually on the server
    side.

    @since 3.17.0"""
    # Since: 3.17.0


@dataclass
class RelativePattern(CamelSnakeMixin):
    """A relative pattern is a helper to construct glob patterns that are matched
    relatively to a base URI. The common value for a `baseUri` is a workspace
    folder root, but it can be another absolute URI as well.

    @since 3.17.0"""

    # Since: 3.17.0

    base_uri: Union[WorkspaceFolder, URI]
    """A workspace folder or a base URI to which this pattern will be matched
    against relatively."""

    pattern: Pattern
    """The actual glob pattern;"""


@dataclass
class WorkspaceEditClientCapabilitiesChangeAnnotationSupportType(CamelSnakeMixin):
    groups_on_label: Optional[bool] = None
    """Whether the client groups edits with equal labels into tree nodes,
    for instance all edits labelled with "Changes in Strings" would
    be a tree node."""


@dataclass
class WorkspaceEditClientCapabilities(CamelSnakeMixin):
    document_changes: Optional[bool] = None
    """The client supports versioned document changes in `WorkspaceEdit`s"""

    resource_operations: Optional[List[ResourceOperationKind]] = None
    """The resource operations the client supports. Clients should at least
    support 'create', 'rename' and 'delete' files and folders.

    @since 3.13.0"""
    # Since: 3.13.0

    failure_handling: Optional[FailureHandlingKind] = None
    """The failure handling strategy of a client if applying the workspace edit
    fails.

    @since 3.13.0"""
    # Since: 3.13.0

    normalizes_line_endings: Optional[bool] = None
    """Whether the client normalizes line endings to the client specific
    setting.
    If set to `true` the client will normalize line ending characters
    in a workspace edit to the client-specified new line
    character.

    @since 3.16.0"""
    # Since: 3.16.0

    change_annotation_support: Optional[WorkspaceEditClientCapabilitiesChangeAnnotationSupportType] = None
    """Whether the client in general supports change annotations on text edits,
    create file, rename file and delete file changes.

    @since 3.16.0"""
    # Since: 3.16.0


@dataclass
class DidChangeConfigurationClientCapabilities(CamelSnakeMixin):
    dynamic_registration: Optional[bool] = None
    """Did change configuration notification supports dynamic registration."""


@dataclass
class DidChangeWatchedFilesClientCapabilities(CamelSnakeMixin):
    dynamic_registration: Optional[bool] = None
    """Did change watched files notification supports dynamic registration. Please note
    that the current protocol doesn't support static configuration for file changes
    from the server side."""

    relative_pattern_support: Optional[bool] = None
    """Whether the client has support for {@link  RelativePattern relative pattern}
    or not.

    @since 3.17.0"""
    # Since: 3.17.0


@dataclass
class WorkspaceSymbolClientCapabilitiesSymbolKindType(CamelSnakeMixin):
    value_set: Optional[List[SymbolKind]] = None
    """The symbol kind values the client supports. When this
    property exists the client also guarantees that it will
    handle values outside its set gracefully and falls back
    to a default value when unknown.

    If this property is not present the client only supports
    the symbol kinds from `File` to `Array` as defined in
    the initial version of the protocol."""


@dataclass
class WorkspaceSymbolClientCapabilitiesTagSupportType(CamelSnakeMixin):
    value_set: List[SymbolTag]
    """The tags supported by the client."""


@dataclass
class WorkspaceSymbolClientCapabilitiesResolveSupportType(CamelSnakeMixin):
    properties: List[str]
    """The properties that a client can resolve lazily. Usually
    `location.range`"""


@dataclass
class WorkspaceSymbolClientCapabilities(CamelSnakeMixin):
    """Client capabilities for a {@link WorkspaceSymbolRequest}."""

    dynamic_registration: Optional[bool] = None
    """Symbol request supports dynamic registration."""

    symbol_kind: Optional[WorkspaceSymbolClientCapabilitiesSymbolKindType] = None
    """Specific capabilities for the `SymbolKind` in the `workspace/symbol` request."""

    tag_support: Optional[WorkspaceSymbolClientCapabilitiesTagSupportType] = None
    """The client supports tags on `SymbolInformation`.
    Clients supporting tags have to handle unknown tags gracefully.

    @since 3.16.0"""
    # Since: 3.16.0

    resolve_support: Optional[WorkspaceSymbolClientCapabilitiesResolveSupportType] = None
    """The client support partial workspace symbols. The client will send the
    request `workspaceSymbol/resolve` to the server to resolve additional
    properties.

    @since 3.17.0"""
    # Since: 3.17.0


@dataclass
class ExecuteCommandClientCapabilities(CamelSnakeMixin):
    """The client capabilities of a {@link ExecuteCommandRequest}."""

    dynamic_registration: Optional[bool] = None
    """Execute command supports dynamic registration."""


@dataclass
class SemanticTokensWorkspaceClientCapabilities(CamelSnakeMixin):
    """@since 3.16.0"""

    # Since: 3.16.0

    refresh_support: Optional[bool] = None
    """Whether the client implementation supports a refresh request sent from
    the server to the client.

    Note that this event is global and will force the client to refresh all
    semantic tokens currently shown. It should be used with absolute care
    and is useful for situation where a server for example detects a project
    wide change that requires such a calculation."""


@dataclass
class CodeLensWorkspaceClientCapabilities(CamelSnakeMixin):
    """@since 3.16.0"""

    # Since: 3.16.0

    refresh_support: Optional[bool] = None
    """Whether the client implementation supports a refresh request sent from the
    server to the client.

    Note that this event is global and will force the client to refresh all
    code lenses currently shown. It should be used with absolute care and is
    useful for situation where a server for example detect a project wide
    change that requires such a calculation."""


@dataclass
class FileOperationClientCapabilities(CamelSnakeMixin):
    """Capabilities relating to events from file operations by the user in the client.

    These events do not come from the file system, they come from user operations
    like renaming a file in the UI.

    @since 3.16.0"""

    # Since: 3.16.0

    dynamic_registration: Optional[bool] = None
    """Whether the client supports dynamic registration for file requests/notifications."""

    did_create: Optional[bool] = None
    """The client has support for sending didCreateFiles notifications."""

    will_create: Optional[bool] = None
    """The client has support for sending willCreateFiles requests."""

    did_rename: Optional[bool] = None
    """The client has support for sending didRenameFiles notifications."""

    will_rename: Optional[bool] = None
    """The client has support for sending willRenameFiles requests."""

    did_delete: Optional[bool] = None
    """The client has support for sending didDeleteFiles notifications."""

    will_delete: Optional[bool] = None
    """The client has support for sending willDeleteFiles requests."""


@dataclass
class InlineValueWorkspaceClientCapabilities(CamelSnakeMixin):
    """Client workspace capabilities specific to inline values.

    @since 3.17.0"""

    # Since: 3.17.0

    refresh_support: Optional[bool] = None
    """Whether the client implementation supports a refresh request sent from the
    server to the client.

    Note that this event is global and will force the client to refresh all
    inline values currently shown. It should be used with absolute care and is
    useful for situation where a server for example detects a project wide
    change that requires such a calculation."""


@dataclass
class InlayHintWorkspaceClientCapabilities(CamelSnakeMixin):
    """Client workspace capabilities specific to inlay hints.

    @since 3.17.0"""

    # Since: 3.17.0

    refresh_support: Optional[bool] = None
    """Whether the client implementation supports a refresh request sent from
    the server to the client.

    Note that this event is global and will force the client to refresh all
    inlay hints currently shown. It should be used with absolute care and
    is useful for situation where a server for example detects a project wide
    change that requires such a calculation."""


@dataclass
class DiagnosticWorkspaceClientCapabilities(CamelSnakeMixin):
    """Workspace client capabilities specific to diagnostic pull requests.

    @since 3.17.0"""

    # Since: 3.17.0

    refresh_support: Optional[bool] = None
    """Whether the client implementation supports a refresh request sent from
    the server to the client.

    Note that this event is global and will force the client to refresh all
    pulled diagnostics currently shown. It should be used with absolute care and
    is useful for situation where a server for example detects a project wide
    change that requires such a calculation."""


@dataclass
class TextDocumentSyncClientCapabilities(CamelSnakeMixin):
    dynamic_registration: Optional[bool] = None
    """Whether text document synchronization supports dynamic registration."""

    will_save: Optional[bool] = None
    """The client supports sending will save notifications."""

    will_save_wait_until: Optional[bool] = None
    """The client supports sending a will save request and
    waits for a response providing text edits which will
    be applied to the document before it is saved."""

    did_save: Optional[bool] = None
    """The client supports did save notifications."""


@dataclass
class CompletionClientCapabilitiesCompletionItemTypeTagSupportType(CamelSnakeMixin):
    value_set: List[CompletionItemTag]
    """The tags supported by the client."""


@dataclass
class CompletionClientCapabilitiesCompletionItemTypeResolveSupportType(CamelSnakeMixin):
    properties: List[str]
    """The properties that a client can resolve lazily."""


@dataclass
class CompletionClientCapabilitiesCompletionItemTypeInsertTextModeSupportType(CamelSnakeMixin):
    value_set: List[InsertTextMode]


@dataclass
class CompletionClientCapabilitiesCompletionItemType(CamelSnakeMixin):
    snippet_support: Optional[bool] = None
    """Client supports snippets as insert text.

    A snippet can define tab stops and placeholders with `$1`, `$2`
    and `${3:foo}`. `$0` defines the final tab stop, it defaults to
    the end of the snippet. Placeholders with equal identifiers are linked,
    that is typing in one will update others too."""

    commit_characters_support: Optional[bool] = None
    """Client supports commit characters on a completion item."""

    documentation_format: Optional[List[MarkupKind]] = None
    """Client supports the following content formats for the documentation
    property. The order describes the preferred format of the client."""

    deprecated_support: Optional[bool] = None
    """Client supports the deprecated property on a completion item."""

    preselect_support: Optional[bool] = None
    """Client supports the preselect property on a completion item."""

    tag_support: Optional[CompletionClientCapabilitiesCompletionItemTypeTagSupportType] = None
    """Client supports the tag property on a completion item. Clients supporting
    tags have to handle unknown tags gracefully. Clients especially need to
    preserve unknown tags when sending a completion item back to the server in
    a resolve call.

    @since 3.15.0"""
    # Since: 3.15.0

    insert_replace_support: Optional[bool] = None
    """Client support insert replace edit to control different behavior if a
    completion item is inserted in the text or should replace text.

    @since 3.16.0"""
    # Since: 3.16.0

    resolve_support: Optional[CompletionClientCapabilitiesCompletionItemTypeResolveSupportType] = None
    """Indicates which properties a client can resolve lazily on a completion
    item. Before version 3.16.0 only the predefined properties `documentation`
    and `details` could be resolved lazily.

    @since 3.16.0"""
    # Since: 3.16.0

    insert_text_mode_support: Optional[CompletionClientCapabilitiesCompletionItemTypeInsertTextModeSupportType] = None
    """The client supports the `insertTextMode` property on
    a completion item to override the whitespace handling mode
    as defined by the client (see `insertTextMode`).

    @since 3.16.0"""
    # Since: 3.16.0

    label_details_support: Optional[bool] = None
    """The client has support for completion item label
    details (see also `CompletionItemLabelDetails`).

    @since 3.17.0"""
    # Since: 3.17.0


@dataclass
class CompletionClientCapabilitiesCompletionItemKindType(CamelSnakeMixin):
    value_set: Optional[List[CompletionItemKind]] = None
    """The completion item kind values the client supports. When this
    property exists the client also guarantees that it will
    handle values outside its set gracefully and falls back
    to a default value when unknown.

    If this property is not present the client only supports
    the completion items kinds from `Text` to `Reference` as defined in
    the initial version of the protocol."""


@dataclass
class CompletionClientCapabilitiesCompletionListType(CamelSnakeMixin):
    item_defaults: Optional[List[str]] = None
    """The client supports the following itemDefaults on
    a completion list.

    The value lists the supported property names of the
    `CompletionList.itemDefaults` object. If omitted
    no properties are supported.

    @since 3.17.0"""
    # Since: 3.17.0


@dataclass
class CompletionClientCapabilities(CamelSnakeMixin):
    """Completion client capabilities"""

    dynamic_registration: Optional[bool] = None
    """Whether completion supports dynamic registration."""

    completion_item: Optional[CompletionClientCapabilitiesCompletionItemType] = None
    """The client supports the following `CompletionItem` specific
    capabilities."""

    completion_item_kind: Optional[CompletionClientCapabilitiesCompletionItemKindType] = None

    insert_text_mode: Optional[InsertTextMode] = None
    """Defines how the client handles whitespace and indentation
    when accepting a completion item that uses multi line
    text in either `insertText` or `textEdit`.

    @since 3.17.0"""
    # Since: 3.17.0

    context_support: Optional[bool] = None
    """The client supports to send additional context information for a
    `textDocument/completion` request."""

    completion_list: Optional[CompletionClientCapabilitiesCompletionListType] = None
    """The client supports the following `CompletionList` specific
    capabilities.

    @since 3.17.0"""
    # Since: 3.17.0


@dataclass
class HoverClientCapabilities(CamelSnakeMixin):
    dynamic_registration: Optional[bool] = None
    """Whether hover supports dynamic registration."""

    content_format: Optional[List[MarkupKind]] = None
    """Client supports the following content formats for the content
    property. The order describes the preferred format of the client."""


@dataclass
class SignatureHelpClientCapabilitiesSignatureInformationTypeParameterInformationType(CamelSnakeMixin):
    label_offset_support: Optional[bool] = None
    """The client supports processing label offsets instead of a
    simple label string.

    @since 3.14.0"""
    # Since: 3.14.0


@dataclass
class SignatureHelpClientCapabilitiesSignatureInformationType(CamelSnakeMixin):
    documentation_format: Optional[List[MarkupKind]] = None
    """Client supports the following content formats for the documentation
    property. The order describes the preferred format of the client."""

    parameter_information: Optional[
        SignatureHelpClientCapabilitiesSignatureInformationTypeParameterInformationType
    ] = None
    """Client capabilities specific to parameter information."""

    active_parameter_support: Optional[bool] = None
    """The client supports the `activeParameter` property on `SignatureInformation`
    literal.

    @since 3.16.0"""
    # Since: 3.16.0


@dataclass
class SignatureHelpClientCapabilities(CamelSnakeMixin):
    """Client Capabilities for a {@link SignatureHelpRequest}."""

    dynamic_registration: Optional[bool] = None
    """Whether signature help supports dynamic registration."""

    signature_information: Optional[SignatureHelpClientCapabilitiesSignatureInformationType] = None
    """The client supports the following `SignatureInformation`
    specific properties."""

    context_support: Optional[bool] = None
    """The client supports to send additional context information for a
    `textDocument/signatureHelp` request. A client that opts into
    contextSupport will also support the `retriggerCharacters` on
    `SignatureHelpOptions`.

    @since 3.15.0"""
    # Since: 3.15.0


@dataclass
class DeclarationClientCapabilities(CamelSnakeMixin):
    """@since 3.14.0"""

    # Since: 3.14.0

    dynamic_registration: Optional[bool] = None
    """Whether declaration supports dynamic registration. If this is set to `true`
    the client supports the new `DeclarationRegistrationOptions` return value
    for the corresponding server capability as well."""

    link_support: Optional[bool] = None
    """The client supports additional metadata in the form of declaration links."""


@dataclass
class DefinitionClientCapabilities(CamelSnakeMixin):
    """Client Capabilities for a {@link DefinitionRequest}."""

    dynamic_registration: Optional[bool] = None
    """Whether definition supports dynamic registration."""

    link_support: Optional[bool] = None
    """The client supports additional metadata in the form of definition links.

    @since 3.14.0"""
    # Since: 3.14.0


@dataclass
class TypeDefinitionClientCapabilities(CamelSnakeMixin):
    """Since 3.6.0"""

    dynamic_registration: Optional[bool] = None
    """Whether implementation supports dynamic registration. If this is set to `true`
    the client supports the new `TypeDefinitionRegistrationOptions` return value
    for the corresponding server capability as well."""

    link_support: Optional[bool] = None
    """The client supports additional metadata in the form of definition links.

    Since 3.14.0"""


@dataclass
class ImplementationClientCapabilities(CamelSnakeMixin):
    """@since 3.6.0"""

    # Since: 3.6.0

    dynamic_registration: Optional[bool] = None
    """Whether implementation supports dynamic registration. If this is set to `true`
    the client supports the new `ImplementationRegistrationOptions` return value
    for the corresponding server capability as well."""

    link_support: Optional[bool] = None
    """The client supports additional metadata in the form of definition links.

    @since 3.14.0"""
    # Since: 3.14.0


@dataclass
class ReferenceClientCapabilities(CamelSnakeMixin):
    """Client Capabilities for a {@link ReferencesRequest}."""

    dynamic_registration: Optional[bool] = None
    """Whether references supports dynamic registration."""


@dataclass
class DocumentHighlightClientCapabilities(CamelSnakeMixin):
    """Client Capabilities for a {@link DocumentHighlightRequest}."""

    dynamic_registration: Optional[bool] = None
    """Whether document highlight supports dynamic registration."""


@dataclass
class DocumentSymbolClientCapabilitiesSymbolKindType(CamelSnakeMixin):
    value_set: Optional[List[SymbolKind]] = None
    """The symbol kind values the client supports. When this
    property exists the client also guarantees that it will
    handle values outside its set gracefully and falls back
    to a default value when unknown.

    If this property is not present the client only supports
    the symbol kinds from `File` to `Array` as defined in
    the initial version of the protocol."""


@dataclass
class DocumentSymbolClientCapabilitiesTagSupportType(CamelSnakeMixin):
    value_set: List[SymbolTag]
    """The tags supported by the client."""


@dataclass
class DocumentSymbolClientCapabilities(CamelSnakeMixin):
    """Client Capabilities for a {@link DocumentSymbolRequest}."""

    dynamic_registration: Optional[bool] = None
    """Whether document symbol supports dynamic registration."""

    symbol_kind: Optional[DocumentSymbolClientCapabilitiesSymbolKindType] = None
    """Specific capabilities for the `SymbolKind` in the
    `textDocument/documentSymbol` request."""

    hierarchical_document_symbol_support: Optional[bool] = None
    """The client supports hierarchical document symbols."""

    tag_support: Optional[DocumentSymbolClientCapabilitiesTagSupportType] = None
    """The client supports tags on `SymbolInformation`. Tags are supported on
    `DocumentSymbol` if `hierarchicalDocumentSymbolSupport` is set to true.
    Clients supporting tags have to handle unknown tags gracefully.

    @since 3.16.0"""
    # Since: 3.16.0

    label_support: Optional[bool] = None
    """The client supports an additional label presented in the UI when
    registering a document symbol provider.

    @since 3.16.0"""
    # Since: 3.16.0


@dataclass
class CodeActionClientCapabilitiesCodeActionLiteralSupportTypeCodeActionKindType(CamelSnakeMixin):
    value_set: List[Union[CodeActionKind, str]]
    """The code action kind values the client supports. When this
    property exists the client also guarantees that it will
    handle values outside its set gracefully and falls back
    to a default value when unknown."""


@dataclass
class CodeActionClientCapabilitiesCodeActionLiteralSupportType(CamelSnakeMixin):
    code_action_kind: CodeActionClientCapabilitiesCodeActionLiteralSupportTypeCodeActionKindType
    """The code action kind is support with the following value
    set."""


@dataclass
class CodeActionClientCapabilitiesResolveSupportType(CamelSnakeMixin):
    properties: List[str]
    """The properties that a client can resolve lazily."""


@dataclass
class CodeActionClientCapabilities(CamelSnakeMixin):
    """The Client Capabilities of a {@link CodeActionRequest}."""

    dynamic_registration: Optional[bool] = None
    """Whether code action supports dynamic registration."""

    code_action_literal_support: Optional[CodeActionClientCapabilitiesCodeActionLiteralSupportType] = None
    """The client support code action literals of type `CodeAction` as a valid
    response of the `textDocument/codeAction` request. If the property is not
    set the request can only return `Command` literals.

    @since 3.8.0"""
    # Since: 3.8.0

    is_preferred_support: Optional[bool] = None
    """Whether code action supports the `isPreferred` property.

    @since 3.15.0"""
    # Since: 3.15.0

    disabled_support: Optional[bool] = None
    """Whether code action supports the `disabled` property.

    @since 3.16.0"""
    # Since: 3.16.0

    data_support: Optional[bool] = None
    """Whether code action supports the `data` property which is
    preserved between a `textDocument/codeAction` and a
    `codeAction/resolve` request.

    @since 3.16.0"""
    # Since: 3.16.0

    resolve_support: Optional[CodeActionClientCapabilitiesResolveSupportType] = None
    """Whether the client supports resolving additional code action
    properties via a separate `codeAction/resolve` request.

    @since 3.16.0"""
    # Since: 3.16.0

    honors_change_annotations: Optional[bool] = None
    """Whether the client honors the change annotations in
    text edits and resource operations returned via the
    `CodeAction#edit` property by for example presenting
    the workspace edit in the user interface and asking
    for confirmation.

    @since 3.16.0"""
    # Since: 3.16.0


@dataclass
class CodeLensClientCapabilities(CamelSnakeMixin):
    """The client capabilities  of a {@link CodeLensRequest}."""

    dynamic_registration: Optional[bool] = None
    """Whether code lens supports dynamic registration."""


@dataclass
class DocumentLinkClientCapabilities(CamelSnakeMixin):
    """The client capabilities of a {@link DocumentLinkRequest}."""

    dynamic_registration: Optional[bool] = None
    """Whether document link supports dynamic registration."""

    tooltip_support: Optional[bool] = None
    """Whether the client supports the `tooltip` property on `DocumentLink`.

    @since 3.15.0"""
    # Since: 3.15.0


@dataclass
class DocumentColorClientCapabilities(CamelSnakeMixin):
    dynamic_registration: Optional[bool] = None
    """Whether implementation supports dynamic registration. If this is set to `true`
    the client supports the new `DocumentColorRegistrationOptions` return value
    for the corresponding server capability as well."""


@dataclass
class DocumentFormattingClientCapabilities(CamelSnakeMixin):
    """Client capabilities of a {@link DocumentFormattingRequest}."""

    dynamic_registration: Optional[bool] = None
    """Whether formatting supports dynamic registration."""


@dataclass
class DocumentRangeFormattingClientCapabilities(CamelSnakeMixin):
    """Client capabilities of a {@link DocumentRangeFormattingRequest}."""

    dynamic_registration: Optional[bool] = None
    """Whether range formatting supports dynamic registration."""


@dataclass
class DocumentOnTypeFormattingClientCapabilities(CamelSnakeMixin):
    """Client capabilities of a {@link DocumentOnTypeFormattingRequest}."""

    dynamic_registration: Optional[bool] = None
    """Whether on type formatting supports dynamic registration."""


@dataclass
class RenameClientCapabilities(CamelSnakeMixin):
    dynamic_registration: Optional[bool] = None
    """Whether rename supports dynamic registration."""

    prepare_support: Optional[bool] = None
    """Client supports testing for validity of rename operations
    before execution.

    @since 3.12.0"""
    # Since: 3.12.0

    prepare_support_default_behavior: Optional[PrepareSupportDefaultBehavior] = None
    """Client supports the default behavior result.

    The value indicates the default behavior used by the
    client.

    @since 3.16.0"""
    # Since: 3.16.0

    honors_change_annotations: Optional[bool] = None
    """Whether the client honors the change annotations in
    text edits and resource operations returned via the
    rename request's workspace edit by for example presenting
    the workspace edit in the user interface and asking
    for confirmation.

    @since 3.16.0"""
    # Since: 3.16.0


@dataclass
class FoldingRangeClientCapabilitiesFoldingRangeKindType(CamelSnakeMixin):
    value_set: Optional[List[Union[FoldingRangeKind, str]]] = None
    """The folding range kind values the client supports. When this
    property exists the client also guarantees that it will
    handle values outside its set gracefully and falls back
    to a default value when unknown."""


@dataclass
class FoldingRangeClientCapabilitiesFoldingRangeType(CamelSnakeMixin):
    collapsed_text: Optional[bool] = None
    """If set, the client signals that it supports setting collapsedText on
    folding ranges to display custom labels instead of the default text.

    @since 3.17.0"""
    # Since: 3.17.0


@dataclass
class FoldingRangeClientCapabilities(CamelSnakeMixin):
    dynamic_registration: Optional[bool] = None
    """Whether implementation supports dynamic registration for folding range
    providers. If this is set to `true` the client supports the new
    `FoldingRangeRegistrationOptions` return value for the corresponding
    server capability as well."""

    range_limit: Optional[int] = None
    """The maximum number of folding ranges that the client prefers to receive
    per document. The value serves as a hint, servers are free to follow the
    limit."""

    line_folding_only: Optional[bool] = None
    """If set, the client signals that it only supports folding complete lines.
    If set, client will ignore specified `startCharacter` and `endCharacter`
    properties in a FoldingRange."""

    folding_range_kind: Optional[FoldingRangeClientCapabilitiesFoldingRangeKindType] = None
    """Specific options for the folding range kind.

    @since 3.17.0"""
    # Since: 3.17.0

    folding_range: Optional[FoldingRangeClientCapabilitiesFoldingRangeType] = None
    """Specific options for the folding range.

    @since 3.17.0"""
    # Since: 3.17.0


@dataclass
class SelectionRangeClientCapabilities(CamelSnakeMixin):
    dynamic_registration: Optional[bool] = None
    """Whether implementation supports dynamic registration for selection range providers. If this is set to `true`
    the client supports the new `SelectionRangeRegistrationOptions` return value for the corresponding server
    capability as well."""


@dataclass
class PublishDiagnosticsClientCapabilitiesTagSupportType(CamelSnakeMixin):
    value_set: List[DiagnosticTag]
    """The tags supported by the client."""


@dataclass
class PublishDiagnosticsClientCapabilities(CamelSnakeMixin):
    """The publish diagnostic client capabilities."""

    related_information: Optional[bool] = None
    """Whether the clients accepts diagnostics with related information."""

    tag_support: Optional[PublishDiagnosticsClientCapabilitiesTagSupportType] = None
    """Client supports the tag property to provide meta data about a diagnostic.
    Clients supporting tags have to handle unknown tags gracefully.

    @since 3.15.0"""
    # Since: 3.15.0

    version_support: Optional[bool] = None
    """Whether the client interprets the version property of the
    `textDocument/publishDiagnostics` notification's parameter.

    @since 3.15.0"""
    # Since: 3.15.0

    code_description_support: Optional[bool] = None
    """Client supports a codeDescription property

    @since 3.16.0"""
    # Since: 3.16.0

    data_support: Optional[bool] = None
    """Whether code action supports the `data` property which is
    preserved between a `textDocument/publishDiagnostics` and
    `textDocument/codeAction` request.

    @since 3.16.0"""
    # Since: 3.16.0


@dataclass
class CallHierarchyClientCapabilities(CamelSnakeMixin):
    """@since 3.16.0"""

    # Since: 3.16.0

    dynamic_registration: Optional[bool] = None
    """Whether implementation supports dynamic registration. If this is set to `true`
    the client supports the new `(TextDocumentRegistrationOptions & StaticRegistrationOptions)`
    return value for the corresponding server capability as well."""


@dataclass
class SemanticTokensClientCapabilitiesRequestsTypeFullType1(CamelSnakeMixin):
    delta: Optional[bool] = None
    """The client will send the `textDocument/semanticTokens/full/delta` request if
    the server provides a corresponding handler."""


@dataclass
class SemanticTokensClientCapabilitiesRequestsType(CamelSnakeMixin):
    range: Optional[Union[bool, Any]] = None
    """The client will send the `textDocument/semanticTokens/range` request if
    the server provides a corresponding handler."""

    full: Optional[Union[bool, SemanticTokensClientCapabilitiesRequestsTypeFullType1]] = None
    """The client will send the `textDocument/semanticTokens/full` request if
    the server provides a corresponding handler."""


@dataclass
class SemanticTokensClientCapabilities(CamelSnakeMixin):
    """@since 3.16.0"""

    # Since: 3.16.0

    requests: SemanticTokensClientCapabilitiesRequestsType
    """Which requests the client supports and might send to the server
    depending on the server's capability. Please note that clients might not
    show semantic tokens or degrade some of the user experience if a range
    or full request is advertised by the client but not provided by the
    server. If for example the client capability `requests.full` and
    `request.range` are both set to true but the server only provides a
    range provider the client might not render a minimap correctly or might
    even decide to not show any semantic tokens at all."""

    token_types: List[str]
    """The token types that the client supports."""

    token_modifiers: List[str]
    """The token modifiers that the client supports."""

    formats: List[TokenFormat]
    """The token formats the clients supports."""

    dynamic_registration: Optional[bool] = None
    """Whether implementation supports dynamic registration. If this is set to `true`
    the client supports the new `(TextDocumentRegistrationOptions & StaticRegistrationOptions)`
    return value for the corresponding server capability as well."""

    overlapping_token_support: Optional[bool] = None
    """Whether the client supports tokens that can overlap each other."""

    multiline_token_support: Optional[bool] = None
    """Whether the client supports tokens that can span multiple lines."""

    server_cancel_support: Optional[bool] = None
    """Whether the client allows the server to actively cancel a
    semantic token request, e.g. supports returning
    LSPErrorCodes.ServerCancelled. If a server does the client
    needs to retrigger the request.

    @since 3.17.0"""
    # Since: 3.17.0

    augments_syntax_tokens: Optional[bool] = None
    """Whether the client uses semantic tokens to augment existing
    syntax tokens. If set to `true` client side created syntax
    tokens and semantic tokens are both used for colorization. If
    set to `false` the client only uses the returned semantic tokens
    for colorization.

    If the value is `undefined` then the client behavior is not
    specified.

    @since 3.17.0"""
    # Since: 3.17.0


@dataclass
class LinkedEditingRangeClientCapabilities(CamelSnakeMixin):
    """Client capabilities for the linked editing range request.

    @since 3.16.0"""

    # Since: 3.16.0

    dynamic_registration: Optional[bool] = None
    """Whether implementation supports dynamic registration. If this is set to `true`
    the client supports the new `(TextDocumentRegistrationOptions & StaticRegistrationOptions)`
    return value for the corresponding server capability as well."""


@dataclass
class MonikerClientCapabilities(CamelSnakeMixin):
    """Client capabilities specific to the moniker request.

    @since 3.16.0"""

    # Since: 3.16.0

    dynamic_registration: Optional[bool] = None
    """Whether moniker supports dynamic registration. If this is set to `true`
    the client supports the new `MonikerRegistrationOptions` return value
    for the corresponding server capability as well."""


@dataclass
class TypeHierarchyClientCapabilities(CamelSnakeMixin):
    """@since 3.17.0"""

    # Since: 3.17.0

    dynamic_registration: Optional[bool] = None
    """Whether implementation supports dynamic registration. If this is set to `true`
    the client supports the new `(TextDocumentRegistrationOptions & StaticRegistrationOptions)`
    return value for the corresponding server capability as well."""


@dataclass
class InlineValueClientCapabilities(CamelSnakeMixin):
    """Client capabilities specific to inline values.

    @since 3.17.0"""

    # Since: 3.17.0

    dynamic_registration: Optional[bool] = None
    """Whether implementation supports dynamic registration for inline value providers."""


@dataclass
class InlayHintClientCapabilitiesResolveSupportType(CamelSnakeMixin):
    properties: List[str]
    """The properties that a client can resolve lazily."""


@dataclass
class InlayHintClientCapabilities(CamelSnakeMixin):
    """Inlay hint client capabilities.

    @since 3.17.0"""

    # Since: 3.17.0

    dynamic_registration: Optional[bool] = None
    """Whether inlay hints support dynamic registration."""

    resolve_support: Optional[InlayHintClientCapabilitiesResolveSupportType] = None
    """Indicates which properties a client can resolve lazily on an inlay
    hint."""


@dataclass
class DiagnosticClientCapabilities(CamelSnakeMixin):
    """Client capabilities specific to diagnostic pull requests.

    @since 3.17.0"""

    # Since: 3.17.0

    dynamic_registration: Optional[bool] = None
    """Whether implementation supports dynamic registration. If this is set to `true`
    the client supports the new `(TextDocumentRegistrationOptions & StaticRegistrationOptions)`
    return value for the corresponding server capability as well."""

    related_document_support: Optional[bool] = None
    """Whether the clients supports related documents for document diagnostic pulls."""


@dataclass
class NotebookDocumentSyncClientCapabilities(CamelSnakeMixin):
    """Notebook specific client capabilities.

    @since 3.17.0"""

    # Since: 3.17.0

    dynamic_registration: Optional[bool] = None
    """Whether implementation supports dynamic registration. If this is
    set to `true` the client supports the new
    `(TextDocumentRegistrationOptions & StaticRegistrationOptions)`
    return value for the corresponding server capability as well."""

    execution_summary_support: Optional[bool] = None
    """The client supports sending execution summary data per cell."""


@dataclass
class ShowMessageRequestClientCapabilitiesMessageActionItemType(CamelSnakeMixin):
    additional_properties_support: Optional[bool] = None
    """Whether the client supports additional attributes which
    are preserved and send back to the server in the
    request's response."""


@dataclass
class ShowMessageRequestClientCapabilities(CamelSnakeMixin):
    """Show message request client capabilities"""

    message_action_item: Optional[ShowMessageRequestClientCapabilitiesMessageActionItemType] = None
    """Capabilities specific to the `MessageActionItem` type."""


@dataclass
class ShowDocumentClientCapabilities(CamelSnakeMixin):
    """Client capabilities for the showDocument request.

    @since 3.16.0"""

    # Since: 3.16.0

    support: bool
    """The client has support for the showDocument
    request."""


@dataclass
class RegularExpressionsClientCapabilities(CamelSnakeMixin):
    """Client capabilities specific to regular expressions.

    @since 3.16.0"""

    # Since: 3.16.0

    engine: str
    """The engine's name."""

    version: Optional[str] = None
    """The engine's version."""


@dataclass
class MarkdownClientCapabilities(CamelSnakeMixin):
    """Client capabilities specific to the used markdown parser.

    @since 3.16.0"""

    # Since: 3.16.0

    parser: str
    """The name of the parser."""

    version: Optional[str] = None
    """The version of the parser."""

    allowed_tags: Optional[List[str]] = None
    """A list of HTML tags that the client allows / supports in
    Markdown.

    @since 3.17.0"""
    # Since: 3.17.0


@dataclass
class TextDocumentColorPresentationOptions(CamelSnakeMixin):
    work_done_progress: Optional[bool] = None

    document_selector: Optional[DocumentSelector] = None
    """A document selector to identify the scope of the registration. If set to null
    the document selector provided on the client side will be used."""


Definition = Union[Location, List[Location]]
"""The definition of a symbol represented as one or many {@link Location locations}.
For most programming languages there is only one location at which a symbol is
defined.

Servers should prefer returning `DefinitionLink` over `Definition` if supported
by the client."""


DefinitionLink = LocationLink
"""Information about where a symbol is defined.

Provides additional metadata over normal {@link Location location} definitions, including the range of
the defining symbol"""


LSPArray = List[Any]
"""LSP arrays.
@since 3.17.0"""
# Since: 3.17.0


LSPAny = Union[Any, None]
"""The LSP any type.
Please note that strictly speaking a property with the value `undefined`
can't be converted into JSON preserving the property name. However for
convenience it is allowed and assumed that all these properties are
optional as well.
@since 3.17.0"""
# Since: 3.17.0


Declaration = Union[Location, List[Location]]
"""The declaration of a symbol representation as one or many {@link Location locations}."""


DeclarationLink = LocationLink
"""Information about where a symbol is declared.

Provides additional metadata over normal {@link Location location} declarations, including the range of
the declaring symbol.

Servers should prefer returning `DeclarationLink` over `Declaration` if supported
by the client."""


InlineValue = Union[InlineValueText, InlineValueVariableLookup, InlineValueEvaluatableExpression]
"""Inline value information can be provided by different means:
- directly as a text value (class InlineValueText).
- as a name to use for a variable lookup (class InlineValueVariableLookup)
- as an evaluatable expression (class InlineValueEvaluatableExpression)
The InlineValue types combines all inline value types into one type.

@since 3.17.0"""
# Since: 3.17.0


DocumentDiagnosticReport = Union[RelatedFullDocumentDiagnosticReport, RelatedUnchangedDocumentDiagnosticReport]
"""The result of a document diagnostic pull request. A report can
either be a full report containing all diagnostics for the
requested document or an unchanged report indicating that nothing
has changed in terms of diagnostics in comparison to the last
pull request.

@since 3.17.0"""
# Since: 3.17.0


@dataclass
class PrepareRenameResultType1(CamelSnakeMixin):
    range: Range

    placeholder: str


@dataclass
class PrepareRenameResultType2(CamelSnakeMixin):
    default_behavior: bool


PrepareRenameResult = Union[Range, PrepareRenameResultType1, PrepareRenameResultType2]


ProgressToken = Union[int, str]


ChangeAnnotationIdentifier = str
"""An identifier to refer to a change annotation stored with a workspace edit."""


WorkspaceDocumentDiagnosticReport = Union[
    WorkspaceFullDocumentDiagnosticReport, WorkspaceUnchangedDocumentDiagnosticReport
]
"""A workspace diagnostic document report.

@since 3.17.0"""
# Since: 3.17.0


@dataclass
class TextDocumentContentChangeEventType1(CamelSnakeMixin):
    range: Range
    """The range of the document that changed."""

    text: str
    """The new text for the provided range."""

    range_length: Optional[int] = None
    """The optional length of the range that got replaced.

    @deprecated use range instead."""


@dataclass
class TextDocumentContentChangeEventType2(CamelSnakeMixin):
    text: str
    """The new text of the whole document."""


TextDocumentContentChangeEvent = Union[TextDocumentContentChangeEventType1, TextDocumentContentChangeEventType2]
"""An event describing a change to a text document. If only a text is provided
it is considered to be the full content of the document."""


@dataclass
class MarkedStringType1(CamelSnakeMixin):
    language: str

    value: str


MarkedString = Union[str, MarkedStringType1]
"""MarkedString can be used to render human readable text. It is either a markdown string
or a code-block that provides a language and a code snippet. The language identifier
is semantically equal to the optional language identifier in fenced code blocks in GitHub
issues. See https://help.github.com/articles/creating-and-highlighting-code-blocks/#syntax-highlighting

The pair of a language and a value is an equivalent to markdown:
```${language}
${value}
```

Note that markdown strings will be sanitized - that means html will be escaped.
@deprecated use MarkupContent instead."""


@dataclass
class TextDocumentFilterType1(CamelSnakeMixin):
    language: str
    """A language id, like `typescript`."""

    scheme: Optional[str] = None
    """A Uri {@link Uri.scheme scheme}, like `file` or `untitled`."""

    pattern: Optional[str] = None
    """A glob pattern, like `*.{ts,js}`."""


@dataclass
class TextDocumentFilterType2(CamelSnakeMixin):
    scheme: str
    """A Uri {@link Uri.scheme scheme}, like `file` or `untitled`."""

    language: Optional[str] = None
    """A language id, like `typescript`."""

    pattern: Optional[str] = None
    """A glob pattern, like `*.{ts,js}`."""


@dataclass
class TextDocumentFilterType3(CamelSnakeMixin):
    pattern: str
    """A glob pattern, like `*.{ts,js}`."""

    language: Optional[str] = None
    """A language id, like `typescript`."""

    scheme: Optional[str] = None
    """A Uri {@link Uri.scheme scheme}, like `file` or `untitled`."""


TextDocumentFilter = Union[TextDocumentFilterType1, TextDocumentFilterType2, TextDocumentFilterType3]
"""A document filter denotes a document by different properties like
the {@link TextDocument.languageId language}, the {@link Uri.scheme scheme} of
its resource, or a glob-pattern that is applied to the {@link TextDocument.fileName path}.

Glob patterns can have the following syntax:
- `*` to match one or more characters in a path segment
- `?` to match on one character in a path segment
- `**` to match any number of path segments, including none
- `{}` to group sub patterns into an OR expression. (e.g. `**/*.{ts,js}` matches all TypeScript and JavaScript files)
- `[]` to declare a range of characters to match in a path segment (e.g., `example.[0-9]` to match on `example.0`, `example.1`, …)
- `[!...]` to negate a range of characters to match in a path segment (e.g., `example.[!0-9]` to match on `example.a`, `example.b`, but not `example.0`)

@sample A language filter that applies to typescript files on disk: `{ language: 'typescript', scheme: 'file' }`
@sample A language filter that applies to all package.json paths: `{ language: 'json', pattern: '**package.json' }`

@since 3.17.0"""
# Since: 3.17.0


@dataclass
class NotebookDocumentFilterType1(CamelSnakeMixin):
    notebook_type: str
    """The type of the enclosing notebook."""

    scheme: Optional[str] = None
    """A Uri {@link Uri.scheme scheme}, like `file` or `untitled`."""

    pattern: Optional[str] = None
    """A glob pattern."""


@dataclass
class NotebookDocumentFilterType2(CamelSnakeMixin):
    scheme: str
    """A Uri {@link Uri.scheme scheme}, like `file` or `untitled`."""

    notebook_type: Optional[str] = None
    """The type of the enclosing notebook."""

    pattern: Optional[str] = None
    """A glob pattern."""


@dataclass
class NotebookDocumentFilterType3(CamelSnakeMixin):
    pattern: str
    """A glob pattern."""

    notebook_type: Optional[str] = None
    """The type of the enclosing notebook."""

    scheme: Optional[str] = None
    """A Uri {@link Uri.scheme scheme}, like `file` or `untitled`."""


NotebookDocumentFilter = Union[
    NotebookDocumentFilterType1,
    NotebookDocumentFilterType2,
    NotebookDocumentFilterType3,
]
"""A notebook document filter denotes a notebook document by
different properties. The properties will be match
against the notebook's URI (same as with documents)

@since 3.17.0"""
# Since: 3.17.0


Pattern = str
"""The glob pattern to watch relative to the base path. Glob patterns can have the following syntax:
- `*` to match one or more characters in a path segment
- `?` to match on one character in a path segment
- `**` to match any number of path segments, including none
- `{}` to group conditions (e.g. `**/*.{ts,js}` matches all TypeScript and JavaScript files)
- `[]` to declare a range of characters to match in a path segment (e.g., `example.[0-9]` to match on `example.0`, `example.1`, …)
- `[!...]` to negate a range of characters to match in a path segment (e.g., `example.[!0-9]` to match on `example.a`, `example.b`, but not `example.0`)

@since 3.17.0"""
# Since: 3.17.0

DocumentFilter = Union[TextDocumentFilter, NotebookCellTextDocumentFilter]
"""A document filter describes a top level text document or
a notebook cell document.

@since 3.17.0 - proposed support for NotebookCellTextDocumentFilter."""
# Since: 3.17.0 - proposed support for NotebookCellTextDocumentFilter.


GlobPattern = Union[Pattern, RelativePattern]
"""The glob pattern. Either a string pattern or a relative pattern.

@since 3.17.0"""
# Since: 3.17.0

DocumentSelector = List[DocumentFilter]
"""A document selector is the combination of one or many document filters.

@sample `let sel:DocumentSelector = [{ language: 'typescript' }, { language: 'json', pattern: '**/tsconfig.json' }]`;

The use of a string as a document filter is deprecated @since 3.16.0."""
# Since: 3.16.0.
