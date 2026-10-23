package dev.robotcode.robotcode4ij

import com.intellij.openapi.application.runReadActionBlocking
import com.intellij.openapi.module.Module
import com.intellij.openapi.vfs.LocalFileSystem
import com.intellij.testFramework.HeavyPlatformTestCase
import com.intellij.testFramework.IndexingTestUtil
import com.intellij.testFramework.PsiTestUtil
import java.io.File

/** Which modules count as Robot Framework projects, with content roots in the project folder of the test. */
class RobotCodeModuleDetectionModulesTest : HeavyPlatformTestCase() {

    // a module with the folder [name] in the project folder as content root, holding [files]
    private fun moduleWith(name: String, vararg files: Pair<String, String>): Module {
        val folder = File(project.basePath, name).apply { mkdirs() }
        files.forEach { (path, text) -> File(folder, path).apply { parentFile.mkdirs() }.writeText(text) }
        val module = createModule(name)
        PsiTestUtil.addContentRoot(module, LocalFileSystem.getInstance().refreshAndFindFileByIoFile(folder)!!)
        return module
    }

    private fun isRobotProject(module: Module): Boolean {
        IndexingTestUtil.waitUntilIndexesAreReady(project)
        return runReadActionBlocking { isRobotFrameworkModule(module) }
    }

    fun testOnlyARobotToml() {
        assertTrue(isRobotProject(moduleWith("toml", "robot.toml" to "[tool.robot]\n")))
        assertTrue(isRobotProject(moduleWith("hidden", ".robot.toml" to "")))
    }

    fun testOnlyAMatchingPyprojectToml() {
        val pyproject = "[project]\ndependencies = [\"robotframework>=7.0\"]\n"
        val module = moduleWith("pyproject", "pyproject.toml" to pyproject)

        assertTrue(isRobotProject(module))
    }

    fun testOnlyAMatchingRequirementsTxt() {
        assertTrue(isRobotProject(moduleWith("requirements", "requirements.txt" to "robotframework==7.1\n")))
    }

    fun testOnlyARobotFile() {
        val suite = "*** Test Cases ***\nFirst\n    No Operation\n"
        assertTrue(isRobotProject(moduleWith("suites", "tests/first.robot" to suite)))
        assertTrue(isRobotProject(moduleWith("resources", "common.resource" to "*** Keywords ***\n")))
    }

    fun testNoneOfThese() {
        val module = moduleWith(
            "python",
            "main.py" to "print('hello')\n",
            "pyproject.toml" to "[project]\ndependencies = [\"robotframework-browser\"]\n",
            "requirements.txt" to "# robotframework\nrequests\n"
        )

        assertFalse(isRobotProject(module))
    }

    fun testNoContentRootAtAll() {
        moduleWith("other", "robot.toml" to "", "suite.robot" to "*** Test Cases ***\n")

        assertFalse(isRobotProject(createModule("empty")))
    }
}
