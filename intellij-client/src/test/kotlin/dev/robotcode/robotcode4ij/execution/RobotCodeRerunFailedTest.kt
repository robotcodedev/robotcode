package dev.robotcode.robotcode4ij.execution

import dev.robotcode.robotcode4ij.testing.RobotCodeTestItem
import dev.robotcode.robotcode4ij.testing.decodeDiscoverResult
import org.junit.Assert.assertEquals
import org.junit.Test

class RobotCodeRerunFailedTest {

    // the output of `robotcode -dp . discover all` with Robot Framework 7.5
    private val model = javaClass.getResourceAsStream("/discover/selection-project.json")!!.bufferedReader()
        .use { decodeDiscoverResult(it.readText()).items!! }

    private fun RobotRunSelectionItem.text() =
        listOf(kind, name, label, relSource, suite, suiteRelSource).joinToString()

    private fun selection(vararg failed: FailedTest, items: Array<RobotCodeTestItem> = model) =
        rerunSelection(failed.toList(), items).let { (topLevel, selected) -> topLevel to selected.map { it.text() } }

    @Test
    fun aTestInNestedSuitesIsStoredAsAGutterRunStoresIt() {
        assertEquals(
            "Project" to listOf(
                "test, Project.Tests.Nested.Deep.Deep Test, Deep Test, tests/nested/deep.robot, " +
                    "Project.Tests.Nested.Deep, tests/nested/deep.robot"
            ),
            selection(
                FailedTest("/project/tests/nested/deep.robot", "Deep Test", "Project.Tests.Nested.Deep.Deep Test")
            )
        )
    }

    // a run of the folder `tests` names its top-level suite after the folder, discovery after the project
    @Test
    fun theResultsOfARunOfAFolderFindTheTestsByFileAndName() {
        assertEquals(
            "Project" to listOf(
                "test, Project.Tests.Sample.Second Test, Second Test, tests/sample.robot, Project.Tests.Sample, " +
                    "tests/sample.robot",
                "test, Project.Tests.[Draft] Cases.Draft Test, Draft Test, tests/[draft] cases.robot, " +
                    "Project.Tests.[Draft] Cases, tests/[draft] cases.robot"
            ),
            selection(
                FailedTest("/project/tests/sample.robot", "Second Test", "Tests.Sample.Second Test"),
                FailedTest("/project/tests/[draft] cases.robot", "Draft Test", "Tests.[Draft] Cases.Draft Test")
            )
        )
    }

    @Test
    fun aTestThatDiscoveryDoesNotKnowKeepsItsNameFromTheRun() {
        assertEquals(
            null to listOf("test, Tests.Sample.Renamed Test, null, null, null, null"),
            selection(FailedTest("/project/tests/sample.robot", "Renamed Test", "Tests.Sample.Renamed Test"))
        )
    }

    @Test
    fun aTestNameWithDots() {
        val test = RobotCodeTestItem(
            type = "test", id = "t", name = "Version 1.2 Works", longname = "Project.Versions.Version 1.2 Works",
            uri = "file:///project/versions.robot", relSource = "versions.robot"
        )
        val suite = RobotCodeTestItem(
            type = "suite", id = "s", name = "Versions", longname = "Project.Versions",
            uri = "file:///project/versions.robot", relSource = "versions.robot", children = arrayOf(test)
        )
        val topLevel = RobotCodeTestItem(
            type = "suite", id = "p", name = "Project", longname = "Project", uri = "file:///project", relSource = ".",
            children = arrayOf(suite)
        )
        val items = arrayOf(
            RobotCodeTestItem(type = "workspace", id = "w", name = "w", longname = "w", children = arrayOf(topLevel))
        )

        assertEquals(
            "Project" to listOf(
                "test, Project.Versions.Version 1.2 Works, Version 1.2 Works, versions.robot, Project.Versions, " +
                    "versions.robot"
            ),
            selection(
                FailedTest("/project/versions.robot", "Version 1.2 Works", "Versions.Version 1.2 Works"),
                items = items
            )
        )
    }
}
