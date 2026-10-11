package dev.robotcode.robotcode4ij.execution

import dev.robotcode.robotcode4ij.testing.RobotCodeTestItem
import dev.robotcode.robotcode4ij.testing.decodeDiscoverResult
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.file.Path

class RobotCodeContextTargetTest {

    // the output of `robotcode -dp . discover all` with Robot Framework 7.5, recorded in /project
    private val model: Array<RobotCodeTestItem> by lazy {
        val stream = javaClass.getResourceAsStream("/discover/selection-project.json")!!
        decodeDiscoverResult(stream.bufferedReader().use { it.readText() }).items!!
    }

    private val base = Path.of("/project")

    private fun find(longname: String): ContextSelection {
        fun search(items: Array<RobotCodeTestItem>): RobotCodeTestItem? =
            items.firstNotNullOfOrNull { if (it.longname == longname) it else search(it.children ?: arrayOf()) }
        return ContextSelection(search(model)!!, null)
    }

    private fun path(path: String) = ContextSelection(null, base.resolve(path))

    private fun names(selections: List<ContextSelection>) = selections.map { it.item?.longname ?: it.path.toString() }

    @Test
    fun selectionsAreReducedToTheOutermostOnes() {
        val sample = find("Project.Tests.Sample")
        val tests = find("Project.Tests")
        val test = find("Project.Tests.Sample.First Test Passes")

        assertEquals(listOf("Project.Tests.Sample"), names(reduceSelections(listOf(sample, sample), model)))
        assertEquals(listOf("Project.Tests"), names(reduceSelections(listOf(tests, sample), model)))
        assertEquals(listOf("Project.Tests"), names(reduceSelections(listOf(sample, tests), model)))
        assertEquals(listOf("Project.Tests.Sample"), names(reduceSelections(listOf(test, sample), model)))
        assertEquals(
            listOf(base.resolve("extra").toString()),
            names(reduceSelections(listOf(path("extra/new.robot"), path("extra")), model))
        )
    }

    @Test
    fun severalSelectionsGetOneTarget() {
        val known = RobotCodeRunConfigurationOptions()
        assertTrue(setContextTargets(known, listOf(find("Project.Tests.Sample"), find("Project.Other")), model, base))
        assertEquals(RobotRunTargetKind.SELECTION, known.targetKind)
        assertEquals(listOf("Project.Tests.Sample", "Project.Other"), known.selection.map { it.name })
        assertEquals("Project", known.topLevelSuite)

        val files = RobotCodeRunConfigurationOptions()
        assertTrue(setContextTargets(files, listOf(find("Project.Tests.Sample"), path("extra/new.robot")), model, base))
        assertEquals(RobotRunTargetKind.PATHS, files.targetKind)
        assertEquals(listOf("tests/sample.robot", "extra/new.robot"), files.targetPaths)

        // a test cannot run together with a file that discovery does not know
        val mixed = RobotCodeRunConfigurationOptions()
        assertFalse(
            setContextTargets(
                mixed, listOf(find("Project.Tests.Sample.First Test Passes"), path("extra/new.robot")), model, base
            )
        )
    }

    @Test
    fun targetsOfSeveralItemsMatchInAnyOrder() {
        val first = RobotCodeRunConfigurationOptions()
        val second = RobotCodeRunConfigurationOptions()
        setContextTargets(first, listOf(find("Project.Tests.Sample"), find("Project.Other")), model, base)
        setContextTargets(second, listOf(find("Project.Other"), find("Project.Tests.Sample")), model, base)

        assertTrue(sameTarget(first, second))
        val other = RobotCodeRunConfigurationOptions()
        setContextTargets(other, listOf(find("Project.Other"), find("Project.Tests.Nested")), model, base)
        assertFalse(sameTarget(first, other))
    }

    @Test
    fun configurationsFromContextAreNamedAfterTheirTarget() {
        fun target(item: ContextSelection) = RobotCodeRunConfigurationOptions().also {
            setContextTarget(it, item.item!!, model)
        }
        fun selection(vararg items: RobotRunSelectionItem) = RobotCodeRunConfigurationOptions().apply {
            targetKind = RobotRunTargetKind.SELECTION
            selection = items.toMutableList()
        }
        fun paths(vararg paths: String) = RobotCodeRunConfigurationOptions().apply {
            targetKind = RobotRunTargetKind.PATHS
            targetPaths = paths.toMutableList()
        }
        val cases = listOf(
            target(find("Project.Tests.Sample.First Test Passes")) to "Test First Test Passes",
            target(find("Project.Tests.Sample")) to "Suite Sample",
            // an entry of an earlier version has no own name, an entry that the user typed no kind
            selection(RobotRunSelectionItem().apply { kind = "test"; name = "Project.Tests.Sample.First Test Passes" })
                to "Test First Test Passes",
            selection(RobotRunSelectionItem().apply { name = "Project.Tests.Other" }) to "Robot Other",
            selection(RobotRunSelectionItem().apply { name = "A" }, RobotRunSelectionItem().apply { name = "B" })
                to "Robot: 2 items",
            paths("extra/new.robot") to "Robot new.robot",
            paths(".") to "Robot project",
            paths("a.robot", "b.robot") to "Robot: 2 items",
            paths() to "Workspace project",
        )
        for ((options, expected) in cases) {
            assertEquals(expected, targetName(options, "project", base))
        }
    }
}
