import asyncio
import enum
import importlib
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import (
    AbstractSet,
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
    ValuesView,
    cast,
)

if __name__ == "__main__" and __package__ is None or __package__ == "":

    file = Path(__file__).resolve()
    parent, top = file.parent, file.parents[3]

    sys.path.append(str(top))
    try:
        sys.path.remove(str(parent))
    except ValueError:  # Already removed
        pass

    __package__ = "robotcode.robotframework.diagnostics"

    try:
        __import__("pydantic")
    except ImportError:
        file = Path(__file__).resolve()
        external_path = Path(file.parents[2], "external")
        sys.path.append(str(external_path))

from pydantic import BaseModel, Field, PrivateAttr
from ...language_server.types import Position, Range

__all__ = [
    "KeywordDoc",
    "LibraryDoc",
    "KeywordStore",
    "is_library_by_path",
    "get_library_doc",
    "find_file",
    "get_library_doc_external",
    "find_file_external",
]


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


class Model(BaseModel):
    class Config:
        pass


class KeywordDoc(Model):
    name: str = ""
    args: Tuple[Any, ...] = ()
    doc: str = ""
    tags: Tuple[str, ...] = ()
    source: Optional[str] = None
    line_no: int = -1
    end_line_no: int = -1
    type: str = "keyword"

    def __str__(self) -> str:
        return f"{self.name}({', '.join(str(arg) for arg in self.args)})"

    def range(self) -> Range:
        return Range(
            start=Position(line=self.line_no - 1 if self.line_no >= 0 else 0, character=0),
            end=Position(
                line=self.end_line_no - 1 if self.end_line_no >= 0 else self.line_no if self.line_no >= 0 else 0,
                character=0,
            ),
        )

    def to_markdown(self) -> str:
        result = "```python\n"

        result += f"({self.type}) \"{self.name}\": ({', '.join(self.args)})"

        result += "\n```"

        if self.doc:
            result += "\n"
            result += self.doc

        return result


class KeywordStore(Model):
    keywords: Dict[str, KeywordDoc] = Field(default_factory=lambda: {})
    __matchers: Optional[Dict[KeywordMatcher, KeywordDoc]] = PrivateAttr(None)

    @property
    def _matchers(self) -> Dict[KeywordMatcher, KeywordDoc]:
        if self.__matchers is None:
            self.__matchers = {KeywordMatcher(k): v for k, v in self.keywords.items()}
        return self.__matchers

    def __getitem__(self, key: str) -> "KeywordDoc":
        for k, v in self._matchers.items():
            if k == key:
                return v
        raise KeyError()

    def __contains__(self, __x: object) -> bool:
        return any(k == __x for k in self._matchers.keys())

    def __len__(self) -> int:
        return len(self.keywords)

    def items(self) -> AbstractSet[Tuple[str, KeywordDoc]]:
        return self.keywords.items()

    def keys(self) -> AbstractSet[str]:
        return self.keywords.keys()

    def values(self) -> ValuesView[KeywordDoc]:
        return self.keywords.values()

    def get(self, key: str, default: Optional[KeywordDoc] = None) -> Optional[KeywordDoc]:
        for k, v in self._matchers.items():
            if k == key:
                return v

        return default


class Error(Model):
    message: str
    type_name: str


