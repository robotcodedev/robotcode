from enum import Enum, unique
from typing import NamedTuple, Sequence, Union


@unique
class ServerMode(str, Enum):
    STDIO = "stdio"
    TCP = "tcp"
    SOCKET = "socket"
    PIPE = "pipe"
    PIPE_SERVER = "pipe-server"

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return repr(self.value)


class TcpParams(NamedTuple):
    host: Union[str, Sequence[str], None] = None
    port: int = 0
