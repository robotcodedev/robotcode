from typing import TYPE_CHECKING, Any, List, Optional, Union

from robotcode.core.lsp.types import (
    Location,
    SymbolInformation,
    SymbolKind,
    SymbolTag,
    WorkspaceSymbol,
)
from robotcode.core.utils.logging import LoggingDescriptor

from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


def contains_characters_in_order(main_string: str, check_string: str) -> bool:
    main_iter = iter(main_string.lower())
    return all(char in main_iter for char in check_string.lower())


class RobotWorkspaceSymbolsProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

        parent.workspace_symbols.collect.add(self.collect)

    @_logger.call
    def collect(self, sender: Any, query: str) -> Optional[Union[List[WorkspaceSymbol], List[SymbolInformation], None]]:
        result: List[WorkspaceSymbol] = []
        for document in self.parent.documents.documents:
            if document.language_id == "robotframework":
                namespace = self.parent.documents_cache.get_only_initialized_namespace(document)
                if namespace is not None:
                    container_name = namespace.get_library_doc().name

                    for kw_doc in [
                        v
                        for v in namespace.get_keyword_references().keys()
                        if v.source == namespace.source and contains_characters_in_order(v.name, query)
                    ]:
                        result.append(
                            WorkspaceSymbol(
                                name=kw_doc.name,
                                kind=SymbolKind.FUNCTION,
                                location=Location(
                                    uri=document.document_uri,
                                    range=kw_doc.range,
                                ),
                                tags=[SymbolTag.DEPRECATED] if kw_doc.is_deprecated else None,
                                container_name=container_name,
                            )
                        )
                    for var in [
                        v
                        for v in namespace.get_variable_references().keys()
                        if v.source == namespace.source and contains_characters_in_order(v.name, query)
                    ]:
                        result.append(
                            WorkspaceSymbol(
                                name=var.name,
                                kind=SymbolKind.VARIABLE,
                                location=Location(
                                    uri=document.document_uri,
                                    range=var.range,
                                ),
                                container_name=container_name,
                            )
                        )

                    for test in [
                        v for v in namespace.get_testcase_definitions() if contains_characters_in_order(v.name, query)
                    ]:
                        result.append(
                            WorkspaceSymbol(
                                name=test.name,
                                kind=SymbolKind.CLASS,
                                location=Location(
                                    uri=document.document_uri,
                                    range=test.range,
                                ),
                                container_name=container_name,
                            )
                        )
        return result
