from typing import Optional

import robot.version
from robotcode.core.utils.version import Version, create_version_from_str

_robot_version: Optional[Version] = None


def get_robot_version() -> Version:
    global _robot_version
    if _robot_version is None:
        _robot_version = create_version_from_str(robot.version.get_version())
    return _robot_version


def get_robot_version_str() -> str:
    return str(robot.version.get_version())
