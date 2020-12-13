from typing import Dict, Optional, TypedDict

from .language_server_base import LanguageServerBase


class TextDocumentItem(TypedDict):
    uri: str
    languageId: str     # noqa: N815
    version: int
    text: str


__all__ = ["TextDocument", "TextDocumentHandler"]


class TextDocument:
    def __init__(self, uri: str, language_id: str, version: int, text: str) -> None:
        self.uri = uri
        self.language_id = language_id
        self.version = version
        self.text = text


class TextDocumentHandler(LanguageServerBase):

    _documents: Optional[Dict[str, TextDocument]] = None

    @property
    def documents(self) -> Dict[str, TextDocument]:
        if self._documents is None:
            self._documents = {}

        return self._documents

    @LanguageServerBase._debug_call
    def serve_textDocument_didOpen(self, textDocument: TextDocumentItem, *args, **kwargs):  # noqa: N802, N803
        self.documents[textDocument["uri"]] = TextDocument(
            textDocument["uri"], textDocument["languageId"], textDocument["version"], textDocument["text"])
