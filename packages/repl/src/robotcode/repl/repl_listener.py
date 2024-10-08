from typing import Any, ClassVar, Dict, Optional

from robotcode.plugin import Application

from .interpreter import Interpreter


class ReplListener:
    ROBOT_LISTENER_API_VERSION = 2
    instance: ClassVar["ReplListener"]

    def __init__(self, app: Application, interpreter: Optional[Interpreter] = None) -> None:
        ReplListener.instance = self
        self.app = app
        self.interpreter = interpreter or Interpreter(app)

    def start_keyword(self, name: str, _attributes: Dict[str, Any]) -> None:
        if name != "robotcode.repl.Repl.Repl":
            return

        self.interpreter.run()

    def log_message(self, message: Dict[str, Any]) -> None:
        self.interpreter.log_message(message["message"], message["level"], message["html"], message.get("timestamp"))

    def message(self, message: Dict[str, Any]) -> None:
        self.interpreter.message(message["message"], message["level"], message["html"], message.get("timestamp"))
