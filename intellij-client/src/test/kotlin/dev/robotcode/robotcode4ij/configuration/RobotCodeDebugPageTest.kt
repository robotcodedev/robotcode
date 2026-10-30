package dev.robotcode.robotcode4ij.configuration

import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.intellij.ui.components.JBCheckBox
import com.intellij.util.ui.UIUtil
import dev.robotcode.robotcode4ij.RobotCodeBundle

class RobotCodeDebugPageTest : BasePlatformTestCase() {

    private lateinit var configurable: RobotCodeDebugConfigurable

    override fun setUp() {
        super.setUp()
        RobotCodeProjectConfiguration.getInstance(project).loadState(RobotCodeProjectConfiguration.ProjectState())
        configurable = RobotCodeDebugConfigurable(project)
    }

    override fun tearDown() {
        try {
            configurable.disposeUIResources()
            RobotCodeProjectConfiguration.getInstance(project).loadState(RobotCodeProjectConfiguration.ProjectState())
        } catch (e: Throwable) {
            addSuppressedException(e)
        } finally {
            super.tearDown()
        }
    }

    private fun attachPython(): JBCheckBox {
        val panel = configurable.createComponent()
        configurable.reset()
        return UIUtil.uiTraverser(panel).filter(JBCheckBox::class.java)
            .single { it.text == RobotCodeBundle.message("settings.debug.attachPython") }
    }

    fun testAttachPythonIsOffInAProjectWithoutStoredSettings() {
        assertFalse(attachPython().isSelected)
    }

    fun testApplyStoresAttachPythonAsTheProjectDefault() {
        attachPython().isSelected = true
        assertTrue(configurable.isModified)

        configurable.apply()

        assertTrue(RobotCodeProjectConfiguration.getInstance(project).debugAttachPython)
    }
}
