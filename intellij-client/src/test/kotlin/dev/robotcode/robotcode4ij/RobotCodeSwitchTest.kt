package dev.robotcode.robotcode4ij

import com.intellij.execution.PsiLocation
import com.intellij.execution.actions.ConfigurationContext
import com.intellij.testFramework.PlatformTestUtil
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import dev.robotcode.robotcode4ij.configuration.RobotCodePersonalConfiguration
import dev.robotcode.robotcode4ij.editor.EditorNotificationProvider
import dev.robotcode.robotcode4ij.execution.RobotCodeRunConfigurationProducer
import dev.robotcode.robotcode4ij.lsp.RobotCodeLanguageServerFactory
import dev.robotcode.robotcode4ij.lsp.langServerManager
import dev.robotcode.robotcode4ij.testing.Position
import dev.robotcode.robotcode4ij.testing.Range
import dev.robotcode.robotcode4ij.testing.RobotCodeTestItem
import dev.robotcode.robotcode4ij.testing.testManger
import dev.robotcode.robotcode4ij.testing.uri

class RobotCodeSwitchTest : BasePlatformTestCase() {

    private val environment get() = project.robotCodeEnvironment
    private val settings get() = RobotCodePersonalConfiguration.getInstance(project)
    private val usable = EnvironmentState.Checked(EnvironmentResult.Usable)
    private val notInstalled = EnvironmentState.Checked(EnvironmentResult.RobotNotInstalled)

    override fun setUp() {
        super.setUp()
        environment.resetForTests()
    }

    override fun tearDown() {
        try {
            // a restart that a test requested would otherwise run during the next test
            PlatformTestUtil.waitWithEventsDispatching(
                "the requested restart did not finish", { !project.langServerManager.restartPending }, 10
            )
            settings.disableExtension = false
            project.langServerManager.enableForSession()
            project.langServerManager.allowStart()
            project.testManger.setTestItemsForTests(arrayOf())
            environment.resetForTests()
        } finally {
            super.tearDown()
        }
    }

    private fun setProjectState(state: EnvironmentState) {
        environment.checks.setState(environment.projectInterpreter, state)
    }

    fun testIsEnabledNeedsEverySwitchAndAUsableInterpreter() {
        val factory = RobotCodeLanguageServerFactory()
        val manager = project.langServerManager
        for (blocked in listOf(false, true)) {
            for (disabled in listOf(false, true)) {
                for (session in listOf(false, true)) {
                    for (state in listOf(usable, notInstalled)) {
                        if (blocked) manager.reportStartFailure() else manager.allowStart()
                        settings.disableExtension = disabled
                        if (session) manager.disableForSession() else manager.enableForSession()
                        setProjectState(state)

                        val expected = !blocked && !disabled && !session && state == usable
                        assertEquals("$blocked $disabled $session $state", expected, factory.isEnabled(project))
                    }
                }
            }
        }
    }

    fun testDisablingInLsp4ijLastsForTheSessionOnly() {
        val factory = RobotCodeLanguageServerFactory()
        setProjectState(usable)

        factory.setEnabled(false, project)

        assertFalse(settings.disableExtension)
        assertTrue(project.langServerManager.isDisabledForSession)
        assertFalse(factory.isEnabled(project))

        // Restart and Clear Cache and Restart restart with reset, as Retry does
        project.restartAll(reset = true)

        assertFalse(project.langServerManager.isDisabledForSession)
    }

    fun testEnablingInLsp4ijUnchecksTheSwitch() {
        settings.disableExtension = true
        project.langServerManager.disableForSession()

        RobotCodeLanguageServerFactory().setEnabled(true, project)

        assertFalse(settings.disableExtension)
        assertFalse(project.langServerManager.isDisabledForSession)
    }

    fun testRestartAllSchedulesNoRestartWhileDisabled() {
        settings.disableExtension = true

        project.restartAll()

        assertFalse(project.langServerManager.restartPending)

        settings.disableExtension = false
        project.restartAll()

        assertTrue(project.langServerManager.restartPending)
    }

    fun testBannerProviderReturnsNoPanelWhileDisabled() {
        setProjectState(notInstalled)
        val file = myFixture.configureByText("suite.robot", "*** Test Cases ***\nFirst\n    Log    first\n").virtualFile
        val provider = EditorNotificationProvider()

        assertNotNull(provider.collectNotificationData(project, file))

        settings.disableExtension = true

        assertNull(provider.collectNotificationData(project, file))
    }

    fun testProducerCreatesNoConfigurationWhileDisabled() {
        setProjectState(usable)
        val file = myFixture.configureByText("suite.robot", "*** Test Cases ***\nFirst\n    Log    first\n").virtualFile
        val test = RobotCodeTestItem(
            type = "test", id = "suite.First", name = "First", longname = "Suite.First", lineno = 2,
            uri = file.uri, source = file.path, range = Range(Position(1u, 0u), Position(1u, 5u))
        )
        project.testManger.setTestItemsForTests(
            arrayOf(
                RobotCodeTestItem(
                    type = "suite", id = "suite", name = "Suite", longname = "Suite", uri = file.uri,
                    source = file.path, children = arrayOf(test)
                )
            )
        )
        val element = myFixture.file.findElementAt(myFixture.editor.document.getLineStartOffset(1))!!
        val context = ConfigurationContext.createEmptyContextForLocation(PsiLocation(element))
        val producer = RobotCodeRunConfigurationProducer()

        assertNotNull(producer.createConfigurationFromContext(context))

        settings.disableExtension = true

        assertNull(producer.createConfigurationFromContext(context))
    }

    fun testSwitchingOffEmptiesTheModel() {
        val file = myFixture.configureByText("suite.robot", "*** Test Cases ***\nFirst\n    Log    first\n").virtualFile
        project.testManger.setTestItemsForTests(
            arrayOf(
                RobotCodeTestItem(type = "suite", id = "suite", name = "Suite", longname = "Suite", uri = file.uri)
            )
        )

        project.setRobotCodeDisabled(true)

        assertTrue(settings.disableExtension)
        assertEmpty(project.testManger.testItems.toList())
    }
}
