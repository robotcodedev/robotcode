package dev.robotcode.robotcode4ij.execution

import dev.robotcode.robotcode4ij.testing.RobotCodeTestItem
import dev.robotcode.robotcode4ij.testing.decodeDiscoverResult
import org.junit.Assert.assertEquals
import org.junit.Test

class RobotCodeSelectionArgumentsTest {

    // the output of `robotcode -dp . discover all` with Robot Framework 7.5
    private fun recorded(name: String): Array<RobotCodeTestItem> {
        val text = javaClass.getResourceAsStream("/discover/$name.json")!!.bufferedReader().use { it.readText() }
        return decodeDiscoverResult(text).items!!
    }

    private fun Array<RobotCodeTestItem>.find(longname: String): RobotCodeTestItem {
        fun search(items: Array<RobotCodeTestItem>): RobotCodeTestItem? =
            items.firstNotNullOfOrNull { if (it.longname == longname) it else search(it.children ?: arrayOf()) }
        return search(this)!!
    }

    private fun arguments(
        model: Array<RobotCodeTestItem>,
        selected: List<RobotCodeTestItem>,
        supportsParseInclude: Boolean = true
    ) = selectionArguments(resolveSelection(selected, model), supportsParseInclude)

    @Test
    fun selectionsOfTheProject() {
        val model = recorded("selection-project")
        val first = "Project.Tests.Sample.First Test Passes"
        val cases = listOf(
            "one test" to listOf(first) to listOf(
                "-I", "tests/sample.robot", "-N", "Project", "-s", "Project.Tests.Sample", "-bl", first
            ),
            "one file suite" to listOf("Project.Tests.Sample") to listOf(
                "-I", "tests/sample.robot", "-N", "Project", "-s", "Project.Tests.Sample", "-bl", "Project.Tests.Sample"
            ),
            "one folder suite" to listOf("Project.Tests") to listOf(
                "-I", "tests", "-N", "Project", "-s", "Project.Tests", "-bl", "Project.Tests"
            ),
            "a test in a nested folder" to listOf("Project.Tests.Nested.Deep.Deep Test") to listOf(
                "-I", "tests/nested/deep.robot", "-N", "Project", "-s", "Project.Tests.Nested.Deep",
                "-bl", "Project.Tests.Nested.Deep.Deep Test"
            ),
            "items from two files" to listOf(first, "Project.Other.Other Test") to listOf(
                "-I", "tests/sample.robot", "-I", "other.robot", "-N", "Project",
                "-s", "Project.Tests.Sample", "-s", "Project.Other", "-bl", first, "-bl", "Project.Other.Other Test"
            ),
            "two tests of one file" to listOf(first, "Project.Tests.Sample.Second Test") to listOf(
                "-I", "tests/sample.robot", "-N", "Project", "-s", "Project.Tests.Sample",
                "-bl", first, "-bl", "Project.Tests.Sample.Second Test"
            ),
            "the workspace item" to listOf("project") to listOf(),
            "the top-level suite" to listOf("Project") to listOf(),
        )
        for ((selection, expected) in cases) {
            val (name, longnames) = selection
            assertEquals(name, expected, arguments(model, longnames.map { model.find(it) }))
        }
        assertEquals("an empty selection", listOf<String>(), arguments(model, listOf()))
    }

    @Test
    fun withoutParseIncludeNoFileIsPassed() {
        val model = recorded("selection-project")
        val test = model.find("Project.Tests.Sample.First Test Passes")

        assertEquals(
            listOf("-N", "Project", "-s", "Project.Tests.Sample", "-bl", test.longname),
            arguments(model, listOf(test), supportsParseInclude = false)
        )
    }

    @Test
    fun globCharactersAreEscapedForFilesAndSuites() {
        val model = recorded("selection-project")
        val test = model.find("Project.Tests.[Draft] Cases.Draft Test")

        assertEquals(
            listOf(
                "-I", "tests/[[]draft[]] cases.robot", "-N", "Project", "-s", "Project.Tests.[[]Draft[]] Cases",
                "-bl", "Project.Tests.[Draft] Cases.Draft Test"
            ),
            arguments(model, listOf(test))
        )
    }

