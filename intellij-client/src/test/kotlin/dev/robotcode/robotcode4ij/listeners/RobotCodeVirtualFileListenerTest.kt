package dev.robotcode.robotcode4ij.listeners

import com.intellij.openapi.util.io.FileUtil
import com.intellij.openapi.vfs.LocalFileSystem
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.openapi.vfs.newvfs.events.VFileContentChangeEvent
import com.intellij.openapi.vfs.newvfs.events.VFileDeleteEvent
import com.intellij.openapi.vfs.newvfs.events.VFilePropertyChangeEvent
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import java.io.File

class RobotCodeVirtualFileListenerTest : BasePlatformTestCase() {

    private fun change(file: VirtualFile) = VFileContentChangeEvent(null, file, 0, 1)

    private fun projectFile(name: String) = myFixture.addFileToProject(name, "").virtualFile

    fun testFileNamesRequestTheirWork() {
        assertEquals(ConfigFileWork.SERVER, configFileWork("robocop.toml"))
        for (name in listOf("robot.toml", ".robot.toml", "pyproject.toml", ".gitignore", ".robotignore")) {
            assertEquals(name, ConfigFileWork.SERVER_AND_DISCOVERY, configFileWork(name))
        }
        assertNull(configFileWork("suite.robot"))
    }

    fun testEventsOfTheProjectRequestTheirWork() {
        val listener = RobotCodeVirtualFileListener(project)
        val robocop = projectFile("robocop.toml")
        val robotToml = projectFile("robot.toml")
        val notes = projectFile("notes.txt")

        assertEquals(ConfigFileWork.SERVER, listener.requestedWork(listOf(change(robocop))))
        assertEquals(ConfigFileWork.SERVER_AND_DISCOVERY, listener.requestedWork(listOf(change(robotToml))))
        assertEquals(ConfigFileWork.SERVER_AND_DISCOVERY, listener.requestedWork(listOf(VFileDeleteEvent(null, robotToml))))
        for (name in listOf(".gitignore", ".robotignore")) {
            assertEquals(name, ConfigFileWork.SERVER_AND_DISCOVERY, listener.requestedWork(listOf(change(projectFile(name)))))
        }
        assertNull(listener.requestedWork(listOf(change(notes))))

        // the stronger work wins, and a file renamed to robot.toml counts as well
        assertEquals(
            ConfigFileWork.SERVER_AND_DISCOVERY,
            listener.requestedWork(listOf(change(robocop), change(robotToml)))
        )
        assertEquals(
            ConfigFileWork.SERVER_AND_DISCOVERY,
            listener.requestedWork(
                listOf(VFilePropertyChangeEvent(null, notes, VirtualFile.PROP_NAME, "notes.txt", "robot.toml"))
            )
        )
    }

    fun testEventOfAnotherProjectIsDropped() {
        val folder = FileUtil.createTempDirectory("other-project", null)
        val robotToml = File(folder, "robot.toml").apply { writeText("") }
        val file = LocalFileSystem.getInstance().refreshAndFindFileByIoFile(robotToml)!!

        assertNull(RobotCodeVirtualFileListener(project).requestedWork(listOf(change(file))))
    }
}
