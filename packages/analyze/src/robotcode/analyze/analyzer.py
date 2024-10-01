from pathlib import Path

from robotcode.robot.config.model import RobotConfig

from .config import AnalyzeConfig


class Analyzer:
    def __init__(
        self,
        config: AnalyzeConfig,
        robot_config: RobotConfig,
        root_folder: Path,
    ):
        self.config = config
        self.robot_config = robot_config
        self.root_folder = root_folder

    # def run(self, *paths: Path) -> Iterator[Diagnostic]:
    #     yield Diagnostic()
