from typing import Any


class LibraryWithErrors:
    def __init__(self, throw_error: bool = False) -> None:
        if throw_error:
            raise Exception("This is an error in the constructor")

    def a_library_keyword(self) -> Any:
        raise Exception("This is an error in a keyword")
