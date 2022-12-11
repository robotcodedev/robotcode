import dataclasses
import re
from pathlib import Path
from typing import Any, Generator, Tuple, Union

import pytest

TEST_EXPRESSION_LINE = re.compile(r"^\#\s*(?P<todo>TODO)?\s*(?P<position>\^+)\s+(?P<name>.*)")


@dataclasses.dataclass()
class GeneratedTestData:
    name: str
    line: int
    character: int


def generate_tests_from_source_document(
    path: Path,
) -> Generator[Union[Tuple[Path, GeneratedTestData], Any], None, None]:

    current_line = 0
    for line, text in enumerate(path.read_text().splitlines()):

        match = TEST_EXPRESSION_LINE.match(text)
        if match:
            name = match.group("name").strip()
            start, end = match.span("position")
            skip = match.group("todo")
            if name:
                if skip:
                    yield pytest.param(
                        path,
                        GeneratedTestData(name, current_line, start),
                        marks=pytest.mark.skip(reason="TODO"),
                    )
                else:
                    if end - start == 1:
                        yield path, GeneratedTestData(name, current_line, start)
                    else:
                        yield path, GeneratedTestData(name, current_line, start)
                        if end - start > 2:
                            yield path, GeneratedTestData(name, current_line, int(start + (end - start) / 2))

                        yield path, GeneratedTestData(name, current_line, end - 1)
        else:
            current_line = line


def generate_test_id(params: Any) -> Any:
    if isinstance(params, GeneratedTestData):
        return f"{params.line:03}-{params.character:03}-{params.name}"
    if dataclasses.is_dataclass(params):
        return repr(params)
    if isinstance(params, Path):
        return params.name

    return params
