from typing import Any, Dict

from .debugger import Debugger


class ListenerV2:
    ROBOT_LISTENER_API_VERSION = "2"

    def __init__(self, no_debug: bool = False) -> None:
        self.no_debug = no_debug
        self.debug = not no_debug

    def start_suite(self, name: str, attributes: Dict[str, Any]) -> None:
        Debugger.instance().start_output_group(name, attributes, "SUITE")

        if self.debug:
            Debugger.instance().start_suite(name, attributes)

    def end_suite(self, name: str, attributes: Dict[str, Any]) -> None:
        if self.debug:
            Debugger.instance().end_suite(name, attributes)

        Debugger.instance().end_output_group(name, attributes)

    def start_test(self, name: str, attributes: Dict[str, Any]) -> None:
        Debugger.instance().start_output_group(name, attributes, "TEST")

        if self.debug:
            Debugger.instance().start_test(name, attributes)

    def end_test(self, name: str, attributes: Dict[str, Any]) -> None:
        if self.debug:
            Debugger.instance().end_test(name, attributes)

        Debugger.instance().end_output_group(name, attributes)

    def start_keyword(self, name: str, attributes: Dict[str, Any]) -> None:
        Debugger.instance().start_output_group(
            f"{name}({', '.join(repr(v) for v in attributes.get('args', []))})",
            attributes,
            attributes.get("type", None),
        )

        if self.debug:
            Debugger.instance().start_keyword(name, attributes)

    def end_keyword(self, name: str, attributes: Dict[str, Any]) -> None:
        if self.debug:
            Debugger.instance().end_keyword(name, attributes)

        Debugger.instance().end_output_group(name, attributes)

    def log_message(self, message: Dict[str, Any]) -> None:
        Debugger.instance().log_message(message)

    def message(self, message: Dict[str, Any]) -> None:
        Debugger.instance().message(message)

    def library_import(self, name: str, attributes: Dict[str, Any]) -> None:
        pass

    def resource_import(self, name: str, attributes: Dict[str, Any]) -> None:
        pass

    def variables_import(self, name: str, attributes: Dict[str, Any]) -> None:
        pass

    def output_file(self, path: str) -> None:
        Debugger.instance().robot_output_file = path

    def log_file(self, path: str) -> None:
        Debugger.instance().robot_log_file = path

    def report_file(self, path: str) -> None:
        Debugger.instance().robot_report_file = path

    def xunit_file(self, path: str) -> None:
        pass

    def debug_file(self, path: str) -> None:
        pass

    def close(self) -> None:
        pass
