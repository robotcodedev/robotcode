import re
from typing import NamedTuple, Optional

__all__ = ["InvalidVersionError", "get_robot_version"]


class InvalidVersionError(Exception):
    def __init__(self) -> None:
        super().__init__("Invalid robot version string.")


class Version(NamedTuple):
    major: int
    minor: int
    patch: Optional[int] = None
    pre_id: Optional[str] = None
    pre_number: Optional[int] = None
    dev: Optional[int] = None


_robot_version: Optional[Version] = None


def get_robot_version() -> Version:
    global _robot_version
    if _robot_version is None:
        import robot

        _robot_version = create_version_from_str(robot.get_version())
    return _robot_version


def get_robot_version_str() -> str:
    import robot

    return str(robot.get_version())


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
        raise InvalidVersionError() from ex

    raise InvalidVersionError()


if __name__ == "__main__":
    print(get_robot_version() >= (4, 0))
