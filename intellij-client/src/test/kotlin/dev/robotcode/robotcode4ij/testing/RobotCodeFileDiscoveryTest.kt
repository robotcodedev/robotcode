package dev.robotcode.robotcode4ij.testing

import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class RobotCodeFileDiscoveryTest {

    // the output of `discover --read-from-stdin all -I <file> --suite <longname>` with Robot Framework 7.5
    private fun recorded(name: String): RobotCodeDiscoverResult {
        val text = javaClass.getResourceAsStream("/discover/$name.json")!!.bufferedReader().use { it.readText() }
        // decoded as the plugin decodes it
        return Json.decodeFromString<RobotCodeDiscoverResult>(text)
    }

    @Test
    fun argumentsWithParseInclude() {
        assertEquals(
            listOf("-dp", ".", "discover", "--read-from-stdin", "all", "-I", "tasks/rpa.robot", "--suite", "Project.Rpa"),
            fileDiscoveryArguments("Project.Rpa", "tasks/rpa.robot", true).toList()
        )
    }

    @Test
    fun argumentsWithoutParseIncludeOrSource() {
        val expected = listOf("-dp", ".", "discover", "--read-from-stdin", "all", "--suite", "Project.Rpa")

        assertEquals(expected, fileDiscoveryArguments("Project.Rpa", "tasks/rpa.robot", false).toList())
        assertEquals(expected, fileDiscoveryArguments("Project.Rpa", null, true).toList())
    }

    @Test
    fun argumentsAreGlobEscaped() {
        assertEquals(
            listOf("-I", "a[*]b.robot", "--suite", "Project.A[*]b [[]x[]]"),
            fileDiscoveryArguments("Project.A*b [x]", "a*b.robot", true).drop(5)
        )
    }

    @Test
    fun taskSuiteYieldsItsTasks() {
        val children = findSuiteChildren(recorded("tasks-suite").items, "/project/tasks/rpa.robot;Project.Tasks.Rpa")!!

        assertEquals(listOf("task", "task"), children.map { it.type })
        assertEquals(listOf("First Task", "Second Task"), children.map { it.name })
    }

    @Test
    fun rpaProjectYieldsTaskTypedItems() {
        val children = findSuiteChildren(
            recorded("rpa-project").items, "/rpaproject/tests/sample.robot;Rpaproject.Tests.Sample"
        )!!

        assertEquals(listOf("task", "task"), children.map { it.type })
        assertEquals(listOf("First Item", "Second Item"), children.map { it.name })
    }

    @Test
    fun fileWithoutTestsOrTasksYieldsNothing() {
        assertNull(findSuiteChildren(recorded("keyword-only").items, "/project/tasks/keywords.robot;Project.Tasks.Keywords"))
        // a suite without children counts as missing as well
        assertNull(findSuiteChildren(recorded("keyword-only").items, "/project;Project"))
    }
}
