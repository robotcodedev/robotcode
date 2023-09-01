from typing import Any, Dict, Iterator, List, Protocol, Set, runtime_checkable


@runtime_checkable
class Languages(Protocol):
    languages: List[Any]
    headers: Dict[str, str]
    settings: Dict[str, str]
    bdd_prefixes: Set[str]
    true_strings: Set[str]
    false_strings: Set[str]

    def add_language(self, name: str) -> None:
        ...

    def __iter__(self) -> Iterator[Any]:
        ...
