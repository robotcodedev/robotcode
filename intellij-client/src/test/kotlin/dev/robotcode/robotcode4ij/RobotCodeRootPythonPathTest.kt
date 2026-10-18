package dev.robotcode.robotcode4ij

import com.intellij.util.xmlb.XmlSerializer
import dev.robotcode.robotcode4ij.configuration.RobotCodeProjectConfiguration
import org.jdom.output.XMLOutputter
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class RobotCodeRootPythonPathTest {

    private val main = ModulePythonRoots(listOf("/p"), listOf("/p/src", "/p/tests"))
    private val shared = ModulePythonRoots(listOf("/shared"), listOf("/shared/src"))

    @Test
    fun contentRootsComeBeforeSourceRoots() {
        assertEquals(
            listOf("/p", "/shared", "/p/src", "/p/tests", "/shared/src"),
            rootPythonPathEntries(listOf(main, shared), addContentRoots = true, addSourceRoots = true)
        )
    }

    @Test
    fun eachSwitchControlsItsKindOfRoots() {
        assertEquals(listOf("/p", "/shared"), rootPythonPathEntries(listOf(main, shared), true, false))
        assertEquals(
            listOf("/p/src", "/p/tests", "/shared/src"), rootPythonPathEntries(listOf(main, shared), false, true)
        )
        assertEquals(emptyList<String>(), rootPythonPathEntries(listOf(main, shared), false, false))
    }

    @Test
    fun aFolderThatIsContentAndSourceRootComesOnce() {
        val flat = ModulePythonRoots(listOf("/p"), listOf("/p"))

        assertEquals(listOf("/p"), rootPythonPathEntries(listOf(flat), addContentRoots = true, addSourceRoots = true))
    }

    @Test
    fun switchesAreOnByDefaultAndStoredOnlyWhenOff() {
        val defaults = RobotCodeProjectConfiguration.ProjectState()
        assertTrue(defaults.robotAddContentRoots)
        assertTrue(defaults.robotAddSourceRoots)
        val stored = XMLOutputter().outputString(XmlSerializer.serialize(defaults))
        assertFalse(stored, stored.contains("robotAddContentRoots") || stored.contains("robotAddSourceRoots"))

        val changed = RobotCodeProjectConfiguration.ProjectState().apply { robotAddSourceRoots = false }
        val restored = XmlSerializer.deserialize(
            XmlSerializer.serialize(changed), RobotCodeProjectConfiguration.ProjectState::class.java
        )
        assertTrue(restored.robotAddContentRoots)
        assertFalse(restored.robotAddSourceRoots)
    }
}
