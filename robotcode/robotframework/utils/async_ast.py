import ast
from typing import Any, AsyncIterator, Callable, Optional, Type, cast

__all__ = ["iter_fields", "iter_child_nodes", "AsyncVisitor", "walk"]


async def iter_fields(node: ast.AST) -> AsyncIterator[Any]:
    """
    Yield a tuple of ``(fieldname, value)`` for each field in ``node._fields``
    that is present on *node*.
    """
    for field in node._fields:
        try:
            yield field, getattr(node, field)
        except AttributeError:
            pass


async def iter_child_nodes(node: ast.AST) -> AsyncIterator[ast.AST]:
    """
    Yield all direct child nodes of *node*, that is, all fields that are nodes
    and all items of fields that are lists of nodes.
    """
    async for name, field in iter_fields(node):
        if isinstance(field, ast.AST):
            yield field
        elif isinstance(field, list):
            for item in field:
                if isinstance(item, ast.AST):
                    yield item


async def walk(node: ast.AST) -> AsyncIterator[ast.AST]:
    from collections import deque

    todo = deque([node])
    while todo:
        node = todo.popleft()
        todo.extend([e async for e in iter_child_nodes(node)])
        yield node


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
        async for field, value in iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        await self.visit(item)
            elif isinstance(value, ast.AST):
                await self.visit(value)
