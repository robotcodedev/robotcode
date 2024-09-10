from typing import TYPE_CHECKING, Any, List, Optional, cast

from robotcode.core.concurrent import check_current_task_canceled
from robotcode.core.language import language_id
from robotcode.core.lsp.types import (
    DocumentHighlight,
    DocumentHighlightKind,
    Position,
    Range,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from .protocol_part import RobotLanguageServerProtocolPart


class RobotDocumentHighlightProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

        parent.document_highlight.collect.add(self.collect)

    @language_id("robotframework")
    @_logger.call
    def collect(self, sender: Any, document: TextDocument, position: Position) -> Optional[List[DocumentHighlight]]:
        namespace = self.parent.documents_cache.get_namespace(document)

        all_variable_refs = namespace.get_variable_references()
        if all_variable_refs:
            for var, var_refs in all_variable_refs.items():
                check_current_task_canceled()

                if var_refs:
                    for r in var_refs:
                        if (var.source == namespace.source and position in var.name_range) or position in r.range:
                            return [
                                *(
                                    [
                                        DocumentHighlight(
                                            var.name_range,
                                            DocumentHighlightKind.WRITE,
                                        )
                                    ]
                                    if var.source == namespace.source
                                    else []
                                ),
                                *(DocumentHighlight(e.range, DocumentHighlightKind.READ) for e in var_refs),
                            ]
                else:
                    if var.source == namespace.source and position in var.name_range:
                        return [
                            *(
                                [
                                    DocumentHighlight(
                                        var.name_range,
                                        DocumentHighlightKind.WRITE,
                                    )
                                ]
                                if var.source == namespace.source
                                else []
                            )
                        ]

        all_kw_refs = namespace.get_keyword_references()
        if all_kw_refs:
            for kw, kw_refs in all_kw_refs.items():
                check_current_task_canceled()

                if kw_refs:
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
                else:
                    if kw.source == namespace.source and position in kw.range:
                        return [
                            *(
                                [DocumentHighlight(kw.range, DocumentHighlightKind.TEXT)]
                                if kw.source == namespace.source
                                else []
                            )
                        ]

        all_namespace_refs = namespace.get_namespace_references()
        if all_namespace_refs:
            for ns, ns_refs in all_namespace_refs.items():
                check_current_task_canceled()
                found_range = (
                    ns.import_range
                    if ns.import_source == namespace.source
                    and (position.is_in_range(ns.alias_range, False) or position.is_in_range(ns.import_range, False))
                    else cast(
                        Optional[Range],
                        next(
                            (r.range for r in ns_refs if position.is_in_range(r.range, False)),
                            None,
                        ),
                    )
                )

                if found_range is not None:
                    return [
                        *(
                            [DocumentHighlight(ns.import_range, DocumentHighlightKind.TEXT)]
                            if ns.import_source == namespace.source and ns.import_range
                            else []
                        ),
                        *(
                            [DocumentHighlight(ns.alias_range, DocumentHighlightKind.TEXT)]
                            if ns.import_source == namespace.source and ns.alias_range
                            else []
                        ),
                        *(DocumentHighlight(e.range, DocumentHighlightKind.TEXT) for e in ns_refs),
                    ]

        return [DocumentHighlight(Range(position, position), DocumentHighlightKind.TEXT)]
