from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional, cast

from robotcode.core.logging import LoggingDescriptor
from robotcode.core.lsp.types import DocumentHighlight, DocumentHighlightKind, Position, Range
from robotcode.language_server.common.decorators import language_id
from robotcode.language_server.common.text_document import TextDocument

if TYPE_CHECKING:
    from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol

from .protocol_part import RobotLanguageServerProtocolPart


class RobotDocumentHighlightProtocolPart(RobotLanguageServerProtocolPart):
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

        all_namespace_refs = await namespace.get_namespace_references()
        if all_namespace_refs:
            for ns, ns_refs in all_namespace_refs.items():
                found_range = (
                    ns.import_range
                    if ns.import_source == namespace.source
                    and (position.is_in_range(ns.alias_range, False) or position.is_in_range(ns.import_range, False))
                    else cast(
                        Optional[Range], next((r.range for r in ns_refs if position.is_in_range(r.range, False)), None)
                    )
                )

                if found_range is not None:
                    return [
                        *(
                            [
                                DocumentHighlight(
                                    ns.import_range,
                                    DocumentHighlightKind.TEXT,
                                )
                            ]
                            if ns.import_source == namespace.source and ns.import_range
                            else []
                        ),
                        *(
                            [
                                DocumentHighlight(
                                    ns.alias_range,
                                    DocumentHighlightKind.TEXT,
                                )
                            ]
                            if ns.import_source == namespace.source and ns.alias_range
                            else []
                        ),
                        *(DocumentHighlight(e.range, DocumentHighlightKind.TEXT) for e in ns_refs),
                    ]
        return None
