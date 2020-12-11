from enum import IntEnum
from typing import Optional

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
    UnknownErrorCode = -32001

    # Defined by the protocol.
    RequestCancelled = -32800
    ContentModified = -32801


def to_dict(v):
    if isinstance(v, LSPObject):
        return {
            k: to_dict(_v)
            for k, _v in v.__dict__.items() if _v is not None
        }
    elif isinstance(v, dict):
        return {
            k: to_dict(_v)
            for k, _v in v.items()
        }
    elif isinstance(v, list):
        return [
            to_dict(_v) for _v in v
        ]
    else:
        return v


class LSPObject:
    def to_dict(self):
        return to_dict(self)


class TextDocumentSyncKind(IntEnum):
    _None = 0
    Full = 1
    Incremental = 2


class TextDocumentSyncOptions(LSPObject):
    openClose: Optional[bool]
    change: Optional[TextDocumentSyncKind]


class MessageType(IntEnum):
    Error = 1
    Warning = 2
    Info = 3
    Log = 4


