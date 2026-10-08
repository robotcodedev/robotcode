package dev.robotcode.robotcode4ij.editor

import dev.robotcode.robotcode4ij.EnvironmentResult
import dev.robotcode.robotcode4ij.EnvironmentState
import dev.robotcode.robotcode4ij.lsp.ProjectInfo
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.w3c.dom.Element
import javax.xml.parsers.DocumentBuilderFactory

class RobotCodeStatusBarWidgetTest {

    private val usable = EnvironmentState.Checked(EnvironmentResult.Usable)
    private val info = ProjectInfo("7.5", "9.0.0", "3.14.0 (main, Oct 7 2025)", "/opt/py/bin/python", "2.7.0")

    @Test
    fun runningProjectShowsTheRobotFrameworkVersionAndTheProfiles() {
        val content = widgetContent(false, usable, info, listOf("dev"), "/opt/py/bin/python")

        assertEquals("RF 7.5 · dev", content.text)
        assertFalse(content.error)
        assertEquals(
            listOf(
                "RobotCode 2.7.0", "Robot Framework 7.5", "Robocop 9.0.0", "Python 3.14.0",
                "Interpreter: /opt/py/bin/python", "Profiles: dev"
            ),
            content.tooltip
        )
    }

    @Test
    fun withoutProfilesOrRobocop() {
        val content = widgetContent(false, usable, info.copy(robocopVersionString = null), emptyList(), null)

        assertEquals("RF 7.5", content.text)
        assertFalse(content.tooltip.any { it.startsWith("Robocop") })
        assertEquals("Profiles: the default-profiles of robot.toml", content.tooltip.last())
    }

    @Test
    fun unusableInterpreterIsAnErrorWithTheMessageOfTheCheck() {
        val notInstalled = EnvironmentState.Checked(EnvironmentResult.RobotNotInstalled)
        val failed = EnvironmentState.Failed("it did not answer within 30 seconds.")

        for (state in listOf(notInstalled, failed)) {
            val content = widgetContent(false, state, null, listOf("dev"), null)

            assertEquals("RobotCode", content.text)
            assertTrue(content.error)
            assertEquals(listOf(state.message), content.tooltip)
        }
    }

    @Test
    fun switchedOffAndWaiting() {
        assertEquals("RobotCode off", widgetContent(true, usable, info, emptyList(), null).text)
        assertEquals("RobotCode", widgetContent(false, EnvironmentState.Checking, null, emptyList(), null).text)
        assertEquals("RobotCode", widgetContent(false, usable, null, emptyList(), null).text)
    }

    @Test
    fun factoryIdIsTheIdInPluginXml() {
        val xml = javaClass.getResourceAsStream("/META-INF/plugin.xml")!!.use {
            DocumentBuilderFactory.newInstance().newDocumentBuilder().parse(it)
        }
        val factories = xml.getElementsByTagName("statusBarWidgetFactory")
        val ids = (0 until factories.length).map { factories.item(it) as Element }
            .filter { it.getAttribute("implementation") == RobotCodeStatusBarWidgetFactory::class.java.name }
            .map { it.getAttribute("id") }

        assertEquals(listOf(RobotCodeStatusBarWidgetFactory().id), ids)
    }
}
