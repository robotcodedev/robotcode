package dev.robotcode.robotcode4ij.execution

import dev.robotcode.robotcode4ij.testing.RobotCodeTestItem
import dev.robotcode.robotcode4ij.testing.decodeDiscoverResult
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

class RobotCodeRunTargetTest {

    @get:Rule
    val temporaryFolder = TemporaryFolder()

    // the output of `robotcode -dp . discover all` with Robot Framework 7.5
    private val model: Array<RobotCodeTestItem> by lazy {
        val stream = javaClass.getResourceAsStream("/discover/selection-project.json")!!
        val text = stream.bufferedReader().use { it.readText() }
        decodeDiscoverResult(text).items!!
    }

    private fun Array<RobotCodeTestItem>.find(longname: String): RobotCodeTestItem {
        fun search(items: Array<RobotCodeTestItem>): RobotCodeTestItem? =
            items.firstNotNullOfOrNull { if (it.longname == longname) it else search(it.children ?: arrayOf()) }
        return search(this)!!
    }

    private fun contextTarget(item: RobotCodeTestItem, model: Array<RobotCodeTestItem> = this.model) =
        RobotCodeRunConfigurationOptions().also { setContextTarget(it, item, model) }

    // items that the user entered in the editor: full names only
    private fun selection(vararg names: String, topLevel: String? = "Project") =
        RobotCodeRunConfigurationOptions().apply {
            targetKind = RobotRunTargetKind.SELECTION
            topLevelSuite = topLevel
            selection = names.map { RobotRunSelectionItem().apply { name = it } }.toMutableList()
        }

    private fun paths(vararg paths: String) = RobotCodeRunConfigurationOptions().apply {
        targetKind = RobotRunTargetKind.PATHS
        targetPaths = paths.toMutableList()
    }

    // a model like the recorded one, whose top-level suite has another name
    private fun renamed(): Array<RobotCodeTestItem> {
        fun rename(item: RobotCodeTestItem): RobotCodeTestItem = item.copy(
            longname = item.longname.replaceFirst("Project", "Renamed"),
            name = if (item.longname == "Project") "Renamed" else item.name,
            children = item.children?.map { rename(it) }?.toTypedArray()
        )
        val workspace = model.single()
        return arrayOf(workspace.copy(children = workspace.children!!.map { rename(it) }.toTypedArray()))
    }

    @Test
    fun targetsResolveToTheirArguments() {
        val stored = contextTarget(model.find("Project.Tests.Sample.First Test Passes"))
        val cases = listOf(
            Triple("a new configuration", RobotCodeRunConfigurationOptions(), model) to listOf(),
            Triple("a stored test", stored, model) to listOf(
                "-I", "tests/sample.robot", "-N", "Project", "-s", "Project.Tests.Sample",
                "-bl", "Project.Tests.Sample.First Test Passes"
            ),
            // the stored names are passed as discovery reported them, whatever the model says now
            Triple("a model with another top-level suite", stored, renamed()) to listOf(
                "-I", "tests/sample.robot", "-N", "Project", "-s", "Project.Tests.Sample",
                "-bl", "Project.Tests.Sample.First Test Passes"
            ),
            Triple("no discovery result", stored, arrayOf<RobotCodeTestItem>()) to listOf(
                "-I", "tests/sample.robot", "-N", "Project", "-s", "Project.Tests.Sample",
                "-bl", "Project.Tests.Sample.First Test Passes"
            ),
            Triple("a name that the model has", selection("Project.Tests.Nested.Deep.Deep Test"), model) to listOf(
                "-I", "tests/nested/deep.robot", "-N", "Project", "-s", "Project.Tests.Nested.Deep",
                "-bl", "Project.Tests.Nested.Deep.Deep Test"
            ),
            Triple("a name that the model lacks", selection("Project.Tests.Gone"), model) to listOf(
                "-N", "Project", "-bl", "Project.Tests.Gone"
            ),
            Triple("no stored top-level suite", selection("Project.Tests.Gone", topLevel = null), model) to listOf(
                "-N", "Project", "-bl", "Project.Tests.Gone"
            ),
            Triple("no items", selection(), model) to listOf(),
            Triple("no paths", paths(), model) to listOf(),
            Triple("paths", paths("tests/my suite.robot", "C:\\Robot Tests\\a.robot"), model) to listOf(
                "tests/my suite.robot", "C:\\Robot Tests\\a.robot"
            ),
        )
        for ((case, expected) in cases) {
            val (name, options, model) = case
            assertEquals(name, expected, targetArguments(options, model, supportsParseInclude = true))
        }
    }

    @Test
    fun runArgumentsFollowTheGlobalOptions() {
        val selection = listOf("-bl", "Project.Tests.Sample.First Test Passes")

        assertEquals(
            listOf("--no-pager", "-dp", ".", "debug", "--no-debug", "--tcp", "6613", "--") + selection,
            runArguments(listOf(), debug = false, port = 6613, robotArguments = selection)
        )
        assertEquals(
            listOf("--no-pager", "-p", "dev", "-dp", ".", "debug", "--", "tests"),
            runArguments(listOf("dev"), debug = true, port = 6612, robotArguments = listOf("tests"))
        )
        assertEquals(
            listOf("--no-pager", "-p", "dev", "-p", "ci", "-dp", ".", "debug", "--no-debug"),
            runArguments(listOf("dev", "ci"), debug = false, port = 6612, robotArguments = listOf())
        )
    }

