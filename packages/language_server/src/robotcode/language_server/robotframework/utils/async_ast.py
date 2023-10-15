import ast
from typing import Any, AsyncIterator, Callable, Dict, Iterator, Optional, Type

__all__ = ["iter_fields", "iter_child_nodes", "AsyncVisitor"]


def iter_fields(node: ast.AST) -> Iterator[Any]:
    """
    Yield a tuple of ``(fieldname, value)`` for each field in ``node._fields``
    that is present on *node*.
    """
    for field in node._fields:
        try:
            yield field, getattr(node, field)
        except AttributeError:
            pass


def iter_child_nodes(node: ast.AST) -> Iterator[ast.AST]:
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


async def iter_nodes(node: ast.AST) -> AsyncIterator[ast.AST]:
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
    __NOT_SET = object()

    def __init__(self) -> None:
        self.__cache: Dict[Type[Any], Optional[Callable[..., Any]]] = {}

    def __find_visitor(self, cls: Type[Any]) -> Optional[Callable[..., Any]]:
        if cls is ast.AST:
            return None
        method_name = "visit_" + cls.__name__
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            if callable(method):
                return method  # type: ignore
        for base in cls.__bases__:
            method = self._find_visitor(base)
            if method:
                return method  # type: ignore
        return None

    def _find_visitor(self, cls: Type[Any]) -> Optional[Callable[..., Any]]:
        r = self.__cache.get(cls, self.__NOT_SET)
        if r is self.__NOT_SET:
            self.__cache[cls] = r = self.__find_visitor(cls)
        return r  # type: ignore


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
