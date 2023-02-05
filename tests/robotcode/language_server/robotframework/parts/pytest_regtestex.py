import os

from pytest_regtest import RegTestFixture

from robotcode.language_server.robotframework.utils.version import get_robot_version

rf_version = f"rf{get_robot_version()[0]}{get_robot_version()[1]}"


class RegTestFixtureEx(RegTestFixture):
    @property
    def old_result_file(self) -> str:
        return os.path.join(self.test_folder, "_regtest_outputs", f"{rf_version}", self.old_output_file_name)

    @property
    def result_file(self) -> str:
        return os.path.join(self.test_folder, "_regtest_outputs", f"{rf_version}", self.output_file_name)
