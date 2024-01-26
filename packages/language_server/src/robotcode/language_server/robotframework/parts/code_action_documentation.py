import urllib.parse
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Union, cast

from robot.parsing.lexer.tokens import Token

from robotcode.core.language import language_id
from robotcode.core.lsp.types import (
    CodeAction,
    CodeActionContext,
    CodeActionKind,
    Command,
    Range,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.uri import Uri
from robotcode.core.utils.dataclasses import CamelSnakeMixin
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.jsonrpc2.protocol import rpc_method
from robotcode.robot.diagnostics.entities import LibraryEntry
from robotcode.robot.diagnostics.library_doc import resolve_robot_variables
from robotcode.robot.diagnostics.model_helper import ModelHelper
from robotcode.robot.diagnostics.namespace import Namespace
from robotcode.robot.utils.ast import get_node_at_position, range_from_token

from ...common.decorators import code_action_kinds
from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


@dataclass(repr=False)
class ConvertUriParams(CamelSnakeMixin):
    uri: str


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

        namespace = self.parent.documents_cache.get_namespace(document)

        model = self.parent.documents_cache.get_model(document, False)
        node = get_node_at_position(model, range.start)

        if context.only and isinstance(node, (LibraryImport, ResourceImport)):
            if CodeActionKind.SOURCE.value in context.only and range in range_from_token(
                node.get_token(RobotToken.NAME)
            ):
                url = self.build_url(
                    node.name,
                    node.args if isinstance(node, LibraryImport) else (),
                    document,
                    namespace,
                )

                return [self.open_documentation_code_action(url)]

        if isinstance(node, (KeywordCall, Fixture, TestTemplate, Template)):
            # only source actions

            result = self.get_keyworddoc_and_token_from_position(
                (
                    node.value
                    if isinstance(node, (TestTemplate, Template))
                    else node.keyword if isinstance(node, KeywordCall) else node.name
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
                kw_doc, _ = result

                if kw_doc is not None:
                    if context.only and CodeActionKind.SOURCE.value in context.only:
                        entry: Optional[LibraryEntry] = None

                        if kw_doc.libtype == "LIBRARY":
                            entry = next(
                                (
                                    v
                                    for v in (namespace.get_libraries()).values()
                                    if v.library_doc.digest == kw_doc.parent_digest
                                ),
                                None,
                            )

                        elif kw_doc.libtype == "RESOURCE":
                            entry = next(
                                (
                                    v
                                    for v in (namespace.get_resources()).values()
                                    if v.library_doc.digest == kw_doc.parent_digest
                                ),
                                None,
                            )

                            self_libdoc = namespace.get_library_doc()
                            if entry is None and self_libdoc.digest == kw_doc.parent_digest:
                                entry = LibraryEntry(
                                    self_libdoc.name,
                                    str(document.uri.to_path().name),
                                    self_libdoc,
                                )

                        if entry is None:
                            return None

                        url = self.build_url(
                            entry.import_name,
                            entry.args,
                            document,
                            namespace,
                            kw_doc.name,
                        )

                        return [self.open_documentation_code_action(url)]

        if isinstance(node, KeywordName):
            name_token = node.get_token(RobotToken.KEYWORD_NAME)
            if name_token is not None and range in range_from_token(name_token):
                url = self.build_url(
                    str(document.uri.to_path().name),
                    (),
                    document,
                    namespace,
                    name_token.value,
                )

                return [self.open_documentation_code_action(url)]

        return None

    def open_documentation_code_action(self, url: str) -> CodeAction:
        return CodeAction(
            "Open Documentation",
            kind=CodeActionKind.SOURCE,
            command=Command("Open Documentation", "robotcode.showDocumentation", [url]),
        )

    def build_url(
        self,
        name: str,
        args: Tuple[Any, ...],
        document: TextDocument,
        namespace: Namespace,
        target: Optional[str] = None,
    ) -> str:
        base_dir = document.uri.to_path().parent

        workspace_folder = self.parent.workspace.get_workspace_folder(document.uri)
        if workspace_folder is not None:
            try:
                base_dir = base_dir.relative_to(workspace_folder.uri.to_path())
            except ValueError:
                pass

        robot_variables = resolve_robot_variables(
            str(namespace.imports_manager.root_folder),
            str(base_dir),
            namespace.imports_manager.get_resolvable_command_line_variables(),
            variables=namespace.get_resolvable_variables(),
        )
        try:
            name = robot_variables.replace_string(name, ignore_errors=False)

            args = tuple(robot_variables.replace_string(v, ignore_errors=False) for v in args)

        except (SystemExit, KeyboardInterrupt):
            raise
        except BaseException:
            pass

        url_args = "::".join(args) if args else ""

        base_url = f"http://localhost:{self.parent.http_server.port}"
        params = urllib.parse.urlencode(
            {
                "name": name,
                "args": url_args,
                "basedir": str(base_dir),
                "theme": "${theme}",
            }
        )

        return f"{base_url}/?&{params}{f'#{target}' if target else ''}"

    @rpc_method(name="robot/documentationServer/convertUri", param_type=ConvertUriParams, threaded=True)
    def _convert_uri(self, uri: str, *args: Any, **kwargs: Any) -> Optional[str]:
        real_uri = Uri(uri)

        folder = self.parent.workspace.get_workspace_folder(real_uri)

        if folder:
            path = real_uri.to_path().relative_to(folder.uri.to_path())

            return f"http://localhost:{self.parent.http_server.port}/{path.as_posix()}"

        return None
