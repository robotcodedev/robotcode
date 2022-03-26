import re
from typing import NamedTuple, Optional

__all__ = ["InvalidRobotVersionError", "get_robot_version"]


class InvalidRobotVersionError(Exception):
    def __init__(self) -> None:
        super().__init__("Invalid robot version string.")


class RobotVersion(NamedTuple):
    major: int
    minor: int
    patch: Optional[int] = None
    pre_id: Optional[str] = None
    pre_number: Optional[int] = None
    dev: Optional[int] = None


def get_robot_version() -> RobotVersion:
    import robot

    def s_to_i(s: Optional[str]) -> Optional[int]:
        return int(s) if s is not None else None

    robot_version = robot.get_version()
    try:
        m = re.match(
            r"(?P<major>\d+)"
            r"(\.(?P<minor>\d+))"
            r"(\.(?P<patch>\d+))?"
            r"((?P<pre_id>a|b|rc)(?P<pre_number>\d+))?"
            r"(\.(dev(?P<dev>\d+)))?"
            r"(?P<rest>.+)?",
            robot_version,
        )

        if m is not None and m.group("rest") is None:
            return RobotVersion(
                int(m.group("major")),
                int(m.group("minor")),
                s_to_i(m.group("patch")),
                m.group("pre_id"),
                s_to_i(m.group("pre_number")),
                s_to_i(m.group("dev")),
            )
    except (SystemExit, KeyboardInterrupt):
        raise
    except BaseException as ex:
        raise InvalidRobotVersionError() from ex

    raise InvalidRobotVersionError()


if __name__ == "__main__":
    print(get_robot_version() >= (4, 0))
