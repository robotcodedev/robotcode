import asyncio
from typing import Any, Dict, List, Optional, cast

import pytest

from robotcode.core.lsp.types import MessageActionItem
from robotcode.core.utils.dataclasses import as_dict, as_json
from robotcode.jsonrpc2.protocol import (
    JsonRPCError,
    JsonRPCErrorObject,
    JsonRPCErrors,
    JsonRPCMessage,
    JsonRPCProtocol,
    JsonRPCRequest,
    JsonRPCResponse,
)
from robotcode.jsonrpc2.server import JsonRPCServer


class DummyJsonRPCProtocol(JsonRPCProtocol):
    def __init__(self, server: Optional[JsonRPCServer["DummyJsonRPCProtocol"]]):
        super().__init__()
        self.handled_messages: List[JsonRPCMessage] = []
        self.sended_message: Optional[JsonRPCMessage] = None

    async def handle_message(self, message: JsonRPCMessage) -> None:
        self.handled_messages.append(message)
        await super().handle_message(message)

    def send_message(self, message: JsonRPCMessage) -> None:
        self.sended_message = message

    async def data_received_async(self, data: bytes) -> None:
        self.data_received(data)
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_receive_a_request_message_should_work() -> None:
    protocol = DummyJsonRPCProtocol(None)

    message = JsonRPCRequest(id=1, method="doSomething", params={})

    json_message = as_json(message).encode("utf-8")
    header = f"Content-Length: {len(json_message)}\r\n\r\n".encode("ascii")
    data = header + json_message

    await protocol.data_received_async(data)

    assert protocol.handled_messages == [message]


@pytest.mark.asyncio
async def test_receive_a_request_message_should_work_with_string_id() -> None:
    protocol = DummyJsonRPCProtocol(None)

    message = JsonRPCRequest(id="this is an id", method="doSomething", params={})

    json_message = as_json(message).encode("utf-8")
    header = f"Content-Length: {len(json_message)}\r\n\r\n".encode("ascii")
    data = header + json_message

    await protocol.data_received_async(data)

    assert protocol.handled_messages == [message]


@pytest.mark.asyncio
async def test_receive_a_batch_request_should_work() -> None:
    protocol = DummyJsonRPCProtocol(None)

    message = [
        JsonRPCRequest(id=1, method="doSomething", params={}),
        JsonRPCRequest(id=2, method="doSomething", params={}),
        JsonRPCRequest(id=3, method="doSomething", params={}),
    ]

    json_message = as_json(message).encode("utf-8")
    header = f"Content-Length: {len(json_message)}\r\n\r\n".encode("ascii")
    data = header + json_message

    await protocol.data_received_async(data)

    assert protocol.handled_messages == message


@pytest.mark.asyncio
async def test_receive_invalid_jsonmessage_should_throw_send_an_error() -> None:
    protocol = DummyJsonRPCProtocol(None)

    json_message = b"{"
    header = f"Content-Length: {len(json_message)}\r\n\r\n".encode("ascii")
    data = header + json_message

    await protocol.data_received_async(data)
    assert isinstance(protocol.sended_message, JsonRPCError)
    assert protocol.sended_message.error.code == JsonRPCErrors.PARSE_ERROR


@pytest.mark.asyncio
async def test_receive_a_request_with_invalid_protocol_version_should_send_an_error() -> None:
    protocol = DummyJsonRPCProtocol(None)

    message = JsonRPCRequest(id=1, method="doSomething", params={})
    message.jsonrpc = "1.0"

    json_message = as_json(message).encode("utf-8")
    header = f"Content-Length: {len(json_message)}\r\n\r\n".encode("ascii")
    data = header + json_message
    await protocol.data_received_async(data)
    assert isinstance(protocol.sended_message, JsonRPCError)
    assert protocol.sended_message.error.code == JsonRPCErrors.PARSE_ERROR


@pytest.mark.asyncio
async def test_receive_an_error_should_work() -> None:
    protocol = DummyJsonRPCProtocol(None)

    message = JsonRPCError(
        id=1,
        result=None,
        error=JsonRPCErrorObject(code=1, message="test", data="this is the data"),
    )

    json_message = as_json(message).encode("utf-8")
    header = f"Content-Length: {len(json_message)}\r\n\r\n".encode("ascii")
    data = header + json_message
    await protocol.data_received_async(data)
    assert protocol.handled_messages == [message]


