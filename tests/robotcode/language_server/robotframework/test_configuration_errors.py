"""The language server shows the errors of the configuration it was started with, once the editor has connected."""

from typing import List, Tuple

import pytest

from robotcode.core.lsp.types import MessageType
from robotcode.language_server.robotframework.protocol import RobotLanguageServerProtocol
from robotcode.language_server.robotframework.server import RobotLanguageServer


def shown_messages(protocol: RobotLanguageServerProtocol, monkeypatch: pytest.MonkeyPatch) -> List[Tuple[str, int]]:
    shown: List[Tuple[str, int]] = []
    monkeypatch.setattr(protocol.window, "show_message", lambda message, type: shown.append((message, type)))
    return shown


def test_each_error_of_the_configuration_is_shown_as_an_error_after_initialized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol = RobotLanguageServerProtocol(RobotLanguageServer(), configuration_errors=["first", "second"])
    shown = shown_messages(protocol, monkeypatch)

    assert protocol.show_configuration_errors in protocol.on_initialized
    protocol.show_configuration_errors(protocol)

    assert shown == [("first", MessageType.ERROR), ("second", MessageType.ERROR)]


def test_a_configuration_without_errors_shows_no_message(monkeypatch: pytest.MonkeyPatch) -> None:
    protocol = RobotLanguageServerProtocol(RobotLanguageServer())
    shown = shown_messages(protocol, monkeypatch)

    protocol.show_configuration_errors(protocol)

    assert shown == []
