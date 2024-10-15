from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional, Union, cast

from robotcode.core.concurrent import check_current_task_canceled
from robotcode.core.language import language_id
from robotcode.core.lsp.types import Location, LocationLink, Position, Range
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.robot.utils.ast import range_from_token

from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


class RobotGotoProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.definition.collect.add(self.collect_definition)
        parent.implementation.collect.add(self.collect_implementation)

    @language_id("robotframework")
    @_logger.call
    def collect_definition(
        self, sender: Any, document: TextDocument, position: Position
    ) -> Union[Location, List[Location], List[LocationLink], None]:
        return self.collect(document, position)

    @language_id("robotframework")
    @_logger.call
    def collect_implementation(
        self, sender: Any, document: TextDocument, position: Position
    ) -> Union[Location, List[Location], List[LocationLink], None]:
        return self.collect(document, position)

    def collect(
        self, document: TextDocument, position: Position
    ) -> Union[Location, List[Location], List[LocationLink], None]:
        namespace = self.parent.documents_cache.get_namespace(document)

        all_variable_refs = namespace.get_variable_references()

        if all_variable_refs:
            result = []

            for variable, var_refs in all_variable_refs.items():
                check_current_task_canceled()

                found_range = (
                    variable.name_range
                    if variable.source == namespace.source and position.is_in_range(variable.name_range, False)
                    else cast(
                        Optional[Range],
                        next(
                            (r.range for r in var_refs if position.is_in_range(r.range)),
                            None,
                        ),
                    )
                )

                if found_range is not None and variable.source:
                    if variable.source:
                        result.append(
                            LocationLink(
                                origin_selection_range=found_range,
                                target_uri=str(Uri.from_path(variable.source)),
                                target_range=variable.range,
                                target_selection_range=(
                                    range_from_token(variable.name_token) if variable.name_token else variable.range
                                ),
                            )
                        )

            if result:
                return result

        all_kw_refs = namespace.get_keyword_references()
        if all_kw_refs:
            result = []

            for kw, kw_refs in all_kw_refs.items():
                check_current_task_canceled()

                found_range = (
                    kw.name_range
                    if kw.source == namespace.source and position.is_in_range(kw.name_range, False)
                    else cast(
                        Optional[Range],
                        next(
                            (r.range for r in kw_refs if position.is_in_range(r.range, False)),
                            None,
                        ),
                    )
                )

                if found_range is not None and kw.source:
                    result.append(
                        LocationLink(
                            origin_selection_range=found_range,
                            target_uri=str(Uri.from_path(kw.source)),
                            target_range=kw.range,
                            target_selection_range=range_from_token(kw.name_token) if kw.name_token else kw.range,
                        )
                    )

            if result:
                return result

        all_namespace_refs = namespace.get_namespace_references()
        if all_namespace_refs:
            check_current_task_canceled()

            result = []

            for ns, ns_refs in all_namespace_refs.items():
                for found_range in [
                    next(
                        (r.range for r in ns_refs if position.is_in_range(r.range, False)),
                        None,
                    ),
                    ns.alias_range if position.is_in_range(ns.alias_range, False) else None,
                    ns.import_range if position.is_in_range(ns.import_range, False) else None,
                ]:
                    if found_range is not None:
                        libdoc = ns.library_doc

                        if found_range == ns.import_range and str(document.uri.to_path()) == ns.import_source:
                            if libdoc.source:
                                result.append(
                                    LocationLink(
                                        origin_selection_range=found_range,
                                        target_uri=str(Uri.from_path(libdoc.source)),
                                        target_range=ns.library_doc.range,
                                        target_selection_range=ns.library_doc.range,
                                    )
                                )
                                return result
                        else:
                            if ns.import_source:
                                result.append(
                                    LocationLink(
                                        origin_selection_range=found_range,
                                        target_uri=str(Uri.from_path(ns.import_source)),
                                        target_range=ns.alias_range if ns.alias_range else ns.import_range,
                                        target_selection_range=ns.alias_range if ns.alias_range else ns.import_range,
                                    )
                                )
                            elif libdoc is not None and libdoc.source:
                                result.append(
                                    LocationLink(
                                        origin_selection_range=found_range,
                                        target_uri=str(Uri.from_path(libdoc.source)),
                                        target_range=ns.library_doc.range,
                                        target_selection_range=ns.library_doc.range,
                                    )
                                )

            if result:
                return result

        return None
