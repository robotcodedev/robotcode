from __future__ import annotations

import ast
import itertools
from typing import TYPE_CHECKING, Any, List, Optional, Union, cast

from robotcode.core.logging import LoggingDescriptor
from robotcode.core.lsp.types import DocumentSymbol, SymbolInformation, SymbolKind

from ...common.decorators import language_id
from ...common.text_document import TextDocument
from ..utils.ast_utils import Token, range_from_node, range_from_token, tokenize_variables
from ..utils.async_ast import AsyncVisitor
from .protocol_part import RobotLanguageServerProtocolPart

if TYPE_CHECKING:
    from ..protocol import RobotLanguageServerProtocol


class _Visitor(AsyncVisitor):
    def __init__(self, parent: RobotDocumentSymbolsProtocolPart) -> None:
        super().__init__()
        self.parent = parent

        self.result: List[DocumentSymbol] = []
        self.current_symbol: Optional[DocumentSymbol] = None

    async def generic_visit_current_symbol(self, node: ast.AST, symbol: DocumentSymbol) -> None:
        old = self.current_symbol
        self.current_symbol = symbol
        try:
            await self.generic_visit(node)
        finally:
            self.current_symbol = old

    @classmethod
    async def find_from(
        cls, model: ast.AST, parent: RobotDocumentSymbolsProtocolPart
    ) -> Optional[List[DocumentSymbol]]:
        finder = cls(parent)

        await finder.visit(model)

        return finder.result if finder.result else None

    async def visit_Section(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.model.blocks import Section
        from robot.parsing.model.statements import SectionHeader

        section = cast(Section, node)
        if section.header is None:
            return

        header = cast(SectionHeader, section.header)
        if not header.name:
            return

        r = range_from_node(section)
        symbol = DocumentSymbol(
            name=header.name.replace("*", "").strip(),
            kind=SymbolKind.NAMESPACE,
            range=r,
            selection_range=r,
            children=[],
        )

        self.result.append(symbol)

        await self.generic_visit_current_symbol(node, symbol)

    async def visit_TestCase(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.model.blocks import TestCase

        testcase = cast(TestCase, node)
        if testcase.name is None:
            return

        if self.current_symbol is not None and self.current_symbol.children is not None:
            r = range_from_node(testcase)
            symbol = DocumentSymbol(name=testcase.name, kind=SymbolKind.METHOD, range=r, selection_range=r, children=[])
            self.current_symbol.children.append(symbol)

            await self.generic_visit_current_symbol(node, symbol)

    async def visit_Keyword(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.model.blocks import Keyword

        keyword = cast(Keyword, node)
        if keyword.name is None:
            return

        if self.current_symbol is not None and self.current_symbol.children is not None:
            r = range_from_node(keyword)
            symbol = DocumentSymbol(
                name=keyword.name, kind=SymbolKind.FUNCTION, range=r, selection_range=r, children=[]
            )
            self.current_symbol.children.append(symbol)

            await self.generic_visit_current_symbol(node, symbol)

    async def visit_Arguments(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import Arguments

        n = cast(Arguments, node)
        arguments = n.get_tokens(RobotToken.ARGUMENT)

        if self.current_symbol is not None and self.current_symbol.children is not None:
            for argument_token in (cast(RobotToken, e) for e in arguments):
                if argument_token.value == "@{}":
                    continue

                argument = self.get_variable_token(argument_token)

                if argument is not None:
                    r = range_from_token(argument)

                    symbol = DocumentSymbol(name=argument.value, kind=SymbolKind.VARIABLE, range=r, selection_range=r)
                    if symbol.name not in map(lambda v: v.name, self.current_symbol.children):
                        self.current_symbol.children.append(symbol)

    def get_variable_token(self, token: Token) -> Optional[Token]:
        from robot.parsing.lexer.tokens import Token as RobotToken

        return next(
            (
                v
                for v in itertools.dropwhile(
                    lambda t: t.type in RobotToken.NON_DATA_TOKENS,
                    tokenize_variables(token, ignore_errors=True),
                )
                if v.type == RobotToken.VARIABLE
            ),
            None,
        )

    async def visit_KeywordCall(self, node: ast.AST) -> None:  # noqa: N802
        from robot.errors import VariableError
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import KeywordCall

        # TODO  analyse "Set Local/Global/Suite Variable"

        keyword_call = cast(KeywordCall, node)
        for assign_token in keyword_call.get_tokens(RobotToken.ASSIGN):
            if assign_token is None:
                continue

            if self.current_symbol is not None and self.current_symbol.children is not None:
                try:
                    variable_token = self.get_variable_token(assign_token)

                    if variable_token is not None:
                        r = range_from_token(variable_token)

                        symbol = DocumentSymbol(
                            name=variable_token.value, kind=SymbolKind.VARIABLE, range=r, selection_range=r
                        )
                        if symbol.name not in map(lambda v: v.name, self.current_symbol.children):
                            self.current_symbol.children.append(symbol)

                except VariableError:
                    pass

    async def visit_ForHeader(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import ForHeader

        n = cast(ForHeader, node)
        variables = n.get_tokens(RobotToken.VARIABLE)

        if self.current_symbol is not None and self.current_symbol.children is not None:
            for variable in variables:
                variable_token = self.get_variable_token(variable)
                if variable_token is not None:
                    r = range_from_token(variable_token)
                    symbol = DocumentSymbol(
                        name=variable_token.value, kind=SymbolKind.VARIABLE, range=r, selection_range=r
                    )
                    if symbol.name not in map(lambda v: v.name, self.current_symbol.children):
                        self.current_symbol.children.append(symbol)

    async def visit_KeywordName(self, node: ast.AST) -> None:  # noqa: N802
        from robot.parsing.lexer.tokens import Token as RobotToken
        from robot.parsing.model.statements import KeywordName

        n = cast(KeywordName, node)
        nt = n.get_token(RobotToken.KEYWORD_NAME)
        if nt is None:
            return

        name_token = cast(Token, nt)

        if self.current_symbol is not None and self.current_symbol.children is not None:
            for variable in filter(
                lambda e: e.type == RobotToken.VARIABLE,
                tokenize_variables(name_token, identifiers="$", ignore_errors=True),
            ):
                variable_token = self.get_variable_token(variable)
                if variable_token is not None:
                    r = range_from_token(variable_token)
                    symbol = DocumentSymbol(
                        name=variable_token.value, kind=SymbolKind.VARIABLE, range=r, selection_range=r
                    )
                    if symbol.name not in map(lambda v: v.name, self.current_symbol.children):
                        self.current_symbol.children.append(symbol)

    async def visit_Variable(self, node: ast.AST) -> None:  # noqa: N802
        from robot.api.parsing import Token as RobotToken
        from robot.parsing.model.statements import Variable
        from robot.variables import search_variable

        variable = cast(Variable, node)

        name_token = variable.get_token(RobotToken.VARIABLE)
        name = name_token.value

        if name is not None:
            match = search_variable(name, ignore_errors=True)
            if not match.is_assign(allow_assign_mark=True):
                return

            if name.endswith("="):
                name = name[:-1].rstrip()

        if self.current_symbol is not None and self.current_symbol.children is not None:
            r = range_from_node(variable)
            symbol = DocumentSymbol(name=name, kind=SymbolKind.VARIABLE, range=r, selection_range=r)
            self.current_symbol.children.append(symbol)


class RobotDocumentSymbolsProtocolPart(RobotLanguageServerProtocolPart):
    _logger = LoggingDescriptor()

    def __init__(self, parent: RobotLanguageServerProtocol) -> None:
        super().__init__(parent)

        parent.document_symbols.collect.add(self.collect)

    @language_id("robotframework")
    @_logger.call
    async def collect(
        self, sender: Any, document: TextDocument
    ) -> Optional[Union[List[DocumentSymbol], List[SymbolInformation], None]]:
        return await _Visitor.find_from(await self.parent.documents_cache.get_model(document), self)
