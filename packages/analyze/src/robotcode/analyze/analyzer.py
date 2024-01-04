from pathlib import Path

from robotcode.robot.config.model import RobotConfig

from .config import AnalyzerConfig


class Analyzer:
    def __init__(
        self,
        config: AnalyzerConfig,
        robot_config: RobotConfig,
        root_folder: Path,
    ):
        self.config = config
        self.robot_config = robot_config
        self.root_folder = root_folder

    # def run(self, *paths: Path) -> Iterator[Diagnostic]:
    #     yield Diagnostic()
