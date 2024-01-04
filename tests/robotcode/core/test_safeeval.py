import os
import re
from typing import Any

import pytest

from robotcode.core.utils.safe_eval import safe_eval


@pytest.mark.parametrize(
    ("expression", "result"),
    [
        ("1", 1),
        ("1.0", 1.0),
        ("True", True),
        ("False", False),
        ("None", None),
        ("1+1", 2),
        ("'1'+'1'", "11"),
    ],
)
def test_safe_eval_simple_expressions_should_work(expression: str, result: Any) -> None:
    assert safe_eval(expression) == result


def test_safe_eval_should_not_allow_imports() -> None:
    with pytest.raises(SyntaxError):
        safe_eval("import os")


@pytest.mark.parametrize(
    ("expression"),
    [
        "os",
        "os.path",
        "os.path.join",
        "exec('print(1)')",
        "__import__('os')",
        "open('test.txt', 'w')",
    ],
)
def test_safe_eval_should_not_allow_builtin_names(expression: str) -> None:
    with pytest.raises(NameError):
        safe_eval(expression)


@pytest.mark.parametrize(
    ("expression", "result"),
    [("'PATH' in environ", True), (r"bool(re.match('\\d+', '1234'))", True)],
)
def test_safe_eval_simple_should_support_custom_globals(expression: str, result: Any) -> None:
    assert safe_eval(expression, {"environ": dict(os.environ), "re": re}) == result


def test_safe_eval_should_not_support_del() -> None:
    with pytest.raises(SyntaxError):
        safe_eval("del environ['PATH']", {"environ": os.environ, "re": re})
