package dev.robotcode.robotcode4ij

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** The patterns that decide whether a `pyproject.toml` or `requirements.txt` belongs to a Robot Framework project. */
class RobotCodeModuleDetectionTest {

    @Test
    fun pyprojectDependencyList() {
        assertTrue(pyprojectDependsOnRobot("[project]\ndependencies = [\"robotframework>=7.0\", \"requests\"]\n"))
        assertTrue(pyprojectDependsOnRobot("[project]\ndependencies = [\n    'robotframework',\n]\n"))
        assertTrue(pyprojectDependsOnRobot("[dependency-groups]\ndev = [\"robotcode[all]\"]\n"))
    }

    @Test
    fun pyprojectTableEntry() {
        assertTrue(
            pyprojectDependsOnRobot("[tool.poetry.dependencies]\npython = \"^3.10\"\nrobotframework = \"^7.0\"\n")
        )
        assertTrue(
            pyprojectDependsOnRobot("[tool.poetry.group.dev.dependencies]\n\"robotcode\" = { version = \"*\" }\n")
        )
    }

    @Test
    fun pyprojectExtrasAndVersionSpecifiers() {
        for (requirement in listOf(
            "robotframework==7.1", "robotframework~=7.0", "robotframework!=7.0.1", "robotframework<8",
            "robotframework ; python_version >= '3.10'", "robotframework @ https://example.com/rf.whl",
            "robotcode[all]>=2.0", "robotcode [lint, debugger] >= 2.0"
        )) {
            assertTrue(requirement, pyprojectDependsOnRobot("dependencies = [\"$requirement\"]\n"))
        }
    }

    @Test
    fun pyprojectCommentedOutLine() {
        assertFalse(
            pyprojectDependsOnRobot("[project]\n# dependencies = [\"robotframework>=7.0\"]\ndependencies = []\n")
        )
        assertFalse(pyprojectDependsOnRobot("[tool.poetry.dependencies]\n    # robotframework = \"^7.0\"\n"))
    }

    @Test
    fun pyprojectUnrelatedPackages() {
        assertFalse(pyprojectDependsOnRobot("[project]\ndependencies = [\"robotframework-browser>=18\"]\n"))
        assertFalse(pyprojectDependsOnRobot("[tool.poetry.dependencies]\nrobotframework-seleniumlibrary = \"^6\"\n"))
        assertFalse(pyprojectDependsOnRobot("[project]\nname = \"robotframework-tidy-plugin\"\n"))
    }

    @Test
    fun requirementsDependencyLines() {
        assertTrue(requirementsDependOnRobot("robotframework==7.1\n"))
        assertTrue(requirementsDependOnRobot("requests\nrobotframework\n"))
        assertTrue(requirementsDependOnRobot("-r base.txt\r\nrobotframework\r\nrequests\r\n"))
        assertTrue(requirementsDependOnRobot("robotframework  # the version of the CI\n"))
        assertTrue(requirementsDependOnRobot("robotframework ; python_version >= \"3.10\"\n"))
    }

    @Test
    fun requirementsExtrasAndVersionSpecifiers() {
        assertTrue(requirementsDependOnRobot("robotcode[all]>=2.0\n"))
        assertTrue(requirementsDependOnRobot("robotframework [extra] ~= 7.0\n"))
        assertTrue(requirementsDependOnRobot("ROBOTFRAMEWORK<8\n"))
        assertTrue(requirementsDependOnRobot("robotframework @ https://example.com/rf.whl\n"))
    }

    @Test
    fun requirementsCommentedOutLine() {
        assertFalse(requirementsDependOnRobot("# robotframework==7.1\nrequests\n"))
    }

    @Test
    fun requirementsUnrelatedPackages() {
        assertFalse(requirementsDependOnRobot("robotframework-browser==18.0\nrobotframework-requests\n"))
        assertFalse(requirementsDependOnRobot("robotcode-runner-plugin\n"))
    }
}
