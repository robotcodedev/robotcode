from typing import List, Tuple

from ..language_server.parts.workspace import ConfigBase, config_section


@config_section("robotcode.language-server")
class LanguageServerConfig(ConfigBase):
    mode: str
    tcp_port: int
    args: Tuple[str, ...]
    python: str


@config_section("robotcode.robot")
class RobotConfig(ConfigBase):
    args: Tuple[str, ...]
    pythonpath: List[str]


@config_section("robotcode.syntax")
class SyntaxConfig(ConfigBase):
    section_style: str


@config_section("robotcode.robocop")
class RoboCopConfig(ConfigBase):
    enabled: bool
    include: List[str]
    exclude: List[str]
    configure: List[str]


@config_section("robotcode")
class RobotCodeConfig(ConfigBase):
    language_server: LanguageServerConfig
    robot: RobotConfig
    syntax: SyntaxConfig
