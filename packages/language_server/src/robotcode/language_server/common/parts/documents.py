from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Final,
    List,
    Optional,
)

from robotcode.core.documents_manager import DocumentsManager
from robotcode.core.language import language_id_filter
from robotcode.core.lsp.types import (
    DidChangeTextDocumentParams,
    DidCloseTextDocumentParams,
    DidOpenTextDocumentParams,
    DidSaveTextDocumentParams,
    DocumentUri,
    FileChangeType,
    FileEvent,
    TextDocumentContentChangeEvent,
    TextDocumentContentChangeEventType1,
    TextDocumentContentChangeEventType2,
    TextDocumentIdentifier,
    TextDocumentItem,
    TextDocumentSaveReason,
    TextDocumentSyncKind,
    TextDocumentSyncOptions,
    TextEdit,
    VersionedTextDocumentIdentifier,
    WatchKind,
    WillSaveTextDocumentParams,
)
from robotcode.core.uri import Uri
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import JsonRPCException, rpc_method

from .protocol_part import LanguageServerProtocolPart

if TYPE_CHECKING:
    from robotcode.language_server.common.protocol import LanguageServerProtocol


__all__ = ["TextDocumentProtocolPart", "LanguageServerDocumentError"]


class LanguageServerDocumentError(JsonRPCException):
    pass


class CantReadDocumentError(Exception):
    pass


