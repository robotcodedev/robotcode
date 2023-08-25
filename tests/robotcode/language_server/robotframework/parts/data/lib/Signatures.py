from enum import Enum
from typing import Any, List, Optional, Tuple


class TestEnum(Enum):
    """This is a test enum."""
    A = 1
    B = 2
    C = 3

class Signatures:
    """This class is used to test the signature generation."""

    def __init__(self, l: Optional[List[int]] = None, s: str = "Hello World!", i: int = 0, b: bool = False) -> None:
        """This is the constructor of the class."""
        self.l = l

    def do_something(self, i: int, b: bool, l: Optional[List[int]] = None) -> Tuple[Any, ...]:
        """This is a method of the class."""
        return (self.l, i, b)

    def do_something_with_enum(self, i: int, b: bool, l: TestEnum = TestEnum.A) -> Tuple[Any, ...]:
        """This is a method of the class."""
        return (self.l, i, b)
