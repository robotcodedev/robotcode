from typing import Dict, List, Tuple

from ..common.parts.workspace import ConfigBase, config_section


@config_section("robotcode.languageServer")
class LanguageServerConfig(ConfigBase):
    mode: str = "stdio"
    tcp_port: int = 0
    args: Tuple[str, ...] = ()


@config_section("robotcode.robot")
class RobotConfig(ConfigBase):
    args: Tuple[str, ...] = ()
    python_path: List[str] = []
    env: Dict[str, str] = {}
    variables: Dict[str, str] = {}


@config_section("robotcode.syntax")
class SyntaxConfig(ConfigBase):
    section_style: str = "*** {name}s ***"


@config_section("robotcode.robocop")
class RoboCopConfig(ConfigBase):
    enabled: bool = True
    include: List[str] = []
    exclude: List[str] = []
    configurations: List[str] = []


@config_section("robotcode.robotidy")
class RoboTidyConfig(ConfigBase):
    enabled: bool = True


@config_section("robotcode")
class RobotCodeConfig(ConfigBase):
    language_server: LanguageServerConfig = LanguageServerConfig()
    robot: RobotConfig = RobotConfig()
    syntax: SyntaxConfig = SyntaxConfig()
