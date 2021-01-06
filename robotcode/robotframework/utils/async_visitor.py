import ast
from typing import Any, AsyncGenerator, AsyncIterator, Callable, Optional, Type, cast

__all__ = ["AsyncVisitor", "walk"]


async def walk(node: ast.AST) -> AsyncGenerator[ast.AST, None]:
    async def iter_child_nodes(node: ast.AST) -> AsyncIterator[ast.AST]:
        for n in ast.iter_child_nodes(node):
            yield n

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
            attr = getattr(self, method_name)
            if callable(attr):
                return cast("Callable[..., Any]", attr)
        for base in cls.__bases__:
            visitor = self._find_visitor(base)
            if visitor:
                return visitor
        return None


class AsyncVisitor(VisitorFinder):
    async def visit(self, node: ast.AST) -> None:
        visitor = self._find_visitor(type(node)) or self.generic_visit
        await visitor(node)

    async def generic_visit(self, node: ast.AST) -> None:
        """Called if no explicit visitor function exists for a node."""
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        await self.visit(item)
            elif isinstance(value, ast.AST):
                await self.visit(value)