    @Test
    fun aTestWhoseSuiteIsNoLongerInTheModelKeepsItsFile() {
        val model = recorded("selection-project")
        val test = model.find("Project.Tests.Sample.First Test Passes")
        // the model after the folder `tests` was removed
        val workspace = model.single()
        val topLevel = workspace.children!!.single()
        val newer = arrayOf(
            workspace.copy(children = arrayOf(topLevel.copy(children = arrayOf(model.find("Project.Other")))))
        )

        assertEquals(
            listOf("-I", "tests/sample.robot", "-N", "Project", "-bl", test.longname), arguments(newer, listOf(test))
        )
    }

    @Test
    fun projectWithSeveralPaths() {
        val model = recorded("multi-path-project")
        val test = model.find("Folder1 & Folder2.Folder2.B.My Amazing Testcase")

        assertEquals(
            listOf(
                "-I", "folder2/b.robot", "-N", "Folder1 & Folder2", "-s", "Folder1 & Folder2.Folder2.B",
                "-bl", test.longname
            ),
            arguments(model, listOf(test))
        )
        assertEquals(
            listOf(
                "-I", "folder2", "-N", "Folder1 & Folder2", "-s", "Folder1 & Folder2.Folder2",
                "-bl", "Folder1 & Folder2.Folder2"
            ),
            arguments(model, listOf(model.find("Folder1 & Folder2.Folder2")))
        )
        // the top-level suite has no source of its own and still covers the whole project
        assertEquals(listOf<String>(), arguments(model, listOf(model.find("Folder1 & Folder2"))))
    }

    @Test
    fun selectionArgumentsFollowTheDebugOptions() {
        val model = recorded("selection-project")
        val test = model.find("Project.Tests.Sample.First Test Passes")
        val selection = arguments(model, listOf(test))

        assertEquals(
            listOf(
                "debug", "--no-debug", "--tcp", "6613", "--",
                "-I", "tests/sample.robot", "-N", "Project", "-s", "Project.Tests.Sample", "-bl", test.longname
            ),
            listOf("debug") + debugArguments(debug = false, port = 6613, robotArguments = selection)
        )
        // a Debug of the whole project
        assertEquals(listOf("--tcp", "6613"), debugArguments(debug = true, port = 6613, robotArguments = listOf()))
        // the default port is not passed
        assertEquals(
            listOf("--no-debug", "--") + selection,
            debugArguments(debug = false, port = 6612, robotArguments = selection)
        )
    }

    @Test
    fun aFileOutsideTheProjectKeepsItsWindowsPath() {
        val uri = "file:///C:/Users/me/My%20Tests/%5Bdraft%5D.robot"
        val relSource = "C:\\Users\\me\\My Tests\\[draft].robot"
        val test = RobotCodeTestItem(
            type = "test", id = "t", name = "T", longname = "Project.[Draft].T", uri = uri, relSource = relSource
        )
        val suite = RobotCodeTestItem(
            type = "suite", id = "s", name = "[Draft]", longname = "Project.[Draft]", uri = uri, relSource = relSource,
            children = arrayOf(test)
        )
        val topLevel = RobotCodeTestItem(
            type = "suite", id = "p", name = "Project", longname = "Project", children = arrayOf(suite)
        )
        val model = arrayOf(
            RobotCodeTestItem(type = "workspace", id = "w", name = "w", longname = "w", children = arrayOf(topLevel))
        )

        assertEquals(
            listOf(
                "-I", "C:\\Users\\me\\My Tests\\[[]draft[]].robot", "-N", "Project", "-s", "Project.[[]Draft[]]",
                "-bl", "Project.[Draft].T"
            ),
            arguments(model, listOf(test))
        )
    }
}
