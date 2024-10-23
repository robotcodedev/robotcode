import ast
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Type, cast

from robot.parsing.lexer.tokens import Token

from robotcode.core.concurrent import check_current_task_canceled
from robotcode.core.language import language_id
from robotcode.core.lsp.types import InlayHint, InlayHintKind, Range
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.robot.diagnostics.library_doc import (
    KeywordArgumentKind,
    KeywordDoc,
    LibraryDoc,
)
from robotcode.robot.diagnostics.namespace import Namespace
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
                return cast(_HandlerMethod, method)

        return None

    @language_id("robotframework")
    @_logger.call
    def collect(self, sender: Any, document: TextDocument, range: Range) -> Optional[List[InlayHint]]:
        config = self.get_config(document)
        if config is None or not config.parameter_names and not config.namespaces:
            return None

        model = self.parent.documents_cache.get_model(document, False)
        namespace = self.parent.documents_cache.get_namespace(document)

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
                            for lib in (namespace.get_libraries()).values()
                            if lib.name == kw_doc.libname and kw_doc in lib.library_doc.keywords.keywords
                        ),
                        None,
                    )
                else:
                    lib = next(
                        (
                            lib
                            for lib in (namespace.get_resources()).values()
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
