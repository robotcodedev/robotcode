from typing import Any, List, Optional, Tuple


class Signatures:
    """This class is used to test the signature generation."""

    def __init__(self, l: Optional[List[int]] = None, s: str = "Hello World!", i: int = 0, b: bool = False) -> None:
        """This is the constructor of the class."""
        self.l = l

    def do_something(self, i: int, b: bool, l: Optional[List[int]] = None) -> Tuple[Any, ...]:
        """This is a method of the class."""
        return (self.l, i, b)
