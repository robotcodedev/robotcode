import json
import logging
from typing import cast

import pytest


from robotcode.server.jsonrpc2_server import (
    JsonRPCErrorMessage,
    JsonRPCErrorObject,
    JsonRPCErrors,
    JsonRPCMessage,
    JsonRPCProtocol,
    JsonRPCRequestMessage,
)


class DummyJsonRPCProtocol(JsonRPCProtocol):
    handled_message = None
    sended_message = None

    def handle_message(self, message: JsonRPCMessage):
        self.handled_message = message

    def send_data(self, message: JsonRPCMessage):
        self.sended_message = message


@pytest.fixture
def enable_log(caplog):
    caplog.set_level(logging.DEBUG)


def test_receive_a_request_message_should_work():
    protocol = DummyJsonRPCProtocol(None)

    message = JsonRPCRequestMessage(id=1, method="doSomething", params={})

    json_message = message.json().encode("utf-8")
    header = f"Content-Length: {len(json_message)}\r\n\r\n".encode("ascii")
    data = header + json_message
    protocol.data_received(data)
    assert protocol.handled_message == message


def test_receive_a_batch_request_should_work():
    protocol = DummyJsonRPCProtocol(None)

    message = [
        JsonRPCRequestMessage(id=1, method="doSomething", params={}).dict(),
        JsonRPCRequestMessage(id=2, method="doSomething", params={}).dict(),
        JsonRPCRequestMessage(id=3, method="doSomething", params={}).dict(),
    ]

    json_message = json.dumps(message).encode("utf-8")
    header = f"Content-Length: {len(json_message)}\r\n\r\n".encode("ascii")
    data = header + json_message
    protocol.data_received(data)
    assert protocol.handled_message == message


def test_receive_invalid_jsonmessage_should_throw_send_an_error():
    protocol = DummyJsonRPCProtocol(None)

    json_message = b"{"
    header = f"Content-Length: {len(json_message)}\r\n\r\n".encode("ascii")
    data = header + json_message

    protocol.data_received(data)
    assert (
        isinstance(protocol.sended_message, JsonRPCErrorMessage)
        and cast(JsonRPCErrorMessage, protocol.sended_message).error.code == JsonRPCErrors.PARSE_ERROR
    )


def test_receive_a_request_with_invalid_protocol_version_should_send_an_error():
    protocol = DummyJsonRPCProtocol(None)

    message = JsonRPCRequestMessage(id=1, method="doSomething", params={})
    message.jsonrpc = "1.0"

    json_message = message.json().encode("utf-8")
    header = f"Content-Length: {len(json_message)}\r\n\r\n".encode("ascii")
    data = header + json_message
    protocol.data_received(data)
    assert (
        isinstance(protocol.sended_message, JsonRPCErrorMessage)
        and cast(JsonRPCErrorMessage, protocol.sended_message).error.code == JsonRPCErrors.PARSE_ERROR
    )


def test_receive_an_error_should_work():
    protocol = DummyJsonRPCProtocol(None)

    message = JsonRPCErrorMessage(
        id=1, result=None, error=JsonRPCErrorObject(code=1, message="test", data="this is the data")
    )

    json_message = message.json().encode("utf-8")
    header = f"Content-Length: {len(json_message)}\r\n\r\n".encode("ascii")
    data = header + json_message
    protocol.data_received(data)
    assert protocol.handled_message == message
