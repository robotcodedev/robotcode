package dev.robotcode.robotcode4ij.json

import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.jetbrains.jsonSchema.ide.JsonSchemaService

/** The JSON schema the IDE finds for robot.toml and other TOML files; it is not downloaded in tests. */
class RobotTomlSchemaProviderFactoryTest : BasePlatformTestCase() {

    private fun schemaUrls(fileName: String): List<String> {
        val file = myFixture.addFileToProject(fileName, "").virtualFile
        return JsonSchemaService.Impl.get(project).getSchemaFilesForFile(file).map { it.url }
    }

    fun testRobotTomlGetsRobotCodesSchema() {
        assertEquals(listOf(ROBOT_TOML_SCHEMA_URL), schemaUrls("robot.toml"))
    }

    fun testDotRobotTomlGetsRobotCodesSchema() {
        assertEquals(listOf(ROBOT_TOML_SCHEMA_URL), schemaUrls(".robot.toml"))
    }

    fun testOtherTomlFilesDoNotGetIt() {
        assertFalse(ROBOT_TOML_SCHEMA_URL in schemaUrls("pyproject.toml"))
        assertFalse(ROBOT_TOML_SCHEMA_URL in schemaUrls("sub/robot.toml.bak"))
    }
}
