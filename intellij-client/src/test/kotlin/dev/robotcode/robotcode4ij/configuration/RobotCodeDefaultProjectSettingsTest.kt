package dev.robotcode.robotcode4ij.configuration

import com.intellij.openapi.options.Configurable
import com.intellij.openapi.project.Project
import com.intellij.openapi.project.ProjectManager
import com.intellij.testFramework.PlatformTestUtil
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import dev.robotcode.robotcode4ij.publishRobotCodeSettingsChanged
import dev.robotcode.robotcode4ij.restartDecisions

class RobotCodeDefaultProjectSettingsTest : BasePlatformTestCase() {

    private fun applyEditingPage(project: Project) {
        val configurable: Configurable = RobotCodeEditingConfigurable(project)
        try {
            configurable.createComponent()
            configurable.reset()
            configurable.apply()
        } finally {
            configurable.disposeUIResources()
        }
    }

    private fun waitForDecisions(count: Int) {
        PlatformTestUtil.waitWithEventsDispatching(
            "the settings change led to no decision", { project.restartDecisions >= count }, 10
        )
    }

    fun testApplyingASharedPageForTheDefaultProjectLeadsToNoDecision() {
        val defaultProject = ProjectManager.getInstance().defaultProject
        val before = project.restartDecisions

        applyEditingPage(defaultProject)
        Thread.sleep(1000)

        assertEquals(0, defaultProject.restartDecisions)

        // the same page of an open project lets the restart manager decide
        applyEditingPage(project)
        waitForDecisions(before + 1)
    }

    fun testTwoEventsWithinTheDebounceLeadToOneDecision() {
        val before = project.restartDecisions

        project.publishRobotCodeSettingsChanged()
        project.publishRobotCodeSettingsChanged()
        waitForDecisions(before + 1)
        Thread.sleep(1000)

        assertEquals(before + 1, project.restartDecisions)
    }
}