class TextDocumentProtocolPart(LanguageServerProtocolPart, DocumentsManager):
    __logger: Final = LoggingDescriptor()

    def __init__(self, parent: "LanguageServerProtocol") -> None:
        super().__init__(parent)
        DocumentsManager.__init__(self, parent.languages)

        self.parent.on_initialized.add(self._protocol_initialized)

    def _protocol_initialized(self, sender: Any) -> None:
        self._update_filewatchers()

    def _update_filewatchers(self) -> None:
        if self.parent.file_extensions:
            self.parent.workspace.add_file_watcher(
                self._file_watcher,
                f"**/*.{{{','.join(self.parent.file_extensions)}}}",
                WatchKind.CREATE | WatchKind.CHANGE | WatchKind.DELETE,
            )

    def _file_watcher(self, sender: Any, changes: List[FileEvent]) -> None:
        to_change: Dict[str, FileEvent] = {}
        for change in changes:
            to_change[change.uri] = change

        for change in to_change.values():
            if change.type == FileChangeType.CREATED:
                self.did_create_uri(self, change.uri)

            document = self._documents.get(DocumentUri(Uri(change.uri).normalized()), None)
            if document is not None and change.type == FileChangeType.CREATED:
                self.did_create(self, document, callback_filter=language_id_filter(document))

            elif document is not None and not document.opened_in_editor:
                if change.type == FileChangeType.DELETED:
                    self.close_document(document, True)

                elif change.type == FileChangeType.CHANGED:
                    document.apply_full_change(
                        None,
                        self.read_document_text(document.uri, language_id_filter(document)),
                        save=True,
                    )
                    self.did_change(
                        self,
                        document,
                        callback_filter=language_id_filter(document),
                    )

    @rpc_method(name="textDocument/didOpen", param_type=DidOpenTextDocumentParams)
    @__logger.call
    def _text_document_did_open(self, text_document: TextDocumentItem, *args: Any, **kwargs: Any) -> None:
        with self._lock:
            uri = str(Uri(text_document.uri).normalized())
            document = self._documents.get(uri, None)

            normalized_text = self._normalize_line_endings(text_document.text)

            if document is None:
                text_changed = False
                document = self._create_document(
                    text_document.uri,
                    normalized_text,
                    (
                        text_document.language_id
                        if text_document.language_id
                        else self.detect_language_id(text_document.uri)
                    ),
                    text_document.version,
                )

                self._documents[uri] = document
            else:
                text_changed = document.text() != normalized_text
                if text_changed:
                    document.apply_full_change(text_document.version, normalized_text)
                else:
                    document.version = text_document.version

            document.opened_in_editor = True

            self.did_open(self, document, callback_filter=language_id_filter(document))

        if text_changed:
            self.did_change(self, document, callback_filter=language_id_filter(document))

    @rpc_method(name="textDocument/didClose", param_type=DidCloseTextDocumentParams)
    @__logger.call
    def _text_document_did_close(self, text_document: TextDocumentIdentifier, *args: Any, **kwargs: Any) -> None:
        uri = str(Uri(text_document.uri).normalized())
        document = self.get(uri)

        if document is not None:
            document.opened_in_editor = False

            self.close_document(document)

    @rpc_method(name="textDocument/willSave", param_type=WillSaveTextDocumentParams)
    @__logger.call
    def _text_document_will_save(
        self,
        text_document: TextDocumentIdentifier,
        reason: TextDocumentSaveReason,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        # TODO: implement
        pass

    @rpc_method(name="textDocument/didSave", param_type=DidSaveTextDocumentParams)
    @__logger.call
    def _text_document_did_save(
        self,
        text_document: TextDocumentIdentifier,
        text: Optional[str] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        document = self.get(str(Uri(text_document.uri).normalized()))
        self._logger.warning(
            lambda: f"Document {text_document.uri} is not opened.",
            condition=lambda: document is None,
        )

        if document is not None:
            if text is not None:
                normalized_text = self._normalize_line_endings(text)

                text_changed = document.text() != normalized_text
                if text_changed:
                    document.save(None, text)
                    self.did_change(
                        self,
                        document,
                        callback_filter=language_id_filter(document),
                    )

            self.did_save(self, document, callback_filter=language_id_filter(document))

    @rpc_method(
        name="textDocument/willSaveWaitUntil",
        param_type=WillSaveTextDocumentParams,
    )
    @__logger.call
    def _text_document_will_save_wait_until(
        self,
        text_document: TextDocumentIdentifier,
        reason: TextDocumentSaveReason,
        *args: Any,
        **kwargs: Any,
    ) -> List[TextEdit]:
        return []

    @rpc_method(name="textDocument/didChange", param_type=DidChangeTextDocumentParams)
    @__logger.call
    def _text_document_did_change(
        self,
        text_document: VersionedTextDocumentIdentifier,
        content_changes: List[TextDocumentContentChangeEvent],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        document = self.get(str(Uri(text_document.uri).normalized()))
        if document is None:
            raise LanguageServerDocumentError(f"Document {text_document.uri} is not opened.")

        sync_kind = (
            self.parent.capabilities.text_document_sync
            if isinstance(
                self.parent.capabilities.text_document_sync,
                TextDocumentSyncKind,
            )
            else (
                self.parent.capabilities.text_document_sync.change
                if isinstance(
                    self.parent.capabilities.text_document_sync,
                    TextDocumentSyncOptions,
                )
                else None
            )
        )
        for content_change in content_changes:
            if sync_kind is None or sync_kind == TextDocumentSyncKind.NONE_:
                document.apply_none_change()
            elif sync_kind == TextDocumentSyncKind.FULL and isinstance(
                content_change, TextDocumentContentChangeEventType2
            ):
                document.apply_full_change(
                    text_document.version,
                    self._normalize_line_endings(content_change.text),
                )
            elif sync_kind == TextDocumentSyncKind.INCREMENTAL and isinstance(
                content_change, TextDocumentContentChangeEventType1
            ):
                document.apply_incremental_change(
                    text_document.version,
                    content_change.range,
                    self._normalize_line_endings(content_change.text),
                )
            else:
                raise LanguageServerDocumentError(
                    f"Invalid type for content_changes {type(content_change)} "
                    f"and server capability {self.parent.capabilities.text_document_sync} "
                    f"for document {text_document.uri}."
                )

        self.did_change(self, document, callback_filter=language_id_filter(document))
