import re
from pathlib import Path
from typing import Any, Generator, Tuple, Union

import pytest

TEST_EXPRESSION_LINE = re.compile(
    r"^\#\s*(?P<todo>TODO)?\s*(?P<position>\^+)\s*(?P<name>[^:]+)\s*:\s*(?P<expression>.+)"
)


def generate_tests_from_source_document(
    path: str,
) -> Generator[Union[Tuple[str, str, int, int, str], Any], None, None]:
    file = Path(path).relative_to(Path(".").parent.absolute())

    current_line = 0
    for line, text in enumerate(file.read_text().splitlines()):

        match = TEST_EXPRESSION_LINE.match(text)
        if match:
            name = match.group("name").strip()
            start, end = match.span("position")
            expression = match.group("expression").strip()
            skip = match.group("todo")
            if name and expression:
                if skip:
                    yield pytest.param(
                        str(file), name, current_line, start, expression, marks=pytest.mark.skip(reason="TODO")
                    )
                else:
                    if end - start == 1:
                        yield str(file), name, current_line, start, expression
                    else:
                        yield str(file), name, current_line, start, expression
                        if end - start > 2:
                            yield str(file), name, current_line, int(start + (end - start) / 2), expression

                        yield str(file), name, current_line, end - 1, expression
        else:
            current_line = line
