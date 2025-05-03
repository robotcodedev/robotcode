from pathlib import Path

from robotcode.robot.utils import get_robot_version

from .....conftest import RegTestFixture

rf_version = f"rf{get_robot_version()[0]}{get_robot_version()[1]}"


class RegTestFixtureEx(RegTestFixture):
    @property
    def result_file(self) -> Path:
        return Path(
            self.test_folder,
            "_regtest_outputs",
            rf_version,
            self.output_file_name,
        )
