import sys
from typing import Optional

from robotcode.jsonrpc2.protocol import JsonRPCProtocol, rpc_method

from .interpreter import ExecutionResult, Interpreter


class ReplServerProtocol(JsonRPCProtocol):
    def __init__(self, interpreter: Interpreter):
        super().__init__()
        self.interpreter = interpreter
        self._is_shutdown = False

    @rpc_method(name="initialize", threaded=True)
    def initialize(self, message: str) -> str:
        return "yeah initialized " + message

    @rpc_method(name="executeCell", threaded=True)
    def execute_cell(self, source: str, language_id: str) -> Optional[ExecutionResult]:
        return self.interpreter.execute(source)

    @rpc_method(name="interrupt", threaded=True)
    def interrupt(self) -> None:
        self.interpreter.interrupt()

    @rpc_method(name="shutdown", threaded=True)
    def shutdown(self) -> None:
        try:
            self.interpreter.shutdown()
        finally:
            self._is_shutdown = True

    @rpc_method(name="exit", threaded=True)
    def exit(self) -> None:
        sys.exit(0 if self._is_shutdown else 1)
