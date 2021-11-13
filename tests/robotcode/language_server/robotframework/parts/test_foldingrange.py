import re
from pathlib import Path
from typing import Any, Generator, Iterable, Tuple, Union

import pytest

from robotcode.language_server.common.lsp_types import (
    ClientCapabilities,
    FoldingRange,
    FoldingRangeClientCapabilities,
    TextDocumentClientCapabilities,
)
from robotcode.language_server.common.text_document import TextDocument
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)

from ..tools import (
    GeneratedTestData,
    generate_test_id,
    generate_tests_from_source_document,
)


def prepend_protocol_data(
    protocol: Iterable[Any], data: Iterable[Union[Tuple[Any, Path, GeneratedTestData], Any]]
) -> Generator[Union[Tuple[Any, Path, GeneratedTestData], Any], None, None]:
    for p in protocol:
        for d in data:
            yield (p, *d)


@pytest.mark.parametrize(
    ("protocol", "test_document", "data"),
    prepend_protocol_data(
        [
            ClientCapabilities(
                text_document=TextDocumentClientCapabilities(
                    folding_range=FoldingRangeClientCapabilities(line_folding_only=True),
                )
            ),
            ClientCapabilities(
                text_document=TextDocumentClientCapabilities(
                    folding_range=FoldingRangeClientCapabilities(line_folding_only=False),
                )
            ),
        ],
        list(generate_tests_from_source_document(Path(Path(__file__).parent, "data/foldingrange.robot"))),
    ),
    indirect=["protocol", "test_document"],
    ids=generate_test_id,
)
@pytest.mark.asyncio
async def test_foldingrange(
    protocol: RobotLanguageServerProtocol,
    test_document: TextDocument,
    data: GeneratedTestData,
) -> None:

    result = await protocol.robot_folding_ranges.collect(protocol.robot_goto, test_document)

    assert bool(
        eval(
            data.expression,
            {
                "re": re,
                "FoldingRange": FoldingRange,
                "result": result,
                "line": data.line,
                "character": data.character,
            },
        )
    ), f"{data.expression} -> {repr(result)}"
