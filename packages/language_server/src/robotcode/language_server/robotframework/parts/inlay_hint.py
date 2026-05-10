import ast
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Type, cast

from robot.parsing.lexer.tokens import Token

from robotcode.core.concurrent import check_current_task_canceled
from robotcode.core.language import language_id
from robotcode.core.lsp.types import InlayHint, InlayHintKind, Position, Range
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.robot.diagnostics.library_doc import (
    KeywordArgumentKind,
    KeywordDoc,
    LibraryDoc,
)
from robotcode.robot.diagnostics.namespace import Namespace
from robotcode.robot.diagnostics.semantic_analyzer.enums import ImportType, TokenKind
from robotcode.robot.diagnostics.semantic_analyzer.model import SemanticModel
from robotcode.robot.diagnostics.semantic_analyzer.nodes import (
    ImportStatement,
    KeywordCallStatement,
    SemanticToken,
)
from robotcode.robot.utils.ast import (
    iter_nodes,
    range_from_node,
    range_from_token,
)

from ..configuration import InlayHintsConfig

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

from robotcode.robot.diagnostics.model_helper import ModelHelper

from .protocol_part import RobotLanguageServerProtocolPart

_HandlerMethod = Callable[
    [TextDocument, Range, ast.AST, ast.AST, Namespace, InlayHintsConfig],
    Optional[List[InlayHint]],
]


