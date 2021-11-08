import re
from pathlib import Path

import pytest

from robotcode.language_server.common.lsp_types import FoldingRange
from robotcode.language_server.common.text_document import TextDocument
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)

from ..tools import (
    GeneratedTestData,
    generate_test_id,
    generate_tests_from_source_document,
)


@pytest.mark.parametrize(
    ("test_document", "data"),
    generate_tests_from_source_document(Path(Path(__file__).parent, "data/foldingrange.robot")),
    indirect=["test_document"],
    ids=generate_test_id,
)
@pytest.mark.asyncio
async def test_foldingrange(
    protocol: RobotLanguageServerProtocol,
    test_document: TextDocument,
    data: GeneratedTestData,
) -> None:

    result = await protocol._robot_folding_ranges.collect(protocol._robot_goto, test_document)

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
