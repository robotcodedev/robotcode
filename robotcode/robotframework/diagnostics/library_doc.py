import importlib
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import AbstractSet, Any, Iterator, List, Mapping, Optional, Sequence, Set, Tuple, ValuesView, cast

from ...language_server.types import Position, Range

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

    def to_markdown(self) -> str:
        result = "```python\n"

        result += f"def {self.name}({', '.join(self.args)})"

        result += "\n```"

        if self.doc:
            result += "\n"
            result += self.doc

        return result


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

    def to_markdown(self) -> str:
        result = ""

        if self.inits:
            result += "\n\n---\n".join(i.to_markdown() for i in self.inits.values())

        if self.doc:
            if result:
                result += "\n\n---\n"
            result += self.doc

        return result


def is_library_by_path(path: str) -> bool:
    return path.lower().endswith((".py", ".java", ".class", "/", os.sep))


def _update_sys_path(working_dir: str = ".", pythonpath: Optional[List[str]] = None) -> None:

    global _PRELOADED_MODULES

    if _PRELOADED_MODULES is None:
        _PRELOADED_MODULES = set(sys.modules.values())
    else:
        for m in set(sys.modules.values()) - _PRELOADED_MODULES:
            try:
                importlib.reload(m)
            except BaseException:
                pass

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


_PRELOADED_MODULES: Optional[Set[ModuleType]] = None


def get_library_doc(
    name: str,
    args: Optional[Tuple[Any, ...]] = None,
    working_dir: str = ".",
    base_dir: str = ".",
    pythonpath: Optional[List[str]] = None,
) -> LibraryDoc:

    from robot.libdocpkg.robotbuilder import KeywordDocBuilder
    from robot.libraries import STDLIBS
    from robot.output import LOGGER
    from robot.running.outputcapture import OutputCapturer
    from robot.running.testlibraries import _get_lib_class
    from robot.utils import Importer
    from robot.utils.robotpath import find_file as robot_find_file

    def get_test_library(
        name: str,
        args: Optional[Tuple[Any, ...]] = None,
        variables: Any = None,
        create_handlers: bool = True,
        logger: Any = LOGGER,
    ) -> Any:
        if name in STDLIBS:
            import_name = "robot.libraries." + name
        else:
            import_name = name
        with OutputCapturer(library_import=True):
            importer = Importer("test library")
            libcode, source = importer.import_class_or_module(import_name, return_source=True)
        libclass = _get_lib_class(libcode)
        lib = libclass(libcode, name, args or [], source, logger, variables)
        if create_handlers:
            lib.create_handlers()
        return lib

    _update_sys_path(working_dir, pythonpath)

    if is_library_by_path(name):
        name = robot_find_file(name, base_dir or ".", "Library")

    lib = get_test_library(name, args, create_handlers=False)

    libdoc = LibraryDoc(
        name=str(lib.name),
        source=lib.source,
    )

    try:

        libdoc.inits = KeywordStore(
            {
                kw.name: KeywordDoc(
                    libdoc,
                    name=libdoc.name,
                    args=tuple(str(a) for a in kw.args),
                    doc=kw.doc,
                    tags=tuple(kw.tags),
                    source=kw.source,
                    line_no=kw.lineno,
                )
                for kw in [KeywordDocBuilder().build_keyword(lib.init)]
            }
        )

        libdoc.line_no = lib.lineno
        libdoc.doc = str(lib.doc)
        libdoc.version = str(lib.version)
        libdoc.scope = str(lib.scope)
        libdoc.doc_format = str(lib.doc_format)

        lib.create_handlers()

        libdoc.keywords = KeywordStore(
            {
                kw.name: KeywordDoc(
                    libdoc,
                    name=kw.name,
                    args=tuple(str(a) for a in kw.args),
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
