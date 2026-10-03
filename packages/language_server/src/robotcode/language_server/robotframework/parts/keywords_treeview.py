from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, List, Mapping, Optional, Tuple

from robotcode.core.lsp.types import TextDocumentIdentifier
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.core.utils.dataclasses import CamelSnakeMixin
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import rpc_method
from robotcode.robot.diagnostics.entities import LibraryEntry
from robotcode.robot.diagnostics.library_doc import KeywordDoc, LibraryDoc
from robotcode.robot.diagnostics.namespace import Namespace
from robotcode.robot.utils.markdown_docs import LinkResolver, ReferenceTarget

from .code_action_documentation import DocumentationTarget, keyword_reference_targets, link_documentation
from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


@dataclass(repr=False)
class GetDocumentImportsParams(CamelSnakeMixin):
    text_document: TextDocumentIdentifier
    no_documentation: Optional[bool] = None


@dataclass(repr=False)
class GetDocumentKeywordsParams(CamelSnakeMixin):
    text_document: TextDocumentIdentifier
    no_documentation: Optional[bool] = None


@dataclass(repr=False)
class GetLibraryDocumentationParams(CamelSnakeMixin):
    workspace_folder_uri: str
    library_name: str


@dataclass(repr=False)
class GetKeywordDocumentationParams(CamelSnakeMixin):
    workspace_folder_uri: str
    library_name: str
    keyword_name: str


@dataclass(repr=False)
class Keyword(CamelSnakeMixin):
    name: str
    id: Optional[str]
    signature: Optional[str] = None
    documentation: Optional[str] = None


@dataclass(repr=False)
class LibraryDocumentation(CamelSnakeMixin):
    name: str
    documentation: Optional[str] = None
    keywords: Optional[List[Keyword]] = None
    initializers: Optional[List[Keyword]] = None


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


class RobotKeywordsTreeViewPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

    @rpc_method(name="robot/keywordsview/getDocumentImports", param_type=GetDocumentImportsParams, threaded=True)
    @_logger.call
    def _get_document_imports(
        self,
        text_document: TextDocumentIdentifier,
        no_documentation: Optional[bool] = None,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[List[DocumentImport]]:
        document = self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        namespace = self.parent.documents_cache.get_namespace(document)

        result = []

        for _k, v in namespace.libraries.items():
            documentation, keywords = (
                self._import_documentation(v, True, document, namespace) if not no_documentation else (None, None)
            )
            result.append(
                DocumentImport(
                    name=v.name,
                    alias=v.alias,
                    id=str(hash(v)),
                    type="library",
                    documentation=documentation,
                    keywords=keywords,
                )
            )
        for _k, v in namespace.resources.items():
            documentation, keywords = (
                self._import_documentation(v, False, document, namespace) if not no_documentation else (None, None)
            )
            result.append(
                DocumentImport(
                    name=v.name,
                    alias=None,
                    id=str(hash(v)),
                    type="resource",
                    documentation=documentation,
                    keywords=keywords,
                )
            )

        return result

    @property
    def _links(self) -> bool:
        return self.parent.robot_initialization_options.documentation_viewer_links

    def _import_documentation(
        self, entry: LibraryEntry, is_library: bool, document: TextDocument, namespace: Namespace
    ) -> Tuple[str, List[Keyword]]:
        """The tooltips of an import and of its keywords."""
        library_doc = entry.library_doc
        target = (
            self.parent.robot_code_action_documentation.entry_target(entry, is_library, document, namespace)
            if self._links
            else None
        )
        link_resolver = self._link_resolver(document, namespace, target, library_doc)
        return (
            self._documentation(
                lambda link_resolver: library_doc.to_markdown(add_signature=False, link_resolver=link_resolver),
                target,
                link_resolver,
            ),
            self._keywords(list(library_doc.keywords.values()), target, link_resolver),
        )

    def _link_resolver(
        self,
        document: TextDocument,
        namespace: Namespace,
        target: Optional[DocumentationTarget],
        library_doc: LibraryDoc,
    ) -> Optional[LinkResolver]:
        # one for the tooltips of an import and all of its keywords
        if target is None:
            return None
        return self.parent.robot_code_action_documentation.link_resolver(document, namespace, target, library_doc)

    def _keywords(
        self,
        keywords: List[KeywordDoc],
        target: Optional[DocumentationTarget],
        link_resolver: Optional[LinkResolver],
    ) -> List[Keyword]:
        """The keywords of a library, a resource file or the document with their tooltips."""
        # once for all keywords, they share their library and its documentation format
        targets = keyword_reference_targets(keywords[0], self._links) if keywords else None
        return [self._keyword(kw, target, link_resolver, targets) for kw in keywords]

    def _keyword(
        self,
        kw: KeywordDoc,
        target: Optional[DocumentationTarget],
        link_resolver: Optional[LinkResolver],
        targets: Optional[Mapping[str, ReferenceTarget]],
    ) -> Keyword:
        return Keyword(
            kw.name,
            str(hash(kw)),
            kw.parameter_signature(),
            self._documentation(
                lambda link_resolver: kw.to_markdown(
                    add_signature=False, link_resolver=link_resolver, reference_targets=targets
                ),
                target,
                link_resolver,
                heading=False,
            ),
        )

    def _documentation(
        self,
        render: Callable[[Optional[LinkResolver]], str],
        target: Optional[DocumentationTarget],
        link_resolver: Optional[LinkResolver],
        *,
        heading: bool = True,
    ) -> str:
        """A tooltip; with links, linked into the Documentation Viewer at the page of `target`."""
        if not self._links:
            return render(None)
        return link_documentation(render, target, None, heading=heading, link_resolver=link_resolver)

    @rpc_method(name="robot/keywordsview/getDocumentKeywords", param_type=GetDocumentKeywordsParams, threaded=True)
    @_logger.call
    def _get_document_keywords(
        self,
        text_document: TextDocumentIdentifier,
        no_documentation: Optional[bool] = None,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[List[Keyword]]:
        document = self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        namespace = self.parent.documents_cache.get_namespace(document)

        keywords = list(namespace.library_doc.keywords.values())
        if no_documentation:
            return [Keyword(l.name, str(hash(l)), l.parameter_signature(), None) for l in keywords]

        target = (
            self.parent.robot_code_action_documentation.document_target(document, namespace) if self._links else None
        )
        return self._keywords(keywords, target, self._link_resolver(document, namespace, target, namespace.library_doc))

    def _documentation_target(
        self,
        text_document: TextDocumentIdentifier,
        import_id: Optional[str],
        keyword_id: Optional[str],
    ) -> Optional[DocumentationTarget]:
        document = self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        namespace = self.parent.documents_cache.get_namespace(document)
        documentation = self.parent.robot_code_action_documentation

        keyword_name = None

        if import_id is None:
            if keyword_id is not None:
                keyword = next((l for l in namespace.library_doc.keywords.values() if str(hash(l)) == keyword_id), None)
                if keyword is not None:
                    keyword_name = keyword.name

            return documentation.document_target(document, namespace, keyword_name)

        is_library = True
        entry = next((l for l in namespace.libraries.values() if str(hash(l)) == import_id), None)
        if entry is None:
            is_library = False
            entry = next((l for l in namespace.resources.values() if str(hash(l)) == import_id), None)

        if entry is None:
            return None

        if keyword_id:
            keyword = next((l for l in entry.library_doc.keywords.values() if str(hash(l)) == keyword_id), None)
            if keyword is not None:
                keyword_name = keyword.name

        return documentation.entry_target(entry, is_library, document, namespace, keyword_name)

    @rpc_method(name="robot/keywordsview/getDocumentationTarget", param_type=GetDocumentationUrl, threaded=True)
    @_logger.call
    def _get_documentation_target(
        self,
        text_document: TextDocumentIdentifier,
        import_id: Optional[str] = None,
        keyword_id: Optional[str] = None,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[DocumentationTarget]:
        return self._documentation_target(text_document, import_id, keyword_id)

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
        target = self._documentation_target(text_document, import_id, keyword_id)
        if target is None:
            return None

        document = self.parent.documents.get(text_document.uri)
        if document is None:
            return None

        return self.parent.robot_code_action_documentation.build_url(target, document)

    @rpc_method(
        name="robot/keywordsview/getLibraryDocumentation", param_type=GetLibraryDocumentationParams, threaded=True
    )
    @_logger.call
    def _get_library_documentation(
        self,
        workspace_folder_uri: str,
        library_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[LibraryDocumentation]:
        imports_manager = self.parent.documents_cache.get_imports_manager_for_uri(Uri(workspace_folder_uri))

        libdoc = imports_manager.get_libdoc_for_library_import(library_name, (), ".")
        if libdoc.errors:
            raise ValueError(f"Errors while loading library documentation: {libdoc.errors}")

        return LibraryDocumentation(
            name=libdoc.name,
            documentation=libdoc.to_markdown(),
            keywords=[
                Keyword(
                    l.name,
                    str(hash(l)),
                    l.parameter_signature(),
                    l.to_markdown(),
                )
                for l in libdoc.keywords.values()
            ],
            initializers=[
                Keyword(
                    s.name,
                    str(hash(s)),
                    s.parameter_signature(),
                    s.to_markdown(),
                )
                for s in libdoc.inits.values()
            ],
        )

    @rpc_method(
        name="robot/keywordsview/getKeywordDocumentation", param_type=GetKeywordDocumentationParams, threaded=True
    )
    @_logger.call
    def _get_keyword_documentation(
        self,
        workspace_folder_uri: str,
        library_name: str,
        keyword_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> Optional[Keyword]:
        imports_manager = self.parent.documents_cache.get_imports_manager_for_uri(Uri(workspace_folder_uri))

        libdoc = imports_manager.get_libdoc_for_library_import(library_name, (), ".")
        if libdoc.errors:
            raise ValueError(f"Errors while loading library documentation: {libdoc.errors}")

        kw = libdoc.keywords.get(keyword_name, None)
        if kw is None:
            raise ValueError(f"Keyword '{keyword_name}' not found in library '{library_name}'.")

        return Keyword(
            name=kw.name,
            id=str(hash(kw)),
            signature=kw.parameter_signature(),
            documentation=kw.to_markdown(),
        )
