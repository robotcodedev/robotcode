from typing import Any

from robot.api import logger


class alibrary:  # noqa: N801
    def __init__(self, a_param: Any = None) -> None:
        self.a_param = a_param

    def a_library_keyword(self) -> Any:
        logger.info("hello from a_library")
        return self.a_param

    def a_library_keywords_with_args(self, i: int, b: bool) -> Any:
        print(i)
        print(b)
        return (i, b)