    @Test
    fun optionsComeBeforeTheArgumentsOfTheTarget() {
        val stored = contextTarget(model.find("Project.Tests.Sample.First Test Passes"))
        val selectionArguments = listOf(
            "-I", "tests/sample.robot", "-N", "Project", "-s", "Project.Tests.Sample",
            "-bl", "Project.Tests.Sample.First Test Passes"
        )
        val head = listOf("--no-pager", "-dp", ".", "debug", "--no-debug")
        val cases = listOf(
            Triple("paths without options", paths("tests"), listOf("--", "tests")),
            Triple("paths with options", paths("tests").apply { includeTags = mutableListOf("smoke") },
                listOf("--", "-i", "smoke", "tests")),
            Triple("no paths without options", paths(), listOf()),
            // the separator comes also when only the options pass arguments
            Triple("no paths with options", paths().apply { includeTags = mutableListOf("smoke") },
                listOf("--", "-i", "smoke")),
            Triple("tests and suites without options", stored, listOf("--") + selectionArguments),
            Triple("tests and suites with options", contextTarget(model.find("Project.Tests.Sample.First Test Passes"))
                .apply { mode = RobotRunMode.RPA; robotArguments = "--loglevel DEBUG" },
                listOf("--", "--rpa", "--loglevel", "DEBUG") + selectionArguments),
        )
        for ((name, options, expected) in cases) {
            val arguments = robotFrameworkArguments(options, model, supportsParseInclude = true)
            assertEquals(name, head + expected, runArguments(listOf(), debug = false, port = 6612, arguments))
        }
    }

    @Test
    fun contextRunsMatchTheirConfigurationAfterALineShift() {
        val test = model.find("Project.Tests.Sample.First Test Passes")
        val shifted = test.copy(id = test.id + ";shifted", lineno = (test.lineno ?: 0) + 3, range = null)

        assertEquals(targetKey(contextTarget(test)), targetKey(contextTarget(shifted)))
        assertNotEquals(
            targetKey(contextTarget(test)),
            targetKey(contextTarget(model.find("Project.Tests.Sample.Second Test")))
        )
        // the project folder runs without paths, and a configuration with paths is another one
        assertEquals(RobotRunTargetKind.PATHS, contextTarget(model.single()).targetKind)
        assertEquals(targetKey(RobotCodeRunConfigurationOptions()), targetKey(contextTarget(model.single())))
        assertNotEquals(targetKey(paths("tests")), targetKey(contextTarget(model.single())))
    }

    @Test
    fun namesInTheEditorKeepTheirStoredItems() {
        val stored = contextTarget(model.find("Project.Tests.Sample.First Test Passes")).selection

        val items = selectionItemsFromNames(
            listOf("Project.Tests.Sample.First Test Passes", " Project.Tests.Other ", ""), stored
        )

        assertEquals(listOf("test", null), items.map { it.kind })
        assertEquals(listOf("Project.Tests.Sample.First Test Passes", "Project.Tests.Other"), items.map { it.name })
        assertEquals("Project.Tests.Sample", items.first().suite)
    }

    @Test
    fun editorFieldsQuoteEntriesWithSpaces() {
        val entries = listOf(
            "Project.Tests.Sample.First Test",
            "Project.Tests.A;B",
            "Project.Tests.Say \"Hello\"",
            "C:\\Robot Tests\\login.robot",
            "tests/plain"
        )

        val text = joinTargetEntries(entries)

        assertEquals(entries, parseTargetEntries(text))
        assertEquals(listOf("a b", "c"), parseTargetEntries("  \"a b\"   c  \"\" "))
    }

    @Test
    fun chosenPathsAreRelativeToTheWorkingDirectory() {
        val workingDirectory = temporaryFolder.newFolder("project").toPath()
        val inside = workingDirectory.resolve("vars dir").resolve("vars.py")
        val outside = workingDirectory.parent.resolve("shared.py")

        assertEquals("vars dir/vars.py", pathRelativeTo(inside, workingDirectory))
        assertEquals(".", pathRelativeTo(workingDirectory, workingDirectory))
        assertEquals(outside.toString(), pathRelativeTo(outside, workingDirectory))
        assertEquals(inside.toString(), pathRelativeTo(inside, null))
    }

    @Test
    fun folderChooserStartsInTheFolderOfTheField() {
        val workingDirectory = temporaryFolder.newFolder("project").toPath()
        val elsewhere = temporaryFolder.newFolder("elsewhere").toPath()

        assertEquals(workingDirectory.resolve("out3"), chooserStart("out3", workingDirectory))
        assertEquals(elsewhere, chooserStart(elsewhere.toString(), workingDirectory))
        assertEquals(workingDirectory, chooserStart("  ", workingDirectory))
        assertEquals(workingDirectory, chooserStart("\$ProjectFileDir\$/out3", workingDirectory))
        assertEquals(null, chooserStart("out3", null))
    }
}
