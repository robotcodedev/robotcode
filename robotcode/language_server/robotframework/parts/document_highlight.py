from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional

from ....utils.logging import LoggingDescriptor
from ...common.decorators import language_id
from ...common.lsp_types import DocumentHighlight, DocumentHighlightKind, Position
from ...common.text_document import TextDocument

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .model_helper import ModelHelperMixin
from .protocol_part import RobotLanguageServerProtocolPart


class RobotDocumentHighlightProtocolPart(RobotLanguageServerProtocolPart, ModelHelperMixin):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.document_highlight.collect.add(self.collect)

    @language_id("robotframework")
    @_logger.call
    async def collect(
        self,
        sender: Any,
        document: TextDocument,
        position: Position,
    ) -> Optional[List[DocumentHighlight]]:
        namespace = await self.parent.documents_cache.get_namespace(document)
        if namespace is None:
            return None

        all_variable_refs = await namespace.get_variable_references()
        if all_variable_refs:
            for var, var_refs in all_variable_refs.items():
                for r in var_refs:
                    if (var.source == namespace.source and position in var.name_range) or position in r.range:
                        return [
                            *(
                                [DocumentHighlight(var.name_range, DocumentHighlightKind.TEXT)]
                                if var.source == namespace.source
                                else []
                            ),
                            *(DocumentHighlight(e.range, DocumentHighlightKind.TEXT) for e in var_refs),
                        ]

        all_kw_refs = await namespace.get_keyword_references()
        if all_kw_refs:
            for kw, kw_refs in all_kw_refs.items():
                for r in kw_refs:
                    if (kw.source == namespace.source and position in kw.range) or position in r.range:
                        return [
                            *(
                                [DocumentHighlight(kw.range, DocumentHighlightKind.TEXT)]
                                if kw.source == namespace.source
                                else []
                            ),
                            *(DocumentHighlight(e.range, DocumentHighlightKind.TEXT) for e in kw_refs),
                        ]

        return None
