import re
from typing import NamedTuple, Optional


class InvalidVersionError(Exception):
    def __init__(self) -> None:
        super().__init__("Invalid version string.")


class Version(NamedTuple):
    major: int
    minor: int
    patch: Optional[int] = None
    pre_id: Optional[str] = None
    pre_number: Optional[int] = None
    dev: Optional[int] = None


def create_version_from_str(version_str: str) -> Version:
    def s_to_i(s: Optional[str]) -> Optional[int]:
        return int(s) if s is not None else None

    try:
        m = re.match(
            r"(?P<major>\d+)"
            r"(\.(?P<minor>\d+))"
            r"(\.(?P<patch>\d+))?"
            r"((?P<pre_id>a|b|rc)(?P<pre_number>\d+))?"
            r"(\.(dev(?P<dev>\d+)))?"
            r"(?P<rest>.+)?",
            version_str,
        )

        if m is not None and m.group("rest") is None:
            return Version(
                int(m.group("major")),
                int(m.group("minor")),
                s_to_i(m.group("patch")) or 0,
                m.group("pre_id"),
                s_to_i(m.group("pre_number")),
                s_to_i(m.group("dev")),
            )
    except (SystemExit, KeyboardInterrupt):
        raise
    except BaseException as ex:
        raise InvalidVersionError from ex

    raise InvalidVersionError
