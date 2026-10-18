package dev.robotcode.robotcode4ij.configuration

import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.intellij.ui.components.JBCheckBox
import com.intellij.util.ui.UIUtil
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.RobotCodeSettingsListener
import java.awt.Component
import javax.swing.JLabel

class RobotCodeRobotPageTest : BasePlatformTestCase() {

    private lateinit var configurable: RobotCodeRobotConfigurable
    private lateinit var components: List<Component>

    override fun setUp() {
        super.setUp()
        configurable = RobotCodeRobotConfigurable(project)
        val panel = configurable.createComponent()!!
        configurable.reset()
        components = UIUtil.uiTraverser(panel).toList()
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

    private fun checkBox(key: String) =
        components.filterIsInstance<JBCheckBox>().single { it.text == RobotCodeBundle.message(key) }

    private fun label(key: String) =
        components.filterIsInstance<JLabel>().first { it.text == RobotCodeBundle.message(key) }

    fun testSwitchesFollowPythonPathAndAreOnByDefault() {
        val content = checkBox("settings.robot.addContentRoots")
        val source = checkBox("settings.robot.addSourceRoots")

        assertTrue(content.isSelected)
        assertTrue(source.isSelected)
        val pythonPath = components.indexOf(label("settings.robot.pythonPath"))
        val env = components.indexOf(label("settings.robot.env"))
        assertTrue(pythonPath < components.indexOf(content))
        assertTrue(components.indexOf(content) < components.indexOf(source))
        assertTrue(components.indexOf(source) < env)
    }

    fun testApplyStoresASwitchThatWasTurnedOffAndAnnouncesTheChange() {
        var announced = 0
        project.messageBus.connect(testRootDisposable)
            .subscribe(RobotCodeSettingsListener.TOPIC, RobotCodeSettingsListener { announced++ })

        checkBox("settings.robot.addSourceRoots").isSelected = false
        assertTrue(configurable.isModified)
        configurable.apply()

        val state = RobotCodeProjectConfiguration.getInstance(project).state
        assertTrue(state.robotAddContentRoots)
        assertFalse(state.robotAddSourceRoots)
        assertTrue(announced > 0)
    }

    fun testTextsOfTheSwitches() {
        val content = RobotCodeBundle.message("settings.robot.addContentRoots.comment")
        val source = RobotCodeBundle.message("settings.robot.addSourceRoots.comment")

        for (part in listOf(
            "module whose Python interpreter RobotCode uses", "modules it depends on",
            "analysis, test discovery and test runs", "PyCharm's Python run configurations"
        )) {
            assertTrue(part, content.contains(part))
        }
        assertTrue(source.contains("Sources or Test Sources"))
        assertTrue(source.contains("<code>python-path</code> in <code>robot.toml</code>"))
    }
}
