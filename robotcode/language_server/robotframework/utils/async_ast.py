import ast
from typing import Any, AsyncGenerator, Callable, Generator, Optional, Type, cast

__all__ = ["iter_fields", "iter_child_nodes", "AsyncVisitor"]


def iter_fields(node: ast.AST) -> Generator[Any, None, None]:
    """
    Yield a tuple of ``(fieldname, value)`` for each field in ``node._fields``
    that is present on *node*.
    """
    for field in node._fields:
        try:
            yield field, getattr(node, field)
        except AttributeError:
            pass


def iter_child_nodes(node: ast.AST) -> Generator[ast.AST, None, None]:
    """
    Yield all direct child nodes of *node*, that is, all fields that are nodes
    and all items of fields that are lists of nodes.
    """
    for _name, field in iter_fields(node):
        if isinstance(field, ast.AST):
            yield field
        elif isinstance(field, list):
            for item in field:
                if isinstance(item, ast.AST):
                    yield item


async def iter_nodes(node: ast.AST) -> AsyncGenerator[ast.AST, None]:
    for _name, value in iter_fields(node):
        if isinstance(value, list):
            for item in value:
                if isinstance(item, ast.AST):
                    yield item
                    async for n in iter_nodes(item):
                        yield n

        elif isinstance(value, ast.AST):
            yield value

            async for n in iter_nodes(value):
                yield n


class VisitorFinder:
    def _find_visitor(self, cls: Type[Any]) -> Optional[Callable[..., Any]]:
        if cls is ast.AST:
            return None
        method_name = "visit_" + cls.__name__
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            if callable(method):
                return cast("Callable[..., Any]", method)
        for base in cls.__bases__:
            method = self._find_visitor(base)
            if method:
                return cast("Callable[..., Any]", method)
        return None


class AsyncVisitor(VisitorFinder):
    async def visit(self, node: ast.AST) -> None:
        visitor = self._find_visitor(type(node)) or self.generic_visit
        await visitor(node)

    async def generic_visit(self, node: ast.AST) -> None:
        """Called if no explicit visitor function exists for a node."""
        for _, value in iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        await self.visit(item)
            elif isinstance(value, ast.AST):
                await self.visit(value)


class Visitor(VisitorFinder):
    def visit(self, node: ast.AST) -> None:
        visitor = self._find_visitor(type(node)) or self.generic_visit
        visitor(node)

    def generic_visit(self, node: ast.AST) -> None:
        """Called if no explicit visitor function exists for a node."""
        for field, value in iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        self.visit(item)
            elif isinstance(value, ast.AST):
                self.visit(value)
