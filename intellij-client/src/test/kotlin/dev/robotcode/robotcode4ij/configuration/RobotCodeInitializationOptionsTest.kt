package dev.robotcode.robotcode4ij.configuration

import com.google.gson.JsonArray
import com.google.gson.JsonObject
import com.intellij.openapi.project.getProjectDataPath
import com.intellij.openapi.util.Disposer
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import dev.robotcode.robotcode4ij.lsp.RobotCodeLanguageClient
import org.eclipse.lsp4j.ConfigurationItem
import org.eclipse.lsp4j.ConfigurationParams
import java.net.URI
import java.nio.file.Path

class RobotCodeInitializationOptionsTest : BasePlatformTestCase() {

    fun testStorageUriIsTheDataFolderOfTheProject() {
        val storageUri = URI(RobotCodeServerSettingsMapper.toInitializationOptions(project)["storageUri"].asString)

        assertEquals("file", storageUri.scheme)
        assertEquals(project.getProjectDataPath("robotcode"), Path.of(storageUri))
    }

    // A configuration request without a section gets the whole settings tree of createSettings().
    fun testSettingsAreTheTreeOfTheConfigurationAnswers() {
        val client = RobotCodeLanguageClient(project)
        Disposer.register(testRootDisposable, client)

        val options = RobotCodeServerSettingsMapper.toInitializationOptions(project)

        val answer = client.configuration(ConfigurationParams(listOf(ConfigurationItem()))).get()
        assertEquals(answer.single(), options["settings"])
    }

    fun testDefaultSettingsGiveAnEmptyPythonPathAndEnvironment() {
        val options = RobotCodeServerSettingsMapper.toInitializationOptions(project)

        assertEquals(JsonArray(), options["pythonPath"])
        assertEquals(JsonObject(), options["env"])
        assertEquals(setOf("storageUri", "pythonPath", "env", "settings"), options.keySet())
    }
}
