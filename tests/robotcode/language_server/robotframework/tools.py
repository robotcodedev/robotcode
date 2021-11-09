import dataclasses
import re
from pathlib import Path
from typing import Any, Generator, NamedTuple, Tuple, Union

import pytest

TEST_EXPRESSION_LINE = re.compile(
    r"^\#\s*(?P<todo>TODO)?\s*(?P<position>\^+)\s*(?P<name>[^:]+)\s*:\s*(?P<expression>.+)"
)


class GeneratedTestData(NamedTuple):
    name: str
    line: int
    character: int
    expression: str


def generate_tests_from_source_document(
    path: Path,
) -> Generator[Union[Tuple[Path, GeneratedTestData], Any], None, None]:

    current_line = 0
    for line, text in enumerate(path.read_text().splitlines()):

        match = TEST_EXPRESSION_LINE.match(text)
        if match:
            name = match.group("name").strip()
            start, end = match.span("position")
            expression = match.group("expression").strip()
            skip = match.group("todo")
            if name and expression:
                if skip:
                    yield pytest.param(
                        path,
                        GeneratedTestData(name, current_line, start, expression),
                        marks=pytest.mark.skip(reason="TODO"),
                    )
                else:
                    if end - start == 1:
                        yield path, GeneratedTestData(name, current_line, start, expression)
                    else:
                        yield path, GeneratedTestData(name, current_line, start, expression)
                        if end - start > 2:
                            yield path, GeneratedTestData(
                                name, current_line, int(start + (end - start) / 2), expression
                            )

                        yield path, GeneratedTestData(name, current_line, end - 1, expression)
        else:
            current_line = line


def generate_test_id(params: Any) -> Any:
    if isinstance(params, GeneratedTestData):
        return f"{params.line}-{params.character}-{params.name}"
    if dataclasses.is_dataclass(params):
        return repr(params)
    if isinstance(params, Path):
        return params.name

    return params
