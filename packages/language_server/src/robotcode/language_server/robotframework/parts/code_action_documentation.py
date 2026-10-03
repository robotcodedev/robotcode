import re
import urllib.parse
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Iterable, List, Mapping, Optional, Set, Tuple, Union, cast

from robot.parsing.lexer.tokens import Token
from robot.parsing.model.blocks import File, TestCaseSection
from robot.utils.escaping import unescape

from robotcode.core.language import language_id
from robotcode.core.lsp.types import (
    CodeAction,
    CodeActionContext,
    CodeActionKind,
    Command,
    Position,
    Range,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.core.utils.dataclasses import CamelSnakeMixin, as_json
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import rpc_method
from robotcode.robot.diagnostics.entities import LibraryEntry
from robotcode.robot.diagnostics.library_doc import (
    KeywordDoc,
    LibraryDoc,
    is_library_by_path,
    resolve_robot_variables,
)
from robotcode.robot.diagnostics.model_helper import ModelHelper
from robotcode.robot.diagnostics.namespace import DocumentType, Namespace
from robotcode.robot.diagnostics.semantic_analyzer.enums import ImportType, NodeKind, TokenKind
from robotcode.robot.diagnostics.semantic_analyzer.model import SemanticModel
from robotcode.robot.diagnostics.semantic_analyzer.nodes import (
    DefinitionStatement,
    ImportStatement,
    KeywordCallStatement,
)
from robotcode.robot.utils.ast import get_node_at_position, range_from_token
from robotcode.robot.utils.markdown_docs import (
    REFERENCE_KEYWORD,
    REFERENCE_SECTION,
    REFERENCE_TYPE,
    LinkResolver,
    ReferenceTarget,
    normalize_reference,
    replace_anchor_links,
    slugify,
)
from robotcode.robot.utils.match import eq_namespace
from robotcode.robot.utils.variables import contains_variable

from ...common.decorators import code_action_kinds
from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


@dataclass(repr=False)
class ConvertUriParams(CamelSnakeMixin):
    uri: str


@dataclass(repr=False)
class DocumentationTarget(CamelSnakeMixin):
    """What the documentation actions document, as `robotcode doc lib` takes it.

    `name` and `args` are resolved against `base_dir`. `base_dir` is left out
    when the name does not depend on it: a library name that is not a path, or
    an absolute path. Instead of a `keyword`, the page can be shown at a
    heading, by the `anchor` the page's own links use, or at a data type, by
    the name of its documentation (`data_type`).
    """

    uri: str
    name: str
    args: List[str] = field(default_factory=list)
    base_dir: Optional[str] = None
    keyword: Optional[str] = None
    anchor: Optional[str] = None
    data_type: Optional[str] = None


DOCUMENTATION_VIEWER_LINK_TITLE = "Show in Documentation Viewer"

# VS Code cuts every Markdown text it shows here, in hovers, completion details,
# signature help and tooltips, and a cut breaks the last links
DOCUMENTATION_LINKS_SIZE_LIMIT = 100_000

_RE_LINKED_HEADING = re.compile(r"^(#{1,6}) ((?:Keyword|Library|Resource) \*.*\*)[ \t]*$")
_RE_LINK_TEXT_SPECIAL = re.compile(r"([\\\[\]])")


def documentation_viewer_uri(target: DocumentationTarget) -> Optional[str]:
    """The command URI that shows `target` in the Documentation Viewer, `None`
    if the target cannot be encoded.

    VS Code decodes the query of a command link twice, once when it parses the
    URI and once more before it parses the arguments, so it is encoded twice.
    """
    try:
        query = urllib.parse.quote(urllib.parse.quote(as_json([target], compact=True), safe=""), safe="")
    except UnicodeEncodeError:
        # a lone surrogate, as a file name that is not UTF-8 can give one
        return None
    return f"command:robotcode.showInDocumentationViewer?{query}"


def documentation_viewer_link(target: DocumentationTarget) -> Optional[str]:
    """The destination and title of a Markdown link that shows `target` in the Documentation Viewer."""
    uri = documentation_viewer_uri(target)
    return None if uri is None else f'{uri} "{DOCUMENTATION_VIEWER_LINK_TITLE}"'


def documentation_link_resolver(
    target: DocumentationTarget, library_doc: LibraryDoc, *, introduction: bool = True
) -> LinkResolver:
    """A `LinkResolver` for the documentation of `library_doc` shown for `target`.

    Keywords of the page, data types of the library and sections the page has
    link to that place in the Documentation Viewer; a private keyword or a
    section the page does not have stays inline code. Without `introduction`,
    the page has no introduction, as the page of a suite file.
    """
    keywords: Optional[Set[str]] = None
    types: Optional[Set[str]] = None
    sections: Optional[Set[str]] = None

    def resolve(kind: str, name: str) -> Optional[str]:
        nonlocal keywords, types, sections
        if kind == REFERENCE_KEYWORD:
            if keywords is None:
                keywords = {kw.name for kw in library_doc.get_page_keywords()}
            if name not in keywords:
                return None
            return documentation_viewer_link(replace(target, keyword=name, anchor=None, data_type=None))
        if kind == REFERENCE_TYPE:
            if types is None:
                types = {t.name for t in library_doc.types}
            if name not in types:
                return None
            return documentation_viewer_link(replace(target, keyword=None, anchor=None, data_type=name))
        if kind == REFERENCE_SECTION:
            if sections is None:
                sections = _page_sections(library_doc, introduction)
            if normalize_reference(name) not in sections:
                return None
            # a title without letters or digits has no anchor, the page is shown from its start
            anchor = slugify(name) or None
            return documentation_viewer_link(replace(target, keyword=None, anchor=anchor, data_type=None))
        return None

    return resolve


def _page_sections(library_doc: LibraryDoc, introduction: bool) -> Set[str]:
    """The sections that have a heading on the page of `library_doc`, by normalized name."""
    sections: Set[str] = set()
    if introduction and library_doc.doc:
        sections.add("introduction")
        sections.update(normalize_reference(title) for title in library_doc.get_introduction_headings())
    if any(v.arguments for v in library_doc.inits.values()):
        sections.add("importing")
    if library_doc.get_page_keywords():
        sections.add("keywords")
    return sections


def link_heading(markdown: str, target: DocumentationTarget) -> str:
    """Make the first line of `markdown` a link that shows `target` in the
    Documentation Viewer, if it is the heading of a keyword, a library or a
    resource file."""
    first, newline, rest = markdown.partition("\n")
    match = _RE_LINKED_HEADING.match(first)
    if match is None:
        return markdown
    link = documentation_viewer_link(target)
    if link is None:
        return markdown
    text = _RE_LINK_TEXT_SPECIAL.sub(r"\\\1", match.group(2))
    return f"{match.group(1)} [{text}]({link}){newline}{rest}"


def link_documentation(
    render: Callable[[Optional[LinkResolver]], str],
    target: Optional[DocumentationTarget],
    library_doc: Optional[LibraryDoc],
    *,
    heading: bool = True,
    link_resolver: Optional[LinkResolver] = None,
) -> str:
    """Documentation that `render` writes, with links into the Documentation Viewer.

    With a target, the names that `link_resolver` resolves, by default the
    `documentation_link_resolver` of `library_doc`, the links to a place in the
    documentation itself and, with `heading`, the heading link to the viewer.
    Documentation that would get longer than VS Code shows keeps only the
    heading link. Without a target, links to a place in the documentation
    itself become text.
    """
    if target is None:
        return replace_anchor_links(render(None), _no_link)

    def anchor_link(anchor: str) -> Optional[str]:
        # `#` alone shows the page from its start
        return documentation_viewer_uri(replace(target, keyword=None, anchor=anchor or None, data_type=None))

    resolver = link_resolver
    if resolver is None and library_doc is not None:
        resolver = documentation_link_resolver(target, library_doc)
    text = replace_anchor_links(render(resolver), anchor_link, DOCUMENTATION_VIEWER_LINK_TITLE)
    if heading:
        text = link_heading(text, target)
    # VS Code counts the limit in UTF-16 code units
    if len(text.encode("utf-16-le", "surrogatepass")) > 2 * DOCUMENTATION_LINKS_SIZE_LIMIT:
        text = replace_anchor_links(render(None), _no_link)
        if heading:
            text = link_heading(text, target)
    return text


def _no_link(anchor: str) -> Optional[str]:
    return None


def keyword_reference_targets(kw_doc: KeywordDoc, links: bool) -> Optional[Mapping[str, ReferenceTarget]]:
    """What references in the documentation of `kw_doc` can point to, to compute once for all of its parts.

    Without links only documentation in Markdown has references; with links,
    the names in documentation in Robot Framework's format link as well.
    """
    if links and kw_doc.parent is not None:
        return kw_doc.parent.get_reference_targets()
    return kw_doc.get_reference_targets()


class RobotCodeActionDocumentationProtocolPart(RobotLanguageServerProtocolPart, ModelHelper):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)
        self.parent.commands.register_all(self)

        parent.code_action.collect.add(self.collect)

    @language_id("robotframework")
    @code_action_kinds([CodeActionKind.SOURCE])
    @_logger.call
    def collect(
        self,
        sender: Any,
        document: TextDocument,
        range: Range,
        context: CodeActionContext,
    ) -> Optional[List[Union[Command, CodeAction]]]:
        if not context.only or CodeActionKind.SOURCE.value not in context.only:
            return None

        target = self.target_at(document, range)
        if target is None:
            return None

        return self.documentation_actions(target, document)

    def target_at(self, document: TextDocument, range: Range) -> Optional[DocumentationTarget]:
        """What the documentation actions document at `range`, or `None` where they are not offered."""
        namespace = self.parent.documents_cache.get_namespace(document)

        # Tier 2 model-based path — used when the experimental SemanticAnalyzer
        # is enabled. Reads everything off the SemanticModel: statement kind
        # via `model.statement_at()`, the pre-resolved `keyword_doc`, the
        # `import_name`, and SemanticTokens for cursor-position checks. No
        # `find_keyword`, no AST walk.
        semantic_model = namespace.semantic_model
        if semantic_model is not None:
            return self._target_at_from_model(document, range, namespace, semantic_model)

        return self._target_at_legacy(document, range, namespace)

    def _target_at_legacy(
        self,
        document: TextDocument,
        range: Range,
        namespace: Namespace,
    ) -> Optional[DocumentationTarget]:
        from robot.parsing.lexer import Token as RobotToken
        from robot.parsing.model.statements import (
            Fixture,
            KeywordCall,
            KeywordName,
            LibraryImport,
            ResourceImport,
            Template,
            TestTemplate,
        )

        model = self.parent.documents_cache.get_model(document)
        node = get_node_at_position(model, range.start)

        if isinstance(node, (LibraryImport, ResourceImport)):
            if range in range_from_token(node.get_token(RobotToken.NAME)):
                if isinstance(node, LibraryImport):
                    return self.import_target(
                        node.name,
                        node.args,
                        True,
                        document,
                        namespace,
                        namespace.get_imported_library_libdoc(node.name, node.args, node.alias),
                    )
                return self.import_target(node.name, (), False, document, namespace)

        if isinstance(node, (KeywordCall, Fixture, TestTemplate, Template)):
            result = self.get_keyworddoc_and_token_from_position(
                (
                    node.value
                    if isinstance(node, (TestTemplate, Template))
                    else node.keyword
                    if isinstance(node, KeywordCall)
                    else node.name
                ),
                cast(
                    Token,
                    node.get_token(RobotToken.KEYWORD if isinstance(node, KeywordCall) else RobotToken.NAME),
                ),
                [cast(Token, t) for t in node.get_tokens(RobotToken.ARGUMENT)],
                namespace,
                range.start,
            )

            if range.start != range.end:
                return None

            if result is not None:
                kw_doc, kw_token = result

                if kw_doc is not None:
                    prefix_entry, _ = self.get_namespace_info_from_keyword_token(namespace, kw_token)
                    return self.keyword_target(kw_doc, prefix_entry, document, namespace)

        if isinstance(node, KeywordName):
            name_token = node.get_token(RobotToken.KEYWORD_NAME)
            if name_token is not None and range in range_from_token(name_token):
                return self.document_target(document, namespace, name_token.value)

        return None

    # ------------------------------------------------------------------
    # Tier 2 model-based collection
    # ------------------------------------------------------------------

    def _target_at_from_model(
        self,
        document: TextDocument,
        range: Range,
        namespace: Namespace,
        model: SemanticModel,
    ) -> Optional[DocumentationTarget]:
        """Mirror legacy three-branch logic (import / keyword-call / keyword-def)
        purely off the SemanticModel — no AST walks, no `find_keyword`.

        Position checks use SemanticTokens; URL inputs read from pre-resolved
        statement fields (`import_name`, `keyword_doc`, `name`).
        """
        # SemanticModel uses 1-indexed lines; LSP positions are 0-indexed.
        stmt = model.statement_at(range.start.line + 1)
        if stmt is None:
            return None

        # Branch 1: Library / Resource import.
        if isinstance(stmt, ImportStatement) and stmt.import_type in (ImportType.LIBRARY, ImportType.RESOURCE):
            return self._import_target_from_model(stmt, document, range, namespace)

        # Branch 2: keyword call / fixture / template.
        if isinstance(stmt, KeywordCallStatement):
            if range.start != range.end:
                return None
            kw_doc = stmt.keyword_doc
            if kw_doc is None:
                return None
            if not self._cursor_on_keyword_reference(range.start, stmt):
                return None
            return self.keyword_target(kw_doc, stmt.lib_entry, document, namespace)

        # Branch 3: keyword definition header.
        if isinstance(stmt, DefinitionStatement) and stmt.kind is NodeKind.KEYWORD_DEF:
            name_tok = next((t for t in stmt.tokens if t.kind is TokenKind.KEYWORD_NAME), None)
            if name_tok is None or range not in name_tok.range:
                return None
            return self.document_target(document, namespace, name_tok.value)

        return None

    def _import_target_from_model(
        self,
        stmt: ImportStatement,
        document: TextDocument,
        range: Range,
        namespace: Namespace,
    ) -> Optional[DocumentationTarget]:
        """Library / Resource import branch built off SemanticTokens.

        - The import path lives in the IMPORT_NAME token (cursor-position check).
        - Library `args` are the ARGUMENT tokens BEFORE the optional WITH NAME
          marker (CONTROL_FLOW); anything after is the alias and must be
          excluded — matches RF's `LibraryImport.args` semantics.
        - Resource imports never carry args (RF API returns ()).
        """
        name_tok = next((t for t in stmt.tokens if t.kind is TokenKind.IMPORT_NAME), None)
        if name_tok is None or range not in name_tok.range:
            return None

        if stmt.import_type is ImportType.LIBRARY:
            arg_values: List[str] = []
            seen_import_name = False
            for tok in stmt.tokens:
                if tok.kind is TokenKind.IMPORT_NAME:
                    seen_import_name = True
                elif seen_import_name and tok.kind is TokenKind.SETTING_IMPORT:
                    break  # WITH NAME / AS — everything after is the alias
                elif tok.kind is TokenKind.ARGUMENT:
                    arg_values.append(tok.value)
            args: Tuple[str, ...] = tuple(arg_values)
        else:
            args = ()

        return self.import_target(
            stmt.import_name or "",
            args,
            stmt.import_type is ImportType.LIBRARY,
            document,
            namespace,
            stmt.lib_entry.library_doc if stmt.lib_entry is not None else None,
        )

    @staticmethod
    def _cursor_on_keyword_reference(pos: Position, stmt: KeywordCallStatement) -> bool:
        """Cursor is within the NAMESPACE / "." / KEYWORD SemanticTokens
        that make up the keyword reference (BDD prefix excluded). Mirrors
        the legacy `position.is_in_range(range_from_token(keyword_token))`
        after the BDD-prefix strip that
        `get_keyworddoc_and_token_from_position` does.
        """
        ref_toks = [t for t in stmt.tokens if t.kind in (TokenKind.NAMESPACE, TokenKind.KEYWORD)]
        if not ref_toks:
            return False
        # Contiguous span from namespace start to keyword end also covers the
        # "." operator between them.
        return pos in Range(start=ref_toks[0].range.start, end=ref_toks[-1].range.end)

    def keyword_target(
        self,
        kw_doc: KeywordDoc,
        prefix_entry: Optional[LibraryEntry],
        document: TextDocument,
        namespace: Namespace,
    ) -> Optional[DocumentationTarget]:
        """Target of a keyword reference: the import that owns `kw_doc`.
        Shared between legacy and model paths so both resolve the same import.

        For a call with a library or resource prefix, that is the prefix's
        import: `LibraryDoc ==` ignores the import arguments, so a second import
        of the same library would otherwise be documented with the first
        import's arguments. A library keyword called without a prefix belongs
        to the import the analysis resolved it to, see `_library_entry`."""
        if prefix_entry is not None and prefix_entry.library_doc == kw_doc.parent:
            return self.entry_target(prefix_entry, kw_doc.libtype == "LIBRARY", document, namespace, kw_doc.name)

        if kw_doc.libtype == "LIBRARY":
            entry = self._library_entry(kw_doc, namespace)
            if entry is not None:
                return self.entry_target(entry, True, document, namespace, kw_doc.name)

        elif kw_doc.libtype == "RESOURCE":
            entry = next(
                (v for v in namespace.resources.values() if v.library_doc == kw_doc.parent),
                None,
            )
            if entry is not None:
                return self.entry_target(entry, False, document, namespace, kw_doc.name)

            if namespace.library_doc == kw_doc.parent:
                return self.document_target(document, namespace, kw_doc.name)

        return None

    @staticmethod
    def _library_entry(kw_doc: KeywordDoc, namespace: Namespace) -> Optional[LibraryEntry]:
        """The import of a library keyword called without a prefix.

        Imports of the same library with other arguments compare equal. In a
        live analysis each import has its own `LibraryDoc`, so the keyword's
        parent is the one the keyword finder chose. After a cache restore that
        identity is lost; then the import is chosen as the keyword finder
        chooses between imports: among those that have the keyword, the first
        that the library search order names."""
        candidates = [v for v in namespace.libraries.values() if v.library_doc == kw_doc.parent]
        if len(candidates) < 2:
            return next(iter(candidates), None)

        entry = next((v for v in candidates if v.library_doc is kw_doc.parent), None)
        if entry is not None:
            return entry

        having = [v for v in candidates if kw_doc.name in v.library_doc.keywords] or candidates
        for name in namespace.imports_manager.global_library_search_order:
            entry = next((v for v in having if eq_namespace(name, v.alias or v.name)), None)
            if entry is not None:
                return entry
        return having[0]

    def link_resolver(
        self,
        document: TextDocument,
        namespace: Namespace,
        target: DocumentationTarget,
        library_doc: LibraryDoc,
    ) -> LinkResolver:
        """The `documentation_link_resolver` for documentation of `library_doc` shown in `document`.

        `robotcode doc lib` documents a suite file without its documentation,
        so the keywords of a suite file link no sections of its introduction.
        """
        introduction = not (library_doc == namespace.library_doc and self._is_suite(document))
        return documentation_link_resolver(target, library_doc, introduction=introduction)

    def _is_suite(self, document: TextDocument) -> bool:
        """Whether `robotcode doc lib` documents `document` as a suite: an initialization file or a file with tests."""
        if self.parent.documents_cache.get_document_type(document) == DocumentType.INIT:
            return True
        model = self.parent.documents_cache.get_model(document)
        return any(isinstance(section, TestCaseSection) for section in cast(File, model).sections)

    def entry_target(
        self,
        entry: LibraryEntry,
        is_library: bool,
        document: TextDocument,
        namespace: Namespace,
        keyword: Optional[str] = None,
    ) -> DocumentationTarget:
        """Target of an import, resolved in the directory of the file that contains it."""
        return self._target(
            entry.import_name,
            self._page_args(entry.args, entry.library_doc),
            is_library,
            document,
            namespace,
            Path(entry.import_source).parent if entry.import_source else None,
            keyword,
        )

    def import_target(
        self,
        name: str,
        args: Iterable[Any],
        is_library: bool,
        document: TextDocument,
        namespace: Namespace,
        library_doc: Optional[LibraryDoc] = None,
    ) -> DocumentationTarget:
        """Target of an import of the current document, `library_doc` is what the import loaded."""
        return self._target(name, self._page_args(args, library_doc), is_library, document, namespace, None, None)

    @staticmethod
    def _page_args(args: Iterable[Any], library_doc: Optional[LibraryDoc]) -> Iterable[Any]:
        """The arguments of the page of an import. RobotCode loads a library whose arguments
        fail without them, and so does its page: `robotcode doc lib` refuses those arguments."""
        return () if library_doc is not None and library_doc.loaded_without_arguments else args

    def document_target(
        self,
        document: TextDocument,
        namespace: Namespace,
        keyword: Optional[str] = None,
    ) -> DocumentationTarget:
        """Target of the current document itself, for its own keywords."""
        return self._target(document.uri.to_path().name, (), False, document, namespace, None, keyword)

    def _target(
        self,
        name: str,
        args: Iterable[Any],
        is_library: bool,
        document: TextDocument,
        namespace: Namespace,
        base_dir: Optional[Path],
        keyword: Optional[str],
    ) -> DocumentationTarget:
        directory = base_dir if base_dir is not None else document.uri.to_path().parent
        str_args = [str(v) for v in args]

        if contains_variable(name, "$@&%") or any(contains_variable(v, "$@&%") for v in str_args):
            robot_variables = resolve_robot_variables(
                str(namespace.imports_manager.root_folder),
                str(directory),
                namespace.imports_manager.get_resolvable_command_line_variables(),
                variables=namespace.get_resolvable_variables(),
            )
            try:
                name = robot_variables.replace_string(name, ignore_errors=False)

                str_args = [robot_variables.replace_string(v, ignore_errors=False) for v in str_args]

            except (SystemExit, KeyboardInterrupt):
                raise
            except BaseException:
                pass
        else:
            # what `replace_string` returns for a string without variables,
            # without the cost of resolving all variables of the namespace
            name = unescape(name)
            str_args = [unescape(v) for v in str_args]

        depends_on_base_dir = (not is_library or is_library_by_path(name)) and not Path(name).is_absolute()

        return DocumentationTarget(
            uri=str(document.uri),
            name=name,
            args=str_args,
            base_dir=str(directory) if depends_on_base_dir else None,
            keyword=keyword,
        )

    def documentation_actions(
        self, target: DocumentationTarget, document: TextDocument
    ) -> List[Union[Command, CodeAction]]:
        return [
            CodeAction(
                "Show in Documentation Viewer",
                kind=CodeActionKind.SOURCE,
                command=Command("Show in Documentation Viewer", "robotcode.showInDocumentationViewer", [target]),
                is_preferred=True,
            ),
            CodeAction(
                "Show in New Documentation Viewer",
                kind=CodeActionKind.SOURCE,
                command=Command("Show in New Documentation Viewer", "robotcode.showInNewDocumentationViewer", [target]),
            ),
            self.open_documentation_code_action(self.build_url(target, document)),
        ]

    def open_documentation_code_action(self, url: str) -> CodeAction:
        return CodeAction(
            "Open Documentation (deprecated)",
            kind=CodeActionKind.SOURCE,
            command=Command("Open Documentation (deprecated)", "robotcode.showDocumentation", [url]),
        )

    def build_url(self, target: DocumentationTarget, document: TextDocument) -> str:
        base_dir = Path(target.base_dir) if target.base_dir is not None else document.uri.to_path().parent

        workspace_folder = self.parent.workspace.get_workspace_folder(document.uri)
        if workspace_folder is not None:
            try:
                base_dir = base_dir.relative_to(workspace_folder.uri.to_path())
            except ValueError:
                pass

        base_url = f"http://localhost:{self.parent.http_server.port}"
        params = urllib.parse.urlencode(
            {
                "name": target.name,
                "args": "::".join(target.args),
                "basedir": str(base_dir),
                "theme": "${theme}",
            }
        )

        return f"{base_url}/?&{params}{f'#{target.keyword}' if target.keyword else ''}"

    @rpc_method(name="robot/documentationServer/convertUri", param_type=ConvertUriParams, threaded=True)
    def _convert_uri(self, uri: str, *args: Any, **kwargs: Any) -> Optional[str]:
        real_uri = Uri(uri)

        folder = self.parent.workspace.get_workspace_folder(real_uri)

        if folder:
            path = real_uri.to_path().relative_to(folder.uri.to_path())

            return f"http://localhost:{self.parent.http_server.port}/{path.as_posix()}"

        return None
