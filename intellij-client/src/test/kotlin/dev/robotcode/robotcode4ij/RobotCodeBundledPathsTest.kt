package dev.robotcode.robotcode4ij

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import java.net.URL
import java.nio.file.Path

class RobotCodeBundledPathsTest {

    @Test
    fun bundledFilesAreBelowTheGivenPluginPath() {
        val pluginPath = Path.of("somewhere", "else", "robotcode4ij")

        assertEquals(pluginPath.resolve("data"), robotCodeBasePath(pluginPath))
    }

    @Test
    fun pluginPathIsTheParentOfTheLibFolderWithTheJar() {
        val pluginPath = Path.of(System.getProperty("java.io.tmpdir"), "plugins", "robotcode4ij").toAbsolutePath()
        val jar = pluginPath.resolve("lib").resolve("robotcode4ij.jar")
        val resource = URL("jar:${jar.toUri()}!/dev/robotcode/robotcode4ij/RobotCodeHelpers.class")

        assertEquals(pluginPath, pluginPathOf(resource))
        assertNull(pluginPathOf(pluginPath.resolve("RobotCodeHelpers.class").toUri().toURL()))
        assertNull(pluginPathOf(null))
    }
}
