"""Tests for the code blocks of Markdown files that Robot Framework executes."""

from pathlib import Path
from typing import List, Optional, Tuple

import pytest

from robotcode.robot.document_formats import MARKDOWN_SUPPORTED
from robotcode.robot.utils.markdown_blocks import (
    RobotBlock,
    find_block,
    find_robot_blocks,
    indent_for_block,
    read_markdown_data,
)

BACKTICKS = """\
# Title

```robot
*** Test Cases ***
First
    Log    one
```

Some prose.
"""

TILDES_LONGER_CLOSE = """\
~~~ Robot
*** Test Cases ***
First
    Log    one
~~~~~
"""

INFO_STRING = """\
```RobotFramework extra words
*** Test Cases ***
```
```robot{.class}
*** Keywords ***
```
"""

INDENTED = """\
1. A list item

    ```robotframework
    *** Test Cases ***
    Indented Test
        Log    one
    ```
"""

UNCLOSED = """\
Text
```robot
*** Test Cases ***
First
    Log    one
"""

EMPTY_LINES_ONLY = """\
```robot


```
"""

OTHER_LANGUAGES = """\
```python
print("*** Test Cases ***")
```

~~~
*** Test Cases ***
~~~

```robot
*** Keywords ***
```
"""

ROBOT_FENCE_IN_PYTHON_FENCE = """\
````python
```robot
*** Test Cases ***
```
````
"""

SHORTER_CLOSE_AND_OTHER_CHARACTER = """\
````robot
*** Test Cases ***
```
~~~~
First
````
"""

FIXTURES: List[Tuple[str, str, List[RobotBlock]]] = [
    ("backticks", BACKTICKS, [RobotBlock(2, 6)]),
    ("tildes with a longer closing fence", TILDES_LONGER_CLOSE, [RobotBlock(0, 4)]),
    ("info string with letter case and further words", INFO_STRING, [RobotBlock(0, 2)]),
    ("indented fences", INDENTED, [RobotBlock(2, 6, 4)]),
    ("unclosed block", UNCLOSED, [RobotBlock(1, None)]),
    ("block with only empty lines", EMPTY_LINES_ONLY, [RobotBlock(0, 3)]),
    ("other-language fences", OTHER_LANGUAGES, [RobotBlock(8, 10)]),
    ("robot fence inside a python fence", ROBOT_FENCE_IN_PYTHON_FENCE, [RobotBlock(1, 3)]),
    ("shorter closing fence and other character", SHORTER_CLOSE_AND_OTHER_CHARACTER, [RobotBlock(0, 5)]),
]


@pytest.mark.parametrize(("text", "expected"), [(t, e) for _, t, e in FIXTURES], ids=[n for n, _, _ in FIXTURES])
def test_finds_the_blocks_robot_framework_executes(text: str, expected: List[RobotBlock]) -> None:
    assert find_robot_blocks(text) == expected


@pytest.mark.parametrize(("text", "expected"), [(t, e) for _, t, e in FIXTURES], ids=[n for n, _, _ in FIXTURES])
def test_finds_the_same_blocks_in_a_file_with_crlf_line_endings(
    tmp_path: Path, text: str, expected: List[RobotBlock]
) -> None:
    path = tmp_path / "suite.robot.md"
    path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))

    assert find_robot_blocks(path.read_bytes().decode("utf-8")) == expected


@pytest.mark.parametrize(
    ("line", "expected"),
    [(1, None), (2, None), (3, RobotBlock(2, 6)), (5, RobotBlock(2, 6)), (6, None), (8, None)],
)
def test_a_line_belongs_to_a_block_only_between_its_fences(line: int, expected: Optional[RobotBlock]) -> None:
    assert find_block(find_robot_blocks(BACKTICKS), line) == expected


def test_an_unclosed_block_holds_every_line_after_its_fence() -> None:
    assert find_block(find_robot_blocks(UNCLOSED), 100) == RobotBlock(1, None)


def test_the_empty_lines_of_a_block_belong_to_it() -> None:
    blocks = find_robot_blocks(EMPTY_LINES_ONLY)

    assert find_block(blocks, 1) == RobotBlock(0, 3)
    assert find_block(blocks, 2) == RobotBlock(0, 3)


@pytest.mark.skipif(not MARKDOWN_SUPPORTED, reason="needs the Markdown parser of Robot Framework 7.5.1")
@pytest.mark.parametrize("crlf", [False, True], ids=["lf", "crlf"])
@pytest.mark.parametrize("text", [t for _, t, _ in FIXTURES], ids=[n for n, _, _ in FIXTURES])
def test_the_blocks_hold_exactly_the_lines_robot_framework_keeps(text: str, crlf: bool) -> None:
    if crlf:
        text = text.replace("\n", "\r\n")

    data, offsets = read_markdown_data(text)
    blocks = find_robot_blocks(text)
    file_lines = text.replace("\r\n", "\n").splitlines(keepends=True)
    data_lines = data.splitlines(keepends=True)

    assert len(data_lines) == len(file_lines)
    for index, (file_line, data_line) in enumerate(zip(file_lines, data_lines)):
        if find_block(blocks, index) is None:
            assert data_line == "\n", f"line {index + 1} is kept by Robot Framework but lies in no block"
        else:
            assert data_line == file_line[offsets.get(index + 1, 0) :], f"line {index + 1} differs"


@pytest.mark.skipif(not MARKDOWN_SUPPORTED, reason="needs the Markdown parser of Robot Framework 7.5.1")
def test_the_offsets_are_the_removed_indentation() -> None:
    _, offsets = read_markdown_data(INDENTED)

    assert offsets == {4: 4, 5: 4, 6: 4}


def test_placed_code_gets_the_indentation_of_the_block() -> None:
    (block,) = find_robot_blocks(INDENTED)

    assert indent_for_block("\nNew Keyword\n    Log    one\n", block) == "\n    New Keyword\n        Log    one\n"
    assert indent_for_block("New Keyword\n", None) == "New Keyword\n"
