"""The language server creates its protocol parts with the first request, before it handles the initialize request.

A part therefore must not use anything in its constructor that exists only after the initialize request, such as
the workspace.
"""

from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol
from robotcode.language_server.robotframework.server import RobotLanguageServer


def test_the_parts_exist_before_the_initialize_request() -> None:
    protocol = RobotLanguageServerProtocol(RobotLanguageServer())

    assert protocol.registry.get_entry("initialize") is not None
