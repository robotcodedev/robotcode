import dataclasses
from typing import List, Union, cast

import pytest
import yaml

from robotcode.core.lsp.types import Location, SymbolInformation, WorkspaceSymbol
from robotcode.core.uri import Uri
from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)

from .pytest_regtestex import RegTestFixtureEx


@pytest.mark.parametrize(
    ("query"),
    ["", "first", "as"],
)
@pytest.mark.usefixtures("protocol")
def test(
    regtest: RegTestFixtureEx,
    protocol: RobotLanguageServerProtocol,
    query: str,
) -> None:
    result = protocol.robot_workspace_symbols.collect(protocol.robot_workspace_symbols, query=query)

    assert result is not None

    regtest.write(
        yaml.dump(
            {
                "result": [
                    dataclasses.replace(
                        v,
                        location=cast(
                            Location,
                            dataclasses.replace(v.location, uri=Uri(v.location.uri).to_path().name),
                        ),
                    )
                    for v in cast(
                        "Union[List[WorkspaceSymbol], List[SymbolInformation]]",
                        sorted(result, key=lambda v: (str(v.container_name), str(v.location.uri), v.name)),
                    )
                ],
            }
        )
    )
