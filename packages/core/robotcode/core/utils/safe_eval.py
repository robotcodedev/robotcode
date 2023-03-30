import ast
from typing import Any, Dict, Optional, Sequence


class Transformer(ast.NodeTransformer):
    STD_ALLOWED_NAMES = (
        "None",
        "False",
        "True",
        "str",
        "bool",
        "int",
        "float",
        "list",
        "dict",
        "tuple",
        "bytes",
        "complex",
        "set",
        "bin",
        "pow",
        "min",
        "max",
        "sum",
        "ord",
        "hex",
        "oct",
        "round",
        "sorted",
        "reversed",
        "zip",
        "divmod",
        "range",
        "reprs",
        "enumerate",
        "all",
        "any",
        "filter",
        "abs",
        "map",
        "chr",
        "format",
        "len",
        "ascii",
    )

    def __init__(self, allowed_names: Optional[Sequence[str]]) -> None:
        self.allowed_names = (*self.STD_ALLOWED_NAMES, *(allowed_names or []))

    def visit_Name(self, node: ast.Name) -> ast.AST:  # noqa: N802
        if node.id not in self.allowed_names:
            raise NameError(f"Name access to '{node.id}' is not allowed")

        return self.generic_visit(node)


def safe_eval(source: str, globals: Dict[str, Any] = {}, filename: str = "<expression>") -> Any:
    transformer = Transformer(list(globals.keys()))
    tree = ast.parse(source, mode="eval")
    tree = transformer.visit(tree)
    clause = compile(tree, filename, "eval", dont_inherit=True)
    return eval(clause, globals, {})
