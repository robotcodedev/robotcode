import ast
import itertools
from typing import TYPE_CHECKING, Any, List, Optional, Union

from robot.errors import VariableError
from robot.parsing.lexer.tokens import Token
from robot.parsing.model.blocks import Keyword, Section, TestCase
from robot.parsing.model.statements import Statement
from robot.variables import search_variable

from robotcode.core.language import language_id
from robotcode.core.lsp.types import (
    DocumentSymbol,
    SymbolInformation,
    SymbolKind,
)
from robotcode.core.text_document import TextDocument
from robotcode.core.utils.logging import LoggingDescriptor
from robotcode.robot.utils.ast import (
    range_from_node,
    range_from_token,
    tokenize_variables,
)
from robotcode.robot.utils.visitor import Visitor

from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


class RobotDocumentSymbolsProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: "RobotLanguageServerProtocol") -> None:
        super().__init__(parent)

        parent.document_symbols.collect.add(self.collect)

    @language_id("robotframework")
    @_logger.call
    def collect(
        self, sender: Any, document: TextDocument
    ) -> Optional[Union[List[DocumentSymbol], List[SymbolInformation], None]]:
        return _Visitor.find_from(self.parent.documents_cache.get_model(document, False), self)


class _Visitor(Visitor):
    def __init__(self, parent: RobotDocumentSymbolsProtocolPart) -> None:
        super().__init__()
        self.parent = parent

        self.result: List[DocumentSymbol] = []
        self.current_symbol: Optional[DocumentSymbol] = None

    def generic_visit_current_symbol(self, node: ast.AST, symbol: DocumentSymbol) -> None:
        old = self.current_symbol
        self.current_symbol = symbol
        try:
            self.generic_visit(node)
        finally:
            self.current_symbol = old

    @classmethod
    def find_from(cls, model: ast.AST, parent: RobotDocumentSymbolsProtocolPart) -> Optional[List[DocumentSymbol]]:
        finder = cls(parent)

        finder.visit(model)

        return finder.result if finder.result else None

    def visit_Section(self, node: Section) -> None:  # noqa: N802
        if not node.header or not node.header.name:
            return

        r = range_from_node(node)
        symbol = DocumentSymbol(
            name=node.header.name,
            kind=SymbolKind.MODULE,
            range=r,
            selection_range=r,
            children=[],
        )

        self.result.append(symbol)

        self.generic_visit_current_symbol(node, symbol)

    def visit_TestCase(self, node: TestCase) -> None:  # noqa: N802
        if node.name is None:
            return

        if self.current_symbol is not None and self.current_symbol.children is not None:
            r = range_from_node(node)
            symbol = DocumentSymbol(
                name=node.name,
                kind=SymbolKind.METHOD,
                range=r,
                selection_range=r,
                children=[],
            )
            self.current_symbol.children.append(symbol)

            self.generic_visit_current_symbol(node, symbol)

    def visit_Keyword(self, node: Keyword) -> None:  # noqa: N802
        if node.name is None:
            return

        if self.current_symbol is not None and self.current_symbol.children is not None:
            r = range_from_node(node)
            symbol = DocumentSymbol(
                name=node.name,
                kind=SymbolKind.FUNCTION,
                range=r,
                selection_range=r,
                children=[],
            )
            self.current_symbol.children.append(symbol)

            self.generic_visit_current_symbol(node, symbol)

    def visit_Arguments(self, node: Statement) -> None:  # noqa: N802
        arguments = node.get_tokens(Token.ARGUMENT)

        if self.current_symbol is not None and self.current_symbol.children is not None:
            for argument_token in arguments:
                if argument_token.value == "@{}":
                    continue

                argument = self.get_variable_token(argument_token)

                if argument is not None:
                    r = range_from_token(argument)

                    symbol = DocumentSymbol(
                        name=argument.value,
                        kind=SymbolKind.VARIABLE,
                        range=r,
                        selection_range=r,
                    )
                    if symbol.name not in map(lambda v: v.name, self.current_symbol.children):
                        self.current_symbol.children.append(symbol)

    def get_variable_token(self, token: Token) -> Optional[Token]:
        return next(
            (
                v
                for v in itertools.dropwhile(
                    lambda t: t.type in Token.NON_DATA_TOKENS,
                    tokenize_variables(token, ignore_errors=True),
                )
                if v.type == Token.VARIABLE
            ),
            None,
        )

    def visit_KeywordCall(self, node: Statement) -> None:  # noqa: N802
        # TODO  analyse "Set Local/Global/Suite Variable"

        for assign_token in node.get_tokens(Token.ASSIGN):
            if assign_token is None:
                continue

            if self.current_symbol is not None and self.current_symbol.children is not None:
                try:
                    variable_token = self.get_variable_token(assign_token)

                    if variable_token is not None:
                        r = range_from_token(variable_token)

                        symbol = DocumentSymbol(
                            name=variable_token.value,
                            kind=SymbolKind.VARIABLE,
                            range=r,
                            selection_range=r,
                        )
                        if symbol.name not in map(lambda v: v.name, self.current_symbol.children):
                            self.current_symbol.children.append(symbol)

                except VariableError:
                    pass

    def visit_ForHeader(self, node: Statement) -> None:  # noqa: N802
        variables = node.get_tokens(Token.VARIABLE)

        if self.current_symbol is not None and self.current_symbol.children is not None:
            for variable in variables:
                variable_token = self.get_variable_token(variable)
                if variable_token is not None:
                    r = range_from_token(variable_token)
                    symbol = DocumentSymbol(
                        name=variable_token.value,
                        kind=SymbolKind.VARIABLE,
                        range=r,
                        selection_range=r,
                    )
                    if symbol.name not in map(lambda v: v.name, self.current_symbol.children):
                        self.current_symbol.children.append(symbol)

    def visit_ExceptHeader(self, node: Statement) -> None:  # noqa: N802
        variables = node.get_tokens(Token.VARIABLE)

        if self.current_symbol is not None and self.current_symbol.children is not None:
            for variable in variables:
                variable_token = self.get_variable_token(variable)
                if variable_token is not None:
                    r = range_from_token(variable_token)
                    symbol = DocumentSymbol(
                        name=variable_token.value,
                        kind=SymbolKind.VARIABLE,
                        range=r,
                        selection_range=r,
                    )
                    if symbol.name not in map(lambda v: v.name, self.current_symbol.children):
                        self.current_symbol.children.append(symbol)

    def visit_Var(self, node: Statement) -> None:  # noqa: N802
        variables = node.get_tokens(Token.VARIABLE)

        if self.current_symbol is not None and self.current_symbol.children is not None:
            for variable in variables:
                variable_token = self.get_variable_token(variable)
                if variable_token is not None:
                    r = range_from_token(variable_token)
                    symbol = DocumentSymbol(
                        name=variable_token.value,
                        kind=SymbolKind.VARIABLE,
                        range=r,
                        selection_range=r,
                    )
                    if symbol.name not in map(lambda v: v.name, self.current_symbol.children):
                        self.current_symbol.children.append(symbol)

    def visit_KeywordName(self, node: Statement) -> None:  # noqa: N802
        name_token = node.get_token(Token.KEYWORD_NAME)
        if name_token is None:
            return

        if self.current_symbol is not None and self.current_symbol.children is not None:
            for variable in filter(
                lambda e: e.type == Token.VARIABLE,
                tokenize_variables(name_token, identifiers="$", ignore_errors=True),
            ):
                variable_token = self.get_variable_token(variable)
                if variable_token is not None:
                    r = range_from_token(variable_token)
                    symbol = DocumentSymbol(
                        name=variable_token.value,
                        kind=SymbolKind.VARIABLE,
                        range=r,
                        selection_range=r,
                    )
                    if symbol.name not in map(lambda v: v.name, self.current_symbol.children):
                        self.current_symbol.children.append(symbol)

    def visit_Variable(self, node: Statement) -> None:  # noqa: N802
        name_token = node.get_token(Token.VARIABLE)
        name = name_token.value

        if name is not None:
            match = search_variable(name, ignore_errors=True)
            if not match.is_assign(allow_assign_mark=True):
                return

            if name.endswith("="):
                name = name[:-1].rstrip()

        if self.current_symbol is not None and self.current_symbol.children is not None:
            r = range_from_node(node)
            symbol = DocumentSymbol(name=name, kind=SymbolKind.VARIABLE, range=r, selection_range=r)
            self.current_symbol.children.append(symbol)