class RobotInlayHintProtocolPart(RobotLanguageServerProtocolPart, ModelHelper):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

        parent.inlay_hint.collect.add(self.collect)

    def get_config(self, document: TextDocument) -> Optional[InlayHintsConfig]:
        folder = self.parent.workspace.get_workspace_folder(document.uri)
        if folder is None:
            return None

        return self.parent.workspace.get_configuration(InlayHintsConfig, folder.uri)

    def _find_method(self, cls: Type[Any]) -> Optional[_HandlerMethod]:
        if cls is ast.AST:
            return None
        method_name = "handle_" + cls.__name__
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            if callable(method):
                return cast(_HandlerMethod, method)
        for base in cls.__bases__:
            method = self._find_method(base)
            if method:
                return method

        return None

    @language_id("robotframework")
    @_logger.call
    def collect(self, sender: Any, document: TextDocument, range: Range) -> Optional[List[InlayHint]]:
        config = self.get_config(document)
        if config is None or (not config.parameter_names and not config.namespaces):
            return None

        namespace = self.parent.documents_cache.get_namespace(document)

        # Tier 2 model-based path — used when the experimental SemanticAnalyzer
        # is enabled (semantic_model is populated). Falls back to the legacy
        # ModelHelper-based path otherwise.
        semantic_model = namespace.semantic_model
        if semantic_model is not None:
            return self._collect_from_model(document, range, namespace, semantic_model, config)

        model = self.parent.documents_cache.get_model(document)
        return self._collect_legacy(document, range, model, namespace, config)

    def _collect_legacy(
        self,
        document: TextDocument,
        range: Range,
        model: ast.AST,
        namespace: Namespace,
        config: InlayHintsConfig,
    ) -> List[InlayHint]:
        """Legacy AST-walk based collection. Kept callable directly so that
        tests can compare it against `_collect_from_model` for equivalence.
        """
        result: List[InlayHint] = []
        for node in iter_nodes(model):
            check_current_task_canceled()

            node_range = range_from_node(node)
            if node_range.end < range.start:
                continue

            if node_range.start > range.end:
                break

            method = self._find_method(type(node))
            if method is not None:
                r = method(document, range, node, model, namespace, config)
                if r is not None:
                    result.extend(r)
        return result

    # ------------------------------------------------------------------
    # Tier 2 model-based collection
    # ------------------------------------------------------------------

    def _collect_from_model(
        self,
        document: TextDocument,
        range: Range,
        namespace: Namespace,
        model: SemanticModel,
        config: InlayHintsConfig,
    ) -> List[InlayHint]:
        """Iterate the SemanticModel statements and produce inlay hints
        directly from the pre-resolved data (no second find_keyword pass,
        no AST re-walk for imports).

        Note: `RunKeywordCallStatement.inner_calls` are intentionally NOT
        traversed here. The legacy AST-walk path also doesn't reach
        Run-Keyword-If inner arguments (they live inside the parent's
        argument tokens, not as standalone AST nodes), so doing so in the
        model path would introduce a drift. If we want hints inside
        `Run Keyword If    cond    Log    msg`, that's a future feature
        and needs a separate equivalence story.
        """
        result: List[InlayHint] = []
        for stmt in model.statements:
            check_current_task_canceled()

            # Range filter — `range` lines are 0-indexed, stmt.line_* are 1-indexed.
            if stmt.line_end - 1 < range.start.line:
                continue
            if stmt.line_start - 1 > range.end.line:
                break

            if isinstance(stmt, KeywordCallStatement) and stmt.keyword_doc is not None:
                hints = self._inlay_hints_for_keyword_call(stmt, namespace, config)
                if hints:
                    result.extend(hints)
            elif (
                config.parameter_names
                and isinstance(stmt, ImportStatement)
                and stmt.init_keyword_doc is not None
                and stmt.import_type in (ImportType.LIBRARY, ImportType.VARIABLES)
            ):
                hints = self._inlay_hints_for_import(stmt, namespace, config)
                if hints:
                    result.extend(hints)

        return result

    def _inlay_hints_for_import(
        self,
        stmt: ImportStatement,
        namespace: Namespace,
        config: InlayHintsConfig,
    ) -> Optional[List[InlayHint]]:
        kw_doc = stmt.init_keyword_doc
        if kw_doc is None:
            return None

        arg_tokens = [t for t in stmt.tokens if t.kind is TokenKind.ARGUMENT]
        # Imports never get a namespace prefix hint — pass keyword_token=None
        # so the namespace branch in the helper is skipped.
        return self._get_inlay_hint_from_semantic_tokens(
            keyword_token=None,
            kw_doc=kw_doc,
            arg_tokens=arg_tokens,
            arg_values=[t.value for t in arg_tokens],
            has_namespace_token=True,
            namespace=namespace,
            config=config,
        )

    def _inlay_hints_for_keyword_call(
        self,
        stmt: KeywordCallStatement,
        namespace: Namespace,
        config: InlayHintsConfig,
    ) -> Optional[List[InlayHint]]:
        kw_doc = stmt.keyword_doc
        if kw_doc is None:
            return None

        # Top-level argument tokens carry positional/named args. NAMED_ARGUMENT_NAME
        # tokens already imply the user wrote the name, so a parameter-name hint
        # is redundant; we work from the parent ARGUMENT positions.
        arg_tokens = [t for t in stmt.tokens if t.kind is TokenKind.ARGUMENT]

        keyword_token = next((t for t in stmt.tokens if t.kind is TokenKind.KEYWORD), None)
        has_namespace_token = any(t.kind is TokenKind.NAMESPACE for t in stmt.tokens)

        return self._get_inlay_hint_from_semantic_tokens(
            keyword_token=keyword_token,
            kw_doc=kw_doc,
            arg_tokens=arg_tokens,
            arg_values=[t.value for t in arg_tokens],
            has_namespace_token=has_namespace_token,
            namespace=namespace,
            config=config,
        )

    @staticmethod
    def _get_inlay_hint_from_semantic_tokens(
        keyword_token: Optional[SemanticToken],
        kw_doc: KeywordDoc,
        arg_tokens: List[SemanticToken],
        arg_values: List[str],
        has_namespace_token: bool,
        namespace: Namespace,
        config: InlayHintsConfig,
    ) -> Optional[List[InlayHint]]:
        """Model-based variant of `_get_inlay_hint`. Operates on SemanticTokens
        rather than RF tokens. Pure function so it can be unit-tested without
        the LSP protocol stack.
        """
        from robot.errors import DataError

        result: List[InlayHint] = []

        if config.parameter_names:
            positional = None
            if kw_doc.arguments_spec is not None:
                try:
                    positional, _ = kw_doc.arguments_spec.resolve(
                        arg_values,
                        None,
                        resolve_variables_until=kw_doc.args_to_process,
                        resolve_named=not kw_doc.is_any_run_keyword(),
                        validate=False,
                    )
                except DataError:
                    pass

            if positional is not None:
                kw_arguments = [
                    a
                    for a in kw_doc.arguments
                    if a.kind
                    not in [
                        KeywordArgumentKind.NAMED_ONLY_MARKER,
                        KeywordArgumentKind.POSITIONAL_ONLY_MARKER,
                        KeywordArgumentKind.VAR_NAMED,
                        KeywordArgumentKind.NAMED_ONLY,
                    ]
                ]
                for i, _ in enumerate(positional):
                    if i >= len(arg_tokens):
                        break

                    index = i if i < len(kw_arguments) else len(kw_arguments) - 1
                    if index < 0:
                        continue

                    arg = kw_arguments[index]
                    if i >= len(kw_arguments) and arg.kind != KeywordArgumentKind.VAR_POSITIONAL:
                        break

                    prefix = ""
                    if arg.kind == KeywordArgumentKind.VAR_POSITIONAL:
                        prefix = "*"
                    elif arg.kind == KeywordArgumentKind.VAR_NAMED:
                        prefix = "**"

                    arg_token = arg_tokens[i]
                    result.append(
                        InlayHint(
                            Position(line=arg_token.line - 1, character=arg_token.col_offset),
                            f"{prefix}{arg.name}=",
                            InlayHintKind.PARAMETER,
                        )
                    )

        if keyword_token is not None and config.namespaces and not has_namespace_token:
            # Only suggest a namespace prefix if the user didn't already write one.
            if kw_doc.libtype == "LIBRARY":
                lib = next(
                    (
                        lib
                        for lib in namespace.libraries.values()
                        if lib.name == kw_doc.libname and kw_doc in lib.library_doc.keywords.keywords
                    ),
                    None,
                )
            else:
                lib = next(
                    (
                        lib
                        for lib in namespace.resources.values()
                        if lib.name == kw_doc.libname and kw_doc in lib.library_doc.keywords.keywords
                    ),
                    None,
                )
            if lib is not None:
                result.append(
                    InlayHint(
                        Position(line=keyword_token.line - 1, character=keyword_token.col_offset),
                        f"{lib.alias or lib.name}.",
                    )
                )

        return result

    def _handle_keywordcall_fixture_template(
        self,
        keyword_token: Token,
        arguments: List[Token],
        namespace: Namespace,
        config: InlayHintsConfig,
    ) -> Optional[List[InlayHint]]:
        kw_result = self.get_keyworddoc_and_token_from_position(
            keyword_token.value,
            keyword_token,
            arguments,
            namespace,
            range_from_token(keyword_token).end,
        )

        if kw_result is None:
            return None

        kw_doc, keyword_token = kw_result

        if kw_doc is None:
            return None

        return self._get_inlay_hint(keyword_token, kw_doc, arguments, namespace, config)

    def _get_inlay_hint(
        self,
        keyword_token: Optional[Token],
        kw_doc: KeywordDoc,
        arguments: List[Token],
        namespace: Namespace,
        config: InlayHintsConfig,
    ) -> Optional[List[InlayHint]]:
        from robot.errors import DataError

        result: List[InlayHint] = []

        if config.parameter_names:
            positional = None
            if kw_doc.arguments_spec is not None:
                try:
                    positional, _ = kw_doc.arguments_spec.resolve(
                        [a.value for a in arguments],
                        None,
                        resolve_variables_until=kw_doc.args_to_process,
                        resolve_named=not kw_doc.is_any_run_keyword(),
                        validate=False,
                    )
                except DataError:
                    pass

            if positional is not None:
                kw_arguments = [
                    a
                    for a in kw_doc.arguments
                    if a.kind
                    not in [
                        KeywordArgumentKind.NAMED_ONLY_MARKER,
                        KeywordArgumentKind.POSITIONAL_ONLY_MARKER,
                        KeywordArgumentKind.VAR_NAMED,
                        KeywordArgumentKind.NAMED_ONLY,
                    ]
                ]
                for i, _ in enumerate(positional):
                    if i >= len(arguments):
                        break

                    index = i if i < len(kw_arguments) else len(kw_arguments) - 1
                    if index < 0:
                        continue

                    arg = kw_arguments[index]
                    if i >= len(kw_arguments) and arg.kind != KeywordArgumentKind.VAR_POSITIONAL:
                        break

                    prefix = ""
                    if arg.kind == KeywordArgumentKind.VAR_POSITIONAL:
                        prefix = "*"
                    elif arg.kind == KeywordArgumentKind.VAR_NAMED:
                        prefix = "**"

                    result.append(
                        InlayHint(
                            range_from_token(arguments[i]).start,
                            f"{prefix}{arg.name}=",
                            InlayHintKind.PARAMETER,
                        )
                    )

        if keyword_token is not None and config.namespaces:
            (
                lib_entry,
                kw_namespace,
            ) = self.get_namespace_info_from_keyword_token(namespace, keyword_token)
            if lib_entry is None and kw_namespace is None:
                if kw_doc.libtype == "LIBRARY":
                    lib = next(
                        (
                            lib
                            for lib in namespace.libraries.values()
                            if lib.name == kw_doc.libname and kw_doc in lib.library_doc.keywords.keywords
                        ),
                        None,
                    )
                else:
                    lib = next(
                        (
                            lib
                            for lib in namespace.resources.values()
                            if lib.name == kw_doc.libname and kw_doc in lib.library_doc.keywords.keywords
                        ),
                        None,
                    )
                if lib is not None:
                    result.append(
                        InlayHint(
                            range_from_token(keyword_token).start,
                            f"{lib.alias or lib.name}.",
                        )
                    )

        return result

    def handle_KeywordCall(  # noqa: N802
        self,
        document: TextDocument,
        range: Range,
        node: ast.AST,
        model: ast.AST,
        namespace: Namespace,
        config: InlayHintsConfig,
    ) -> Optional[List[InlayHint]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import KeywordCall

        keyword_call = cast(KeywordCall, node)
        keyword_token = keyword_call.get_token(RobotToken.KEYWORD)
        if keyword_token is None or not keyword_token.value:
            return None

        arguments = keyword_call.get_tokens(RobotToken.ARGUMENT)
        return self._handle_keywordcall_fixture_template(keyword_token, arguments, namespace, config)

    def handle_Fixture(  # noqa: N802
        self,
        document: TextDocument,
        range: Range,
        node: ast.AST,
        model: ast.AST,
        namespace: Namespace,
        config: InlayHintsConfig,
    ) -> Optional[List[InlayHint]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Fixture

        fixture = cast(Fixture, node)
        keyword_token = fixture.get_token(RobotToken.NAME)
        if keyword_token is None or not keyword_token.value:
            return None

        arguments = fixture.get_tokens(RobotToken.ARGUMENT)
        return self._handle_keywordcall_fixture_template(keyword_token, arguments, namespace, config)

    def handle_TestTemplate(  # noqa: N802
        self,
        document: TextDocument,
        range: Range,
        node: ast.AST,
        model: ast.AST,
        namespace: Namespace,
        config: InlayHintsConfig,
    ) -> Optional[List[InlayHint]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import TestTemplate

        template = cast(TestTemplate, node)
        keyword_token = template.get_token(RobotToken.NAME, RobotToken.ARGUMENT)
        if keyword_token is None or not keyword_token.value:
            return None

        return self._handle_keywordcall_fixture_template(keyword_token, [], namespace, config)

    def handle_Template(  # noqa: N802
        self,
        document: TextDocument,
        range: Range,
        node: ast.AST,
        model: ast.AST,
        namespace: Namespace,
        config: InlayHintsConfig,
    ) -> Optional[List[InlayHint]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Template

        template = cast(Template, node)
        keyword_token = template.get_token(RobotToken.NAME, RobotToken.ARGUMENT)
        if keyword_token is None or not keyword_token.value:
            return None

        return self._handle_keywordcall_fixture_template(keyword_token, [], namespace, config)

    def handle_LibraryImport(  # noqa: N802
        self,
        document: TextDocument,
        range: Range,
        node: ast.AST,
        model: ast.AST,
        namespace: Namespace,
        config: InlayHintsConfig,
    ) -> Optional[List[InlayHint]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import LibraryImport

        library_node = cast(LibraryImport, node)

        if not library_node.name:
            return None

        lib_doc: Optional[LibraryDoc] = None
        try:
            namespace = self.parent.documents_cache.get_namespace(document)

            lib_doc = namespace.get_imported_library_libdoc(library_node.name, library_node.args, library_node.alias)

            if lib_doc is None or lib_doc.errors:
                lib_doc = namespace.imports_manager.get_libdoc_for_library_import(
                    str(library_node.name),
                    (),
                    str(document.uri.to_path().parent),
                    variables=namespace.get_resolvable_variables(),
                )

        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException:
            return None

        arguments = library_node.get_tokens(RobotToken.ARGUMENT)

        for kw_doc in lib_doc.inits:
            return self._get_inlay_hint(None, kw_doc, arguments, namespace, config)

        return None

    def handle_VariablesImport(  # noqa: N802
        self,
        document: TextDocument,
        range: Range,
        node: ast.AST,
        model: ast.AST,
        namespace: Namespace,
        config: InlayHintsConfig,
    ) -> Optional[List[InlayHint]]:
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import VariablesImport

        library_node = cast(VariablesImport, node)

        if not library_node.name:
            return None

        lib_doc: Optional[LibraryDoc] = None
        try:
            namespace = self.parent.documents_cache.get_namespace(document)

            lib_doc = namespace.get_variables_import_libdoc(library_node.name, library_node.args)

            if lib_doc is None or lib_doc.errors:
                lib_doc = namespace.imports_manager.get_libdoc_for_variables_import(
                    str(library_node.name),
                    (),
                    str(document.uri.to_path().parent),
                    variables=namespace.get_resolvable_variables(),
                )

        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException:
            return None

        arguments = library_node.get_tokens(RobotToken.ARGUMENT)

        for kw_doc in lib_doc.inits:
            return self._get_inlay_hint(None, kw_doc, arguments, namespace, config)

        return None
