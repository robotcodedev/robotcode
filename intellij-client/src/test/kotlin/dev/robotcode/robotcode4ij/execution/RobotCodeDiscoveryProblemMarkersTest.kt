package dev.robotcode.robotcode4ij.execution

import com.intellij.testFramework.fixtures.BasePlatformTestCase
import dev.robotcode.robotcode4ij.testing.DiscoverDiagnostic
import dev.robotcode.robotcode4ij.testing.RobotCodeTestItem
import dev.robotcode.robotcode4ij.testing.testManger
import dev.robotcode.robotcode4ij.testing.uri

class RobotCodeDiscoveryProblemMarkersTest : BasePlatformTestCase() {

    override fun tearDown() {
        try {
            project.testManger.setTestItemsForTests(arrayOf())
            project.testManger.setDiagnosticsForTests(emptyMap())
        } finally {
            super.tearDown()
        }
    }

    fun testRunMarkerOfASuiteShowsItsProblems() {
        val file = myFixture.configureByText(
            "template.robot", "*** Settings ***\nTest Template    Log\n\n*** Test Cases ***\nTemplated\n    one\n"
        ).virtualFile
        val test = RobotCodeTestItem(type = "test", id = "t", name = "Templated", longname = "Template.Templated")
        project.testManger.setTestItemsForTests(
            arrayOf(
                RobotCodeTestItem(
                    type = "suite", id = "s", name = "Template", longname = "Template", uri = file.uri, source = file.path,
                    children = arrayOf(test)
                )
            )
        )
        project.testManger.setDiagnosticsForTests(
            mapOf(file.uri to listOf(DiscoverDiagnostic(message = "Setting 'Test Template' is allowed only once.")))
        )

        val info = RobotCodeRunLineMarkerContributor().getInfo(myFixture.file)!!

        assertTrue(info.tooltipProvider!!.apply(myFixture.file).endsWith("Setting 'Test Template' is allowed only once."))
        assertTrue(info.actions.isNotEmpty())
        assertNull(RobotCodeDiscoveryProblemLineMarkerProvider().getLineMarkerInfo(myFixture.file.firstChild.let {
            var leaf = it
            while (leaf.firstChild != null) leaf = leaf.firstChild
            leaf
        }))
    }

    fun testFileWithoutASuiteGetsAProblemMarker() {
        val file = myFixture.configureByText(
            "mixed.robot", "*** Test Cases ***\nA Test\n    Log    test\n\n*** Tasks ***\nA Task\n    Log    task\n"
        ).virtualFile
        project.testManger.setDiagnosticsForTests(
            mapOf(file.uri to listOf(DiscoverDiagnostic(message = "One file cannot have both tests and tasks.")))
        )
        var leaf = myFixture.file.firstChild
        while (leaf.firstChild != null) {
            leaf = leaf.firstChild
        }

        val marker = RobotCodeDiscoveryProblemLineMarkerProvider().getLineMarkerInfo(leaf)!!

        assertEquals("One file cannot have both tests and tasks.", marker.lineMarkerTooltip)
        assertNull(RobotCodeRunLineMarkerContributor().getInfo(myFixture.file))
    }
}
