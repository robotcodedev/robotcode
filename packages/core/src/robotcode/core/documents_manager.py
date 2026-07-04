import os
import re
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Final,
    Iterator,
    List,
    Optional,
    Tuple,
    Union,
)

from .concurrent import RLock
from .event import event
from .language import LanguageDefinition, language_id_filter
from .lsp.types import DocumentUri
from .text_document import TextDocument
from .uri import InvalidUriError, Uri
from .utils.logging import LoggingDescriptor
from .utils.path import DiskInfo, disk_info_from_stat

_STAT_VERIFY_MAX_RETRIES: Final = 3


class CantReadDocumentError(Exception):
    pass


class DocumentsManager:
    _logger: Final = LoggingDescriptor()

    def __init__(self, languages: List[LanguageDefinition] = []) -> None:
        self.languages = languages

        self._documents: Dict[DocumentUri, TextDocument] = {}
        self._lock = RLock(name="DocumentsManager.lock", default_timeout=120)

    @property
    def documents(self) -> Iterator[TextDocument]:
        return iter(self._documents.values())

    __NORMALIZE_LINE_ENDINGS: Final = re.compile(r"(\r?\n)")

    @classmethod
    def _normalize_line_endings(cls, text: str) -> str:
        return cls.__NORMALIZE_LINE_ENDINGS.sub("\n", text)

    def read_document_text(self, uri: Uri, language_id: Union[str, Callable[[Any], bool], None]) -> str:
        for e in self.on_read_document_text(
            self,
            uri,
            callback_filter=language_id_filter(language_id) if isinstance(language_id, str) else language_id,
        ):
            if isinstance(e, BaseException):
                raise RuntimeError(f"Can't read document text from {uri}: {e}") from e

            if e is not None:
                return self._normalize_line_endings(e)

        raise FileNotFoundError(str(uri))

    def read_document_text_with_disk_info(
        self, uri: Uri, language_id: Union[str, Callable[[Any], bool], None]
    ) -> Tuple[str, Optional[DiskInfo]]:
        """Read document text and capture a stat snapshot bound to that exact content.

        Uses a stat → read → stat-verify protocol: when the file changes while it
        is being read, the read is retried. Returns ``None`` as info when no
        consistent snapshot could be captured (non-file URI, stat error, or the
        file never settled) — such text must not be persisted to or validated
        against a disk cache.
        """
        try:
            path = uri.to_path()
            st_before = os.stat(path)
        except (InvalidUriError, OSError):
            return self.read_document_text(uri, language_id), None

        text = self.read_document_text(uri, language_id)

        for _ in range(_STAT_VERIFY_MAX_RETRIES):
            try:
                st_after = os.stat(path)
            except OSError:
                return text, None

            if (st_before.st_mtime_ns, st_before.st_size) == (st_after.st_mtime_ns, st_after.st_size):
                return text, disk_info_from_stat(st_after)

            st_before = st_after
            text = self.read_document_text(uri, language_id)

        return text, None

    def detect_language_id(self, path_or_uri: Union[str, "os.PathLike[Any]", Uri]) -> str:
        path = path_or_uri.to_path() if isinstance(path_or_uri, Uri) else Path(path_or_uri)

        for lang in self.languages:
            suffix = path.suffix
            if lang.extensions_ignore_case:
                suffix = suffix.lower()
            if suffix in lang.extensions:
                return lang.id

        return "unknown"

    @_logger.call
    def get_or_open_document(
        self,
        path: Union[str, "os.PathLike[Any]"],
        language_id: Optional[str] = None,
        version: Optional[int] = None,
    ) -> TextDocument:
        uri = Uri.from_path(path).normalized()

        result = self.get(uri)
        if result is not None:
            return result

        try:
            text, disk_info = self.read_document_text_with_disk_info(uri, language_id)
            return self._append_document(
                document_uri=DocumentUri(uri),
                language_id=language_id or self.detect_language_id(path),
                text=text,
                version=version,
                disk_info=disk_info,
            )
        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException as e:
            raise CantReadDocumentError(f"Error reading document '{path}': {e!s}") from e

    @event
    def on_read_document_text(sender, uri: Uri) -> Optional[str]: ...

    @event
    def did_create_uri(sender, uri: DocumentUri) -> None: ...

    @event
    def did_create(sender, document: TextDocument) -> None: ...

    @event
    def did_open(sender, document: TextDocument) -> None: ...

    @event
    def did_close(sender, document: TextDocument, full_close: bool) -> None: ...

    @event
    def did_change(sender, document: TextDocument) -> None: ...

    @event
    def did_save(sender, document: TextDocument) -> None: ...

    def get(self, _uri: Union[DocumentUri, Uri]) -> Optional[TextDocument]:
        with self._lock:
            return self._documents.get(
                str(Uri(_uri).normalized() if not isinstance(_uri, Uri) else _uri),
                None,
            )

    def __len__(self) -> int:
        return self._documents.__len__()

    def __iter__(self) -> Iterator[DocumentUri]:
        return self._documents.__iter__()

    @event
    def on_document_cache_invalidate(sender, document: TextDocument) -> None: ...

    def _on_document_cache_invalidate(self, sender: TextDocument) -> None:
        self.on_document_cache_invalidate(self, sender)

    @event
    def on_document_cache_invalidated(sender, document: TextDocument) -> None: ...

    def _on_document_cache_invalidated(self, sender: TextDocument) -> None:
        self.on_document_cache_invalidated(self, sender)

    def _create_document(
        self,
        document_uri: DocumentUri,
        text: str,
        language_id: Optional[str] = None,
        version: Optional[int] = None,
        disk_info: Optional[DiskInfo] = None,
    ) -> TextDocument:
        result = TextDocument(
            document_uri=document_uri,
            language_id=language_id,
            text=text,
            version=version,
            disk_info=disk_info,
        )

        result.cache_invalidate.add(self._on_document_cache_invalidate)
        result.cache_invalidated.add(self._on_document_cache_invalidated)

        return result

    def _append_document(
        self,
        document_uri: DocumentUri,
        language_id: str,
        text: str,
        version: Optional[int] = None,
        disk_info: Optional[DiskInfo] = None,
    ) -> TextDocument:
        with self._lock:
            document = self._create_document(
                document_uri=document_uri,
                language_id=language_id,
                text=text,
                version=version,
                disk_info=disk_info,
            )

            self._documents[document_uri] = document

            return document

    @_logger.call
    def close_document(self, document: TextDocument, real_close: bool = False) -> None:
        document._version = None

        if real_close:
            with self._lock:
                self._documents.pop(str(document.uri), None)

            document.clear()
        else:
            if document.revert(None):
                self.did_change(self, document, callback_filter=language_id_filter(document))

        self.did_close(self, document, real_close, callback_filter=language_id_filter(document))