class LibraryDoc(Model):
    name: str = ""
    doc: str = ""
    version: str = ""
    type: str = "LIBRARY"
    scope: str = "TEST"
    named_args: bool = True
    doc_format: str = "ROBOT"
    source: Optional[str] = None
    line_no: int = -1
    end_line_no: int = -1
    inits: KeywordStore = KeywordStore()
    keywords: KeywordStore = KeywordStore()

    errors: Optional[Sequence[Error]] = None

    def range(self) -> Range:
        return Range(
            start=Position(line=self.line_no - 1 if self.line_no >= 0 else 0, character=0),
            end=Position(
                line=self.end_line_no - 1 if self.end_line_no >= 0 else self.line_no if self.line_no >= 0 else 0,
                character=0,
            ),
        )

    def to_markdown(self) -> str:
        result = ""

        if self.inits:
            result += "\n\n---\n".join(i.to_markdown() for i in self.inits.values())
        else:
            result += "```python\n"
            result += f'({self.type.lower()}) "{self.name}": ()'
            result += "\n```"

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

    def import_test_library(
        name: str,
    ) -> Union[Any, Tuple[Any, str]]:

        if name in STDLIBS:
            import_name = "robot.libraries." + name
        else:
            import_name = name
        with OutputCapturer(library_import=True):
            importer = Importer("test library")
            return importer.import_class_or_module(import_name, return_source=True)

    def get_test_library(
        libcode: Any,
        source: str,
        name: str,
        args: Optional[Tuple[Any, ...]] = None,
        variables: Any = None,
        create_handlers: bool = True,
        logger: Any = LOGGER,
    ) -> Any:
        libclass = _get_lib_class(libcode)
        lib = libclass(libcode, name, args or [], source, logger, variables)
        if create_handlers:
            lib.create_handlers()

        return lib

    _update_sys_path(working_dir, pythonpath)

    if is_library_by_path(name):
        name = robot_find_file(name, base_dir or ".", "Library")

    source = None
    try:
        libcode, source = import_test_library(name)
        lib = get_test_library(libcode, source, name, args, create_handlers=False)
    except BaseException as e:
        return LibraryDoc(name=name, source=source, errors=[Error(message=str(e), type_name=type(e).__qualname__)])

    libdoc = LibraryDoc(
        name=str(lib.name),
        source=lib.source,
    )

    class KeywordWrapper:
        def __init__(self, kw: Any, source: str) -> None:
            self.kw = kw
            self.lib_source = source

        @property
        def name(self) -> Any:
            return self.kw.name

        @property
        def arguments(self) -> Any:
            return self.kw.arguments

        @property
        def doc(self) -> Any:
            try:
                return self.kw.doc
            except BaseException:
                return ""

        @property
        def tags(self) -> Any:
            try:
                return self.kw.tags
            except BaseException:
                return []

        @property
        def source(self) -> Any:
            try:
                return self.kw.source
            except BaseException:
                return self.lib_source

        @property
        def lineno(self) -> Any:
            try:
                return self.kw.lineno
            except BaseException:
                return 0

    try:

        libdoc.inits = KeywordStore(
            keywords={
                kw.name: KeywordDoc(
                    name=libdoc.name,
                    args=tuple(str(a) for a in kw.args),
                    doc=kw.doc,
                    tags=tuple(kw.tags),
                    source=kw.source,
                    line_no=kw.lineno,
                    type="library",
                )
                for kw in [KeywordDocBuilder().build_keyword(KeywordWrapper(lib.init, source))]
            }
        )

        libdoc.line_no = lib.lineno
        libdoc.doc = str(lib.doc)
        libdoc.version = str(lib.version)
        libdoc.scope = str(lib.scope)
        libdoc.doc_format = str(lib.doc_format)

        lib.create_handlers()

        libdoc.keywords = KeywordStore(
            keywords={
                kw.name: KeywordDoc(
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
        libdoc.errors = [Error(message=str(e), type_name=type(e).__qualname__)]

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


class ParameterMethod(enum.Enum):
    GET_LIB_DOC = 1
    FIND_NAME = 2


class Parameters(BaseModel):
    method: ParameterMethod
    name: str
    args: Optional[Tuple[Any, ...]] = None
    working_dir: str = "."
    base_dir: str = "."
    pythonpath: Optional[List[str]] = None
    file_type: str = "Resource"


class Result(BaseModel):
    lib_doc_result: Optional[LibraryDoc] = None
    find_file_result: Optional[str] = None
    error: Optional[Error] = None


class LibraryDocRemoteError(Exception):
    def __init__(self, message: str, type_name: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        self.type_name = type_name


async def _call_standalone(parameters: Parameters, timeout: Optional[float] = None) -> Result:
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        __file__,
        parameters.json(),
        stdout=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)

    result = Result.parse_raw(stdout)

    if stderr:
        raise LibraryDocRemoteError(stderr.decode())
    if result.error is not None:
        raise LibraryDocRemoteError(result.error.message, result.error.type_name)

    return result


async def get_library_doc_external(
    name: str,
    args: Optional[Tuple[Any, ...]] = None,
    working_dir: str = ".",
    base_dir: str = ".",
    pythonpath: Optional[List[str]] = None,
    timeout: Optional[float] = None,
) -> LibraryDoc:
    result = await _call_standalone(
        Parameters(
            method=ParameterMethod.GET_LIB_DOC,
            name=name,
            args=args,
            working_dir=working_dir,
            base_dir=base_dir,
            pythonpath=pythonpath,
        ),
        timeout,
    )
    if result.lib_doc_result is None:
        raise LibraryDocRemoteError("lib_doc is 'None'")

    return result.lib_doc_result


async def find_file_external(
    name: str,
    working_dir: str = ".",
    base_dir: str = ".",
    pythonpath: Optional[List[str]] = None,
    file_type: str = "Resource",
    timeout: Optional[float] = None,
) -> str:

    result = await _call_standalone(
        Parameters(
            method=ParameterMethod.FIND_NAME,
            name=name,
            working_dir=working_dir,
            base_dir=base_dir,
            pythonpath=pythonpath,
            file_type=file_type,
        ),
        timeout,
    )
    if result.find_file_result is None:
        raise LibraryDocRemoteError("find_name is 'None'")

    return result.find_file_result


if __name__ == "__main__":
    try:
        params = Parameters.parse_raw(sys.argv[1])
        if params.method == ParameterMethod.GET_LIB_DOC:
            libdoc = get_library_doc(
                params.name,
                args=params.args,
                working_dir=params.working_dir,
                base_dir=params.base_dir,
                pythonpath=params.pythonpath,
            )

            sys.stdout.write(Result(lib_doc_result=libdoc).json())
        elif params.method == ParameterMethod.FIND_NAME:
            result = find_file(
                params.name,
                working_dir=params.working_dir,
                base_dir=params.base_dir,
                pythonpath=params.pythonpath,
                file_type=params.file_type,
            )

            sys.stdout.write(Result(find_file_result=result).json())

    except BaseException as e:
        sys.stdout.write(Result(error=Error(message=str(e), type_name=type(e).__qualname__)).json())
        raise
