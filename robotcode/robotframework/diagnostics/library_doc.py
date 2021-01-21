import os
from dataclasses import dataclass, field
from typing import (
    AbstractSet,
    Any,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    ValuesView,
    cast,
)

from ...language_server.types import Range, Position

__all__ = ["KeywordDoc", "LibraryDoc", "is_library_by_path", "get_library_doc", "find_file"]


@dataclass
class KeywordDoc:
    def __init__(
        self,
        parent: "LibraryDoc",
        name: str = "",
        args: Tuple[Any, ...] = (),
        doc: str = "",
        tags: Tuple[str, ...] = (),
        source: Optional[str] = None,
        line_no: int = -1,
    ) -> None:
        self.parent = parent
        self.name = name
        self.args = args
        self.doc = doc
        self.tags = tags
        self.source = source
        self.line_no = line_no

    parent: "LibraryDoc"
    name: str = ""
    args: Tuple[Any, ...] = ()
    doc: str = ""
    tags: Tuple[str, ...] = ()
    source: Optional[str] = None
    line_no: int = -1

    def __str__(self) -> str:
        return f"{self.name}({', '.join(str(arg) for arg in self.args)})"

    def range(self) -> Range:
        return Range(
            start=Position(line=self.line_no - 1 if self.line_no >= 0 else 0, character=0),
            end=Position(line=self.line_no - 1 if self.line_no >= 0 else 0, character=0),
        )


class KeywordMatcher:
    def __init__(self, name: str) -> None:
        from robot.running.arguments.embedded import EmbeddedArguments
        from robot.utils.normalizing import normalize

        self.name = name
        self.normalized_name = str(normalize(name, "_"))
        self.embedded_arguments = EmbeddedArguments(name)

    def __eq__(self, o: object) -> bool:
        from robot.utils.normalizing import normalize

        if not isinstance(o, str):
            return False

        if self.embedded_arguments:
            return self.embedded_arguments.name.match(o) is not None

        return self.normalized_name == str(normalize(o, "_"))

    def __hash__(self) -> int:
        return hash(self.name)

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(name={repr(self.name)}"
            f", normalized_name={repr(self.normalized_name)}"
            f"{f', embedded=True' if self.embedded_arguments else ''})"
        )


class KeywordStore(Mapping[str, KeywordDoc]):
    def __init__(self, items: Mapping[str, KeywordDoc]) -> None:

        self._items = {KeywordMatcher(k): v for k, v in items.items()}

    def __getitem__(self, key: str) -> KeywordDoc:
        for k, v in self._items.items():
            if k == key:
                return v

        raise KeyError()

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[str]:
        return iter(e.name for e in self._items)

    def __contains__(self, __x: object) -> bool:
        return any(k == __x for k in self._items.keys())

    def items(self) -> AbstractSet[Tuple[str, KeywordDoc]]:
        return {(k.name, v) for k, v in self._items.items()}

    def keys(self) -> AbstractSet[str]:
        return {k.name for k in self._items.keys()}

    def values(self) -> ValuesView[KeywordDoc]:
        return self._items.values()


@dataclass
class Error:
    message: str
    type_name: str


@dataclass
class LibraryDoc:
    name: str = ""
    doc: str = ""
    version: str = ""
    type: str = "LIBRARY"
    scope: str = "TEST"
    named_args: bool = True
    doc_format: str = "ROBOT"
    source: Optional[str] = None
    line_no: int = -1
    inits: KeywordStore = field(default_factory=lambda: KeywordStore({}))
    keywords: KeywordStore = field(default_factory=lambda: KeywordStore({}))

    errors: Optional[Sequence[Error]] = None

    def __str__(self) -> str:
        return self.name

    def range(self) -> Range:
        return Range(
            start=Position(line=self.line_no - 1 if self.line_no >= 0 else 0, character=0),
            end=Position(line=self.line_no - 1 if self.line_no >= 0 else 0, character=0),
        )


def is_library_by_path(path: str) -> bool:
    return path.lower().endswith((".py", ".java", ".class", "/", os.sep))


def _update_sys_path(working_dir: str = ".", pythonpath: Optional[List[str]] = None) -> None:
    import sys
    from pathlib import Path

    file = Path(__file__).resolve()
    top = file.parents[3]
    for p in filter(lambda v: Path(v).is_relative_to(top), sys.path.copy()):
        sys.path.remove(p)
    wd = Path(working_dir)

    os.chdir(wd)

    if pythonpath is not None:
        for p in pythonpath:
            if p in sys.path:
                sys.path.remove(p)
            sys.path.insert(0, str(Path(p).absolute()))


def get_library_doc(
    name: str,
    args: Optional[Tuple[Any, ...]] = None,
    working_dir: str = ".",
    base_dir: str = ".",
    pythonpath: Optional[List[str]] = None,
) -> LibraryDoc:

    from robot.libdocpkg.robotbuilder import KeywordDocBuilder
    from robot.running.testlibraries import TestLibrary
    from robot.utils.robotpath import find_file as robot_find_file

    _update_sys_path(working_dir, pythonpath)

    if is_library_by_path(name):
        name = robot_find_file(name, base_dir or ".", "Library")

    lib = TestLibrary(name, args, create_handlers=False)
    libdoc = LibraryDoc(
        name=str(lib.name),
        doc=str(lib.doc),
        version=str(lib.version),
        scope=str(lib.scope),
        doc_format=str(lib.doc_format),
        source=lib.source,
        line_no=lib.lineno,
    )

    libdoc.inits = KeywordStore(
        {
            kw.name: KeywordDoc(
                libdoc,
                name=kw.name,
                args=tuple(kw.args),
                doc=kw.doc,
                tags=tuple(kw.tags),
                source=kw.source,
                line_no=kw.lineno,
            )
            for kw in [KeywordDocBuilder().build_keyword(lib.init)]
        }
    )

    try:
        lib.create_handlers()

        libdoc.keywords = KeywordStore(
            {
                kw.name: KeywordDoc(
                    libdoc,
                    name=kw.name,
                    args=tuple(kw.args),
                    doc=kw.doc,
                    tags=tuple(kw.tags),
                    source=kw.source,
                    line_no=kw.lineno,
                )
                for kw in KeywordDocBuilder().build_keywords(lib)
            }
        )
    except (SystemExit, KeyboardInterrupt):
        raise
    except BaseException as e:
        libdoc.errors = [Error(str(e), type(e).__qualname__)]

    return libdoc


def find_file(
    name: str,
    working_dir: str = ".",
    base_dir: str = ".",
    pythonpath: Optional[List[str]] = None,
    file_type: str = "Resource",
) -> str:
    from robot.utils.robotpath import find_file as robot_find_file

    _update_sys_path(working_dir, pythonpath)

    return cast(str, robot_find_file(name, base_dir or ".", file_type))