@pytest.mark.asyncio
async def test_receive_response_should_work() -> None:
    protocol = DummyJsonRPCProtocol(None)

    r = protocol.send_request("dummy/method", ["dummy", "data"], list)

    message = JsonRPCResponse(
        id=cast(JsonRPCRequest, protocol.sended_message).id,
        result=["dummy", "data"],
    )
    json_message = as_json(message).encode("utf-8")
    header = f"Content-Length: {len(json_message)}\r\n\r\n".encode("ascii")
    data = header + json_message
    await protocol.data_received_async(data)

    a = r.result(10)

    assert a == ["dummy", "data"]


@pytest.mark.asyncio
async def test_receive_invalid_id_in_response_should_send_an_error() -> None:
    protocol = DummyJsonRPCProtocol(None)

    message = JsonRPCResponse(id=1, result=["dummy", "data"])

    json_message = as_json(message).encode("utf-8")
    header = f"Content-Length: {len(json_message)}\r\n\r\n".encode("ascii")
    data = header + json_message
    await protocol.data_received_async(data)
    assert protocol.handled_messages == [message]
    assert isinstance(protocol.sended_message, JsonRPCError)


@pytest.mark.asyncio
async def test_send_request_receive_response_should_work_without_param_type_work() -> None:
    protocol = DummyJsonRPCProtocol(None)

    r: Any = protocol.send_request("dummy/method", ["dummy", "data"])

    message = JsonRPCResponse(
        id=cast(JsonRPCRequest, protocol.sended_message).id,
        result=MessageActionItem(title="hi there"),
    )
    json_message = as_json(message).encode("utf-8")
    header = f"Content-Length: {len(json_message)}\r\n\r\n".encode("ascii")
    data = header + json_message
    await protocol.data_received_async(data)

    a = r.result(10)

    assert isinstance(a, dict)
    assert a == {"title": "hi there"}


@pytest.mark.asyncio
async def test_receive_response_should_work_with_dataclass() -> None:
    protocol = DummyJsonRPCProtocol(None)

    r = protocol.send_request("dummy/method", ["dummy", "data"], MessageActionItem)

    message = JsonRPCResponse(
        id=cast(JsonRPCRequest, protocol.sended_message).id,
        result=MessageActionItem(title="hi there"),
    )
    json_message = as_json(message).encode("utf-8")
    header = f"Content-Length: {len(json_message)}\r\n\r\n".encode("ascii")
    data = header + json_message
    await protocol.data_received_async(data)

    a = r.result(10)

    assert a == MessageActionItem(title="hi there")


@pytest.mark.asyncio
async def test_receive_response_should_work_with_generic_list() -> None:
    protocol = DummyJsonRPCProtocol(None)

    r = protocol.send_request("dummy/method", ["dummy", "data"], List[MessageActionItem])

    message = JsonRPCResponse(
        id=cast(JsonRPCRequest, protocol.sended_message).id,
        result=[MessageActionItem(title="hi there")],
    )
    json_message = as_json(message).encode("utf-8")
    header = f"Content-Length: {len(json_message)}\r\n\r\n".encode("ascii")
    data = header + json_message
    await protocol.data_received_async(data)

    a = r.result(10)

    assert a == [MessageActionItem(title="hi there")]


@pytest.mark.asyncio
async def test_receive_response_with_generic_dict_should_return_unchanged() -> None:
    protocol = DummyJsonRPCProtocol(None)

    r = protocol.send_request("dummy/method", ["dummy", "data"], List[Dict[str, Any]])

    message = JsonRPCResponse(
        id=cast(JsonRPCRequest, protocol.sended_message).id,
        result=[MessageActionItem(title="hi there")],
    )
    json_message = as_json(message).encode("utf-8")
    header = f"Content-Length: {len(json_message)}\r\n\r\n".encode("ascii")
    data = header + json_message
    await protocol.data_received_async(data)

    a = r.result(10)

    assert a == [as_dict(MessageActionItem(title="hi there"))]
