from enum import IntEnum
from typing import Any, Dict, List, Optional, Union

# flake8: noqa: N815


class LSPErrCode(IntEnum):
    # Defined by JSON RPC
    ParseError = -32700
    InvalidRequest = -32600
    MethodNotFound = -32601
    InvalidParams = -32602
    InternalError = -32603
    ServerErrorStart = -32099
    ServerErrorEnd = -32000
    ServerNotInitialized = -32002
    UnknownError = -32001

    # Defined by the protocol.
    RequestCancelled = -32800
    ContentModified = -32801


def to_dict(v) -> Any:
    if isinstance(v, LSPObject):
        return {k: to_dict(_v) for k, _v in v.__dict__.items() if _v is not None}
    elif isinstance(v, dict):
        return {k: to_dict(_v) for k, _v in v.items()}
    elif isinstance(v, (list, tuple)):
        return [to_dict(_v) for _v in v]
    else:
        return v


class LSPObject:
    def to_dict(self) ->Any:
        return to_dict(self)


class TextDocumentSyncKind(IntEnum):
    _None = 0
    Full = 1
    Incremental = 2


class TextDocumentSyncOptions(LSPObject):
    openClose: Optional[bool]
    change: Optional[TextDocumentSyncKind]


class MessageType:
    Error = 1
    Warning = 2
    Info = 3
    Log = 4


class ConfigurationItem(LSPObject):
    def __init__(self, section: str, scope_uri: Optional[str]):
        self.section = section
        self.scopeUri = scope_uri


class ConfigurationParams(LSPObject):
    def __init__(self, *items: ConfigurationItem):
        self.items = items
