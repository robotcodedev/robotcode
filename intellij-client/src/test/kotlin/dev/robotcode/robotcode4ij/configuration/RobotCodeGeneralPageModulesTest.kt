package dev.robotcode.robotcode4ij.configuration

import com.intellij.openapi.application.WriteAction
import com.intellij.openapi.projectRoots.ProjectJdkTable
import com.intellij.openapi.roots.ModuleRootModificationUtil
import com.intellij.openapi.ui.ComboBox
import com.intellij.testFramework.HeavyPlatformTestCase
import com.intellij.util.ui.UIUtil
import com.jetbrains.python.sdk.PythonSdkType
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.RobotCodeSettingsListener
import java.io.File
import javax.swing.JLabel

/** The row "Module for RobotCode" of the "General" page, in projects with real modules. */
class RobotCodeGeneralPageModulesTest : HeavyPlatformTestCase() {

    private val settings get() = RobotCodePersonalConfiguration.getInstance(project)
    private val configurables = mutableListOf<RobotCodeGeneralConfigurable>()

    override fun tearDown() {
        try {
            configurables.forEach { it.disposeUIResources() }
        } catch (e: Throwable) {
            addSuppressedException(e)
        } finally {
            super.tearDown()
        }
    }

    // a module with a Python interpreter whose path does not exist, so that its check starts no process
    private fun moduleWithInterpreter(name: String) {
        val sdk = ProjectJdkTable.getInstance().createSdk("Python $name", PythonSdkType.getInstance())
        val modificator = sdk.sdkModificator
        modificator.homePath = File(createTempDirectory(), "python").path
        WriteAction.run<Throwable> {
            modificator.commitChanges()
            ProjectJdkTable.getInstance().addJdk(sdk, testRootDisposable)
        }
        ModuleRootModificationUtil.setModuleSdk(createModule(name), sdk)
    }

    // the page and the combo box of its row, the only one on the page
    private fun page(): Pair<RobotCodeGeneralConfigurable, ComboBox<*>> {
        val configurable = RobotCodeGeneralConfigurable(project).also { configurables += it }
        val panel = configurable.createComponent()
        configurable.reset()
        val label = UIUtil.uiTraverser(panel).filterIsInstance<JLabel>()
            .single { it.text == RobotCodeBundle.message("settings.general.pythonModule") }
        val box = UIUtil.uiTraverser(panel).filterIsInstance<ComboBox<*>>().single()
        assertEquals(label.isVisible, box.isVisible)
        return configurable to box
    }

    fun testRowIsHiddenWithOneModuleAndShownWithTwo() {
        moduleWithInterpreter("ModuleA")
        assertFalse(page().second.isVisible)

        moduleWithInterpreter("ModuleB")
        val box = page().second

        assertTrue(box.isVisible)
        val items = (0 until box.itemCount).map { box.getItemAt(it) }
        assertEquals(listOf("ModuleA", "ModuleB"), items.sortedBy { it.toString() })
    }

    fun testApplyStoresTheSelectedModuleAndAnnouncesASettingsChange() {
        settings.pythonModule = "ModuleA"
        moduleWithInterpreter("ModuleA")
        moduleWithInterpreter("ModuleB")
        var settingsChanges = 0
        project.messageBus.connect(testRootDisposable)
            .subscribe(RobotCodeSettingsListener.TOPIC, RobotCodeSettingsListener { settingsChanges++ })
        val (configurable, box) = page()
        assertEquals("ModuleA", box.selectedItem)
        assertFalse(configurable.isModified)

        box.selectedItem = "ModuleB"
        assertTrue(configurable.isModified)
        box.selectedItem = "ModuleA"
        assertFalse(configurable.isModified)

        box.selectedItem = "ModuleB"
        configurable.apply()

        assertEquals("ModuleB", settings.pythonModule)
        assertEquals(1, settingsChanges)
        assertFalse(configurable.isModified)
    }
}
