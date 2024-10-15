import ast
from abc import ABC
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Iterator,
    Optional,
    Type,
)

from robot.parsing.model.statements import Statement


def _patch_robot() -> None:
    if hasattr(Statement, "_fields"):
        Statement._fields = ()


_patch_robot()


def iter_fields(node: ast.AST) -> Iterator[Any]:
    for field in node._fields:
        try:
            yield field, getattr(node, field)
        except AttributeError:
            pass


def iter_field_values(node: ast.AST) -> Iterator[Any]:
    for field in node._fields:
        try:
            yield getattr(node, field)
        except AttributeError:
            pass


def iter_child_nodes(node: ast.AST) -> Iterator[ast.AST]:
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


class VisitorFinder(ABC):
    __cls_finder_cache__: Dict[Type[Any], Optional[Callable[..., Any]]]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.__cls_finder_cache__ = {}

    @classmethod
    def __find_visitor(cls, node_cls: Type[Any]) -> Optional[Callable[..., Any]]:
        if node_cls is ast.AST:
            return None
        method_name = "visit_" + node_cls.__name__
        method = getattr(cls, method_name, None)
        if callable(method):
            return method  # type: ignore[no-any-return]
        for base in node_cls.__bases__:
            method = cls._find_visitor(base)
            if method:
                return method
        return None

    @classmethod
    def _find_visitor(cls, node_cls: Type[Any]) -> Optional[Callable[..., Any]]:
        if node_cls in cls.__cls_finder_cache__:
            return cls.__cls_finder_cache__[node_cls]

        result = cls.__cls_finder_cache__[node_cls] = cls.__find_visitor(node_cls)
        return result


class Visitor(VisitorFinder):
    def visit(self, node: ast.AST) -> None:
        visitor = self._find_visitor(type(node)) or self.__class__.generic_visit
        visitor(self, node)

    def generic_visit(self, node: ast.AST) -> None:
        for value in iter_field_values(node):
            if value is None:
                continue
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        self.visit(item)
            else:
                self.visit(value)
