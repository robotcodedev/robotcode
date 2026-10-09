package dev.robotcode.robotcode4ij.testing

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertSame
import org.junit.Test

class RobotCodeFileDiscoveryTest {

    // the output of `discover --read-from-stdin all -I <file> --suite <longname>` with Robot Framework 7.5
    private fun recorded(name: String): RobotCodeDiscoverResult {
        val text = javaClass.getResourceAsStream("/discover/$name.json")!!.bufferedReader().use { it.readText() }
        // decoded as the plugin decodes it
        return decodeDiscoverResult(text)
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

    private fun item(type: String, id: String, vararg children: RobotCodeTestItem) =
        RobotCodeTestItem(type = type, id = id, name = id, longname = id, children = arrayOf(*children))

    @Test
    fun replacingChildrenCopiesOnlyThePathToTheSuite() {
        val first = item("suite", "first", item("test", "first.one"))
        val second = item("suite", "second", item("test", "second.one"))
        val root = arrayOf(item("workspace", "workspace", item("suite", "project", first, second)))

        val updated = replaceSuiteChildren(root, "second", arrayOf(item("test", "second.two")))!!

        // the old tree is unchanged, and the sibling suite is shared
        assertEquals("second.one", root[0].children!![0].children!![1].children!![0].id)
        assertEquals("second.two", updated[0].children!![0].children!![1].children!![0].id)
        assertSame(first, updated[0].children!![0].children!![0])
        assertNull(replaceSuiteChildren(root, "missing", arrayOf()))
    }

    @Test
    fun brokenFilesAreReportedInTheDiagnostics() {
        val result = recorded("broken-files")
        val suites = result.items!![0].children!![0].children!!.map { it.longname }

        // the file with tests and tasks is left out of the tree; the file with a tolerable problem keeps its test
        assertEquals(listOf("Project.Good", "Project.Template"), suites)
        assertEquals(
            listOf("One file cannot have both tests and tasks."),
            result.diagnostics!!["file:///project/mixed.robot"]!!.map { it.message }
        )
        assertEquals(
            listOf("Setting 'Test Template' is allowed only once. Only the first value is used."),
            result.diagnostics!!["file:///project/template.robot"]!!.map { it.message }
        )
    }
}
