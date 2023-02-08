import asyncio
import dataclasses
from pathlib import Path

import pytest
import yaml

from robotcode.language_server.robotframework.protocol import (
    RobotLanguageServerProtocol,
)
from robotcode.utils.async_tools import run_coroutine_in_thread

from .pytest_regtestex import RegTestFixtureEx


@pytest.mark.usefixtures("protocol")
@pytest.mark.asyncio()
async def test_workspace_discovery(
    regtest: RegTestFixtureEx,
    protocol: RobotLanguageServerProtocol,
) -> None:
    from robotcode.language_server.robotframework.parts.discovering import TestItem

    def split(item: TestItem) -> TestItem:
        return dataclasses.replace(
            item,
            id=item.id.split(";", 1)[1] if ";" in item.id else item.id,
            uri="/".join(item.uri.split("/")[-2:]) if item.uri else item.uri,
            children=sorted(
                [split(v) for v in item.children],
                key=lambda v: (
                    v.uri,
                    v.range.start if v.range is not None else None,
                    v.range.end if v.range is not None else None,
                ),
            )
            if item.children
            else item.children,
        )

    result = await asyncio.wait_for(
        run_coroutine_in_thread(
            protocol.robot_discovering.get_tests_from_workspace, Path(Path(__file__).parent, "data").as_uri()
        ),
        120,
    )
    regtest.write(
        yaml.dump(
            {
                "result": sorted(
                    (split(v) for v in result),
                    key=lambda v: (v.uri, v.range.start, v.range.end) if v.range is not None else (v.uri, None, None),
                )
                if result
                else result,
            }
        )
    )
