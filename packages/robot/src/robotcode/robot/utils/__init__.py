import functools

import robot.version
from robotcode.core.utils.version import Version, create_version_from_str


@functools.lru_cache(maxsize=1)
def get_robot_version() -> Version:
    return create_version_from_str(robot.version.get_version())


@functools.lru_cache(maxsize=1)
def get_robot_version_str() -> str:
    return str(robot.version.get_version())
