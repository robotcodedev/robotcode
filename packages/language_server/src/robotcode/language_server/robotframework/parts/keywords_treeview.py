from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, List, Optional

from robotcode.core.lsp.types import TextDocumentIdentifier
from robotcode.core.utils.dataclasses import CamelSnakeMixin
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import rpc_method
from robotcode.robot.diagnostics.model_helper import ModelHelper

from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


@dataclass(repr=False)
class GetDocumentImportsParams(CamelSnakeMixin):
    text_document: TextDocumentIdentifier


@dataclass(repr=False)
class Keyword(CamelSnakeMixin):
    name: str
    id: Optional[str]
    signature: Optional[str] = None
    documentation: Optional[str] = None


@dataclass(repr=False)
class DocumentImport(CamelSnakeMixin):
    name: str
    alias: Optional[str]
    id: Optional[str]
    type: Optional[str]
    documentation: Optional[str] = None
    keywords: Optional[List[Keyword]] = None


@dataclass(repr=False)
class GetDocumentationUrl(CamelSnakeMixin):
    text_document: TextDocumentIdentifier
    import_id: Optional[str] = None
    keyword_id: Optional[str] = None


class RobotKeywordsTreeViewPart(RobotLanguageServerProtocolPart, ModelHelper):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

    @rpc_method(name="robot/keywordsview/getDocumentImports", param_type=GetDocumentImportsParams, threaded=True)
    @_logger.call
    def _get_document_imports(
        self,
        text_document: TextDocumentIdentifier,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[List[DocumentImport]]:
        document = self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        namespace = self.parent.documents_cache.get_namespace(document)

        result = []

        for _k, v in namespace.get_libraries().items():
            result.append(
                DocumentImport(
                    name=v.name,
                    alias=v.alias,
                    id=str(hash(v)),
                    type="library",
                    documentation=v.library_doc.to_markdown(add_signature=False),
                    keywords=[
                        Keyword(
                            l.name,
                            str(hash(l)),
                            l.parameter_signature(),
                            l.to_markdown(add_signature=False),
                        )
                        for l in v.library_doc.keywords.values()
                    ],
                )
            )
        for _k, v in namespace.get_resources().items():
            result.append(
                DocumentImport(
                    name=v.name,
                    alias=None,
                    id=str(hash(v)),
                    type="resource",
                    documentation=v.library_doc.to_markdown(add_signature=False),
                    keywords=[
                        Keyword(l.name, str(hash(l)), l.parameter_signature(), l.to_markdown(add_signature=False))
                        for l in v.library_doc.keywords.values()
                    ],
                )
            )

        return result

    @rpc_method(name="robot/keywordsview/getDocumentKeywords", param_type=GetDocumentImportsParams, threaded=True)
    @_logger.call
    def _get_document_keywords(
        self,
        text_document: TextDocumentIdentifier,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[List[Keyword]]:
        document = self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        namespace = self.parent.documents_cache.get_namespace(document)

        return [
            Keyword(l.name, str(hash(l)), l.parameter_signature(), l.to_markdown(add_signature=False))
            for l in namespace.get_library_doc().keywords.values()
        ]

    @rpc_method(name="robot/keywordsview/getDocumentationUrl", param_type=GetDocumentationUrl, threaded=True)
    @_logger.call
    def _get_documentation_url(
        self,
        text_document: TextDocumentIdentifier,
        import_id: Optional[str] = None,
        keyword_id: Optional[str] = None,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[str]:
        document = self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        namespace = self.parent.documents_cache.get_namespace(document)

        keyword_name = None

        if import_id is None:
            if keyword_id is not None:
                keyword = next(
                    (l for l in namespace.get_library_doc().keywords.values() if str(hash(l)) == keyword_id), None
                )
                if keyword is not None:
                    keyword_name = keyword.name

            return self.parent.robot_code_action_documentation.build_url(
                str(document.uri.to_path().name), (), document, namespace, keyword_name
            )

        entry = next((l for l in namespace.get_libraries().values() if str(hash(l)) == import_id), None)
        if entry is None:
            entry = next((l for l in namespace.get_resources().values() if str(hash(l)) == import_id), None)

        if keyword_id and entry is not None:
            keyword = next((l for l in entry.library_doc.keywords.values() if str(hash(l)) == keyword_id), None)
            if keyword is not None:
                keyword_name = keyword.name

        if entry is not None:
            return self.parent.robot_code_action_documentation.build_url(
                entry.import_name, entry.args, document, namespace, keyword_name
            )

        return None
