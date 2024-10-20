import ast
import asyncio
import reprlib
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    List,
    Optional,
    Tuple,
    Type,
    cast,
)

from robot.parsing.lexer.tokens import Token
from robot.parsing.model.blocks import TestCase, TestCaseSection
from robot.parsing.model.statements import Documentation, Tags

from robotcode.core.concurrent import check_current_task_canceled
from robotcode.core.language import language_id
from robotcode.core.lsp.types import (
    Hover,
    MarkupContent,
    MarkupKind,
    Position,
    Range,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import TRACE, LoggingDescriptor
from robotcode.robot.diagnostics.entities import VariableDefinitionType
from robotcode.robot.diagnostics.model_helper import ModelHelper
from robotcode.robot.utils.ast import (
    get_nodes_at_position,
    range_from_node,
    range_from_token,
)
from robotcode.robot.utils.markdownformatter import MarkDownFormatter

from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol

_HoverMethod = Callable[[ast.AST, List[ast.AST], TextDocument, Position], Optional[Hover]]


class RobotHoverProtocolPart(RobotLanguageServerProtocolPart, ModelHelper):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

        parent.hover.collect.add(self.collect)

    def _find_method(self, cls: Type[Any]) -> Optional[_HoverMethod]:
        if cls is ast.AST:
            return None
        method_name = "hover_" + cls.__name__
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            if callable(method):
                return cast(_HoverMethod, method)
        for base in cls.__bases__:
            method = self._find_method(base)
            if method:
                return cast(_HoverMethod, method)

        return None

    @language_id("robotframework")
    @_logger.call
    def collect(self, sender: Any, document: TextDocument, position: Position) -> Optional[Hover]:
        model = self.parent.documents_cache.get_model(document)

        result_nodes = get_nodes_at_position(model, position)

        if not result_nodes:
            return None

        result = self._hover_default(result_nodes, document, position)
        if result:
            return result

        for result_node in reversed(result_nodes):
            check_current_task_canceled()

            method = self._find_method(type(result_node))
            if method is not None:
                result = method(result_node, result_nodes, document, position)
                if result is not None:
                    return result

        return None

    def _hover_default(self, nodes: List[ast.AST], document: TextDocument, position: Position) -> Optional[Hover]:
        namespace = self.parent.documents_cache.get_namespace(document)

        all_variable_refs = namespace.get_variable_references()
        if all_variable_refs:
            text = None
            highlight_range = None

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
                value = None
                if found_range is not None:
                    highlight_range = found_range
                    if variable.has_value or variable.resolvable:
                        if (
                            variable.type == VariableDefinitionType.BUILTIN_VARIABLE
                            and variable.matcher.normalized_name == "empty"
                        ):
                            line = document.get_lines()[found_range.start.line]
                            prefix = line[found_range.start.character - 2 : found_range.start.character - 1]
                            if prefix == "$":
                                value = "''"
                            elif prefix == "&":
                                value = "{}"
                            elif prefix == "@":
                                value = "[]"
                        else:
                            try:
                                value = reprlib.repr(
                                    namespace.imports_manager.resolve_variable(
                                        variable.name,
                                        str(document.uri.to_path().parent),
                                        namespace.get_resolvable_variables(nodes, position),
                                    )
                                )
                            except (
                                asyncio.CancelledError,
                                SystemExit,
                                KeyboardInterrupt,
                            ):
                                raise
                            except BaseException:
                                self._logger.exception("Error resolving variable: {e}", level=TRACE)
                                value = ""
                    else:
                        value = ""
                    if text is None:
                        text = ""
                    if text:
                        text += "\n"

                    text += f"| ({variable.type.value}) | {variable.name} | {f' `{value}`' if value else ''} |"

            if text:
                text = "| | | |\n|:--|:--|:--|\n" + text
                return Hover(
                    contents=MarkupContent(kind=MarkupKind.MARKDOWN, value=text),
                    range=highlight_range,
                )

        all_kw_refs = namespace.get_keyword_references()
        if all_kw_refs:
            result: List[Tuple[Range, str]] = []

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

                if found_range is not None:

                    if kw.libtype == "RESOURCE":
                        txt = kw.to_markdown(
                            modify_doc_handler=lambda t: namespace.imports_manager.replace_variables_scalar(
                                t,
                                str(document.uri.to_path().parent),
                                namespace.get_resolvable_variables(),
                                ignore_errors=True,
                            )
                        )
                    else:
                        txt = kw.to_markdown()

                    result.append((found_range, txt))
            if result:
                r = result[0][0]
                if all(r == i[0] for i in result):
                    doc = "\n\n---\n\n".join(i[1] for i in result)

                    return Hover(
                        contents=MarkupContent(kind=MarkupKind.MARKDOWN, value=doc),
                        range=r,
                    )

        all_namespace_refs = namespace.get_namespace_references()
        if all_namespace_refs:
            for ns, ns_refs in all_namespace_refs.items():
                check_current_task_canceled()

                found_range = (
                    ns.import_range
                    if ns.import_source == namespace.source and position.is_in_range(ns.import_range, False)
                    else (
                        ns.alias_range
                        if ns.import_source == namespace.source and position.is_in_range(ns.alias_range, False)
                        else cast(
                            Optional[Range],
                            next(
                                (r.range for r in ns_refs if position.is_in_range(r.range, False)),
                                None,
                            ),
                        )
                    )
                )

                if found_range is not None:
                    return Hover(
                        contents=MarkupContent(
                            kind=MarkupKind.MARKDOWN,
                            value=ns.library_doc.to_markdown(),
                        ),
                        range=found_range,
                    )

        return None

    def hover_TestCase(  # noqa: N802
        self,
        node: ast.AST,
        nodes: List[ast.AST],
        document: TextDocument,
        position: Position,
    ) -> Optional[Hover]:
        namespace = self.parent.documents_cache.get_namespace(document)
        test_case = cast(TestCase, node)

        if not position.is_in_range(range_from_node(test_case.header)):
            return None

        name_token = test_case.header.get_token(Token.TESTCASE_NAME)
        if name_token is None:
            return None

        doc = next((e for e in test_case.body if isinstance(e, Documentation)), None)
        tags = next((e for e in test_case.body if isinstance(e, Tags)), None)

        section = next((e for e in nodes if isinstance(e, TestCaseSection)), None)
        if section is not None and section.tasks:
            txt = f"= Task *{test_case.name}* =\n"
        else:
            txt = f"= Test Case *{test_case.name}* =\n"

        if doc is not None:
            txt += "\n== Documentation ==\n"
            txt += f"\n{doc.value}\n"

        if tags is not None:
            txt += "\n*Tags*: "
            txt += f"{', '.join(tags.values)}\n"

        txt = namespace.imports_manager.replace_variables_scalar(
            txt,
            str(document.uri.to_path().parent),
            namespace.get_resolvable_variables(),
            ignore_errors=True,
        )
        return Hover(
            contents=MarkupContent(kind=MarkupKind.MARKDOWN, value=MarkDownFormatter().format(txt)),
            range=range_from_token(name_token),
        )
