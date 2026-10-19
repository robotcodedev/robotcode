package dev.robotcode.robotcode4ij.configuration

import com.intellij.openapi.util.JDOMUtil
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.intellij.ui.components.JBCheckBox
import com.intellij.util.ui.UIUtil
import com.intellij.util.xmlb.XmlSerializer
import dev.robotcode.robotcode4ij.RobotCodeBundle
import java.awt.Component
import javax.swing.JLabel

class RobotCodeGeneralPageTest : BasePlatformTestCase() {

    private lateinit var configurable: RobotCodeGeneralConfigurable
    private lateinit var components: List<Component>

    override fun setUp() {
        super.setUp()
        RobotCodeApplicationConfiguration.getInstance().loadState(RobotCodeApplicationConfiguration.ApplicationState())
        configurable = RobotCodeGeneralConfigurable(project)
        val panel = configurable.createComponent()
        configurable.reset()
        components = UIUtil.uiTraverser(panel).toList()
    }

    override fun tearDown() {
        try {
            configurable.disposeUIResources()
            RobotCodeApplicationConfiguration.getInstance()
                .loadState(RobotCodeApplicationConfiguration.ApplicationState())
        } catch (e: Throwable) {
            addSuppressedException(e)
        } finally {
            super.tearDown()
        }
    }

    private val showWhatsNew: JBCheckBox
        get() = components.filterIsInstance<JBCheckBox>()
            .single { it.text == RobotCodeBundle.message("settings.general.showWhatsNewOnUpdate") }

    // the stored form of a state, to see that Apply left it as it was
    private fun stored(state: Any) = JDOMUtil.write(XmlSerializer.serialize(state))

    fun testCheckboxFollowsProfilesAndIsOnByDefault() {
        val profiles = components.indexOfFirst {
            it is JLabel && it.text == RobotCodeBundle.message("settings.general.profiles")
        }

        assertTrue(showWhatsNew.isSelected)
        assertTrue(profiles >= 0)
        assertTrue(profiles < components.indexOf(showWhatsNew))
    }

    fun testApplyStoresTheValueForAllProjectsOnly() {
        val projectState = stored(RobotCodeProjectConfiguration.getInstance(project).state)
        val personalState = stored(RobotCodePersonalConfiguration.getInstance(project).state)

        showWhatsNew.isSelected = false
        assertTrue(configurable.isModified)
        configurable.apply()

        assertFalse(RobotCodeApplicationConfiguration.getInstance().showWhatsNewOnUpdate)
        assertEquals(projectState, stored(RobotCodeProjectConfiguration.getInstance(project).state))
        assertEquals(personalState, stored(RobotCodePersonalConfiguration.getInstance(project).state))
    }

    fun testTextOfTheSetting() {
        val comment = RobotCodeBundle.message("settings.general.showWhatsNewOnUpdate.comment")

        assertTrue(comment.contains("notification with a link to the news"))
        assertTrue(comment.contains("all projects"))
    }
}
