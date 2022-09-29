from __future__ import annotations

import os
import re
from dataclasses import astuple, dataclass, fields
from pathlib import Path
from typing import Any, Iterator, Mapping, Optional, Union, overload
from urllib import parse

_IS_WIN = os.name == "nt"

_RE_DRIVE_LETTER_PATH = re.compile(r"^\/[a-zA-Z]:")

_DEFAULT_SCHEME = "file"


class InvalidUriError(Exception):
    pass


@dataclass
class _Parts:
    scheme: str = _DEFAULT_SCHEME
    netloc: str = ""
    path: str = ""
    params: str = ""
    query: str = ""
    fragment: str = ""

    def __iter__(self) -> Iterator[str]:
        yield from astuple(self)

    def __hash__(self) -> int:
        return hash((self.scheme, self.netloc, self.path, self.params, self.query, self.fragment))


class Uri(Mapping[str, str]):
    _parts: _Parts

    @overload
    def __init__(self, uri_str: str):
        ...

    @overload
    def __init__(
        self,
        *,
        scheme: Optional[str] = None,
        netloc: Optional[str] = None,
        path: Optional[str] = None,
        params: Optional[str] = None,
        query: Optional[str] = None,
        fragment: Optional[str] = None,
    ):
        ...

    def __init__(
        self,
        uri_str: Optional[str] = None,
        *,
        scheme: Optional[str] = None,
        netloc: Optional[str] = None,
        path: Optional[str] = None,
        params: Optional[str] = None,
        query: Optional[str] = None,
        fragment: Optional[str] = None,
    ) -> None:
        super().__init__()

        if uri_str is not None:
            self._parts = _Parts(*parse.urlparse(uri_str))
        else:
            self._parts = _Parts()

        if scheme is not None:
            self._parts.scheme = scheme
        if netloc is not None:
            self._parts.netloc = netloc
        if path is not None:
            self._parts.path = path
        if params is not None:
            self._parts.params = params
        if query is not None:
            self._parts.query = query
        if fragment is not None:
            self._parts.fragment = fragment

        self._parts.scheme = self._parts.scheme or _DEFAULT_SCHEME

        self._path: Optional[Path] = None

    def __str__(self) -> str:
        return parse.urlunparse(tuple(self._parts))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({repr(parse.urlunparse(tuple(self._parts)))})"

    def to_path(self) -> Path:
        if self._path is None:
            self._path = Path(self._to_path_str())

        return self._path

    def _to_path_str(self) -> str:
        """Returns the filesystem path of the given URI.
        Will handle UNC paths and normalize windows drive letters to lower-case. Also
        uses the platform specific path separator. Will *not* validate the path for
        invalid characters and semantics. Will *not* look at the scheme of this URI.
        """
        # scheme://netloc/path;parameters?query#fragment
        netloc = parse.unquote(self.netloc)
        path = parse.unquote(self.path)

        if self._parts.scheme != "file":
            raise InvalidUriError(f"Invalid URI scheme '{str(self)}'.")

        if netloc and self._parts.scheme == "file":
            # unc path: file://shares/c$/far/boo
            value = "//{}{}".format(netloc, path or "")

        elif _RE_DRIVE_LETTER_PATH.match(path):
            # windows drive letter: file:///C:/far/boo
            value = path[1].lower() + path[2:]

        else:
            # Other path
            value = path

        if _IS_WIN:
            value = value.replace("/", "\\")

        return value

    @property
    def scheme(self) -> str:
        return self._parts.scheme

    @property
    def netloc(self) -> str:
        return self._parts.netloc

    @property
    def path(self) -> str:
        return self._parts.path

    @property
    def params(self) -> str:
        return self._parts.params

    @property
    def query(self) -> str:
        return self._parts.query

    @staticmethod
    def from_path(path: Union[str, Path, os.PathLike[str]]) -> Uri:
        result = Uri(Path(path).as_uri())

        result._parts.path = parse.quote(parse.unquote(result._parts.path))
        return result

    def __eq__(self, o: object) -> bool:
        if isinstance(o, type(self)):
            return o._parts == self._parts

        return super().__eq__(o)

    def __hash__(self) -> int:
        return hash((type(self), self._parts))

    def __getitem__(self, k: str) -> Any:
        if any(e for e in fields(self._parts) if e.name == k):
            return getattr(self._parts, k)
        raise KeyError(k)

    def __len__(self) -> int:
        return len(fields(self._parts))

    def __iter__(self) -> Iterator[str]:
        for f in fields(self._parts):
            yield f.name

    def normalized(self) -> Uri:
        if self.scheme == "file":
            return Uri.from_path(self.to_path().resolve())

        return Uri(str(self))
