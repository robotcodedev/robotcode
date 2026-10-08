package dev.robotcode.robotcode4ij.configuration

import com.intellij.openapi.options.Configurable
import com.intellij.openapi.project.Project
import com.intellij.openapi.project.ProjectManager
import com.intellij.testFramework.PlatformTestUtil
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import dev.robotcode.robotcode4ij.lsp.langServerManager

class RobotCodeDefaultProjectSettingsTest : BasePlatformTestCase() {

    override fun tearDown() {
        try {
            // a restart that a test requested would otherwise run during the next test
            PlatformTestUtil.waitWithEventsDispatching(
                "the requested restart did not finish", { !project.langServerManager.restartPending }, 10
            )
        } finally {
            super.tearDown()
        }
    }

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

    fun testApplyingASharedPageForTheDefaultProjectSchedulesNoRestart() {
        val defaultProject = ProjectManager.getInstance().defaultProject

        applyEditingPage(defaultProject)

        assertFalse(defaultProject.langServerManager.restartPending)

        // the same page of an open project restarts the language server
        applyEditingPage(project)

        assertTrue(project.langServerManager.restartPending)
    }
}
