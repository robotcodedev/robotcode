package dev.robotcode.robotcode4ij

import com.intellij.execution.CantRunException
import com.intellij.notification.Notification
import com.intellij.notification.Notifications
import com.intellij.openapi.application.WriteAction
import com.intellij.openapi.fileEditor.FileEditorManager
import com.intellij.openapi.module.Module
import com.intellij.openapi.module.ModuleManager
import com.intellij.openapi.projectRoots.ProjectJdkTable
import com.intellij.openapi.projectRoots.Sdk
import com.intellij.openapi.roots.ModuleRootModificationUtil
import com.intellij.openapi.vfs.LocalFileSystem
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.testFramework.DumbModeTestUtils
import com.intellij.testFramework.HeavyPlatformTestCase
import com.intellij.testFramework.IndexingTestUtil
import com.intellij.testFramework.PlatformTestUtil
import com.intellij.testFramework.PsiTestUtil
import com.intellij.ui.EditorNotificationPanel
import com.intellij.ui.HyperlinkLabel
import com.intellij.util.ui.UIUtil
import com.jetbrains.python.sdk.PythonSdkType
import dev.robotcode.robotcode4ij.configuration.RobotCodePersonalConfiguration
import dev.robotcode.robotcode4ij.editor.EditorNotificationProvider
import dev.robotcode.robotcode4ij.lsp.RobotCodeLanguageServerFactory
import org.junit.Assert
import java.io.File

/** The module whose interpreter RobotCode uses, in projects with real modules and their roots. */
class RobotCodeModuleChoiceTest : HeavyPlatformTestCase() {

    private val environment get() = project.robotCodeEnvironment
    private val settings get() = RobotCodePersonalConfiguration.getInstance(project)
    private val suite = "*** Test Cases ***\nFirst\n    No Operation\n"

    // a registered Python interpreter whose path does not exist, so that its check starts no process
    private fun pythonSdk(name: String): Sdk {
        val sdk = ProjectJdkTable.getInstance().createSdk(name, PythonSdkType.getInstance())
        val modificator = sdk.sdkModificator
        modificator.homePath = File(createTempDirectory(), "python").path
        WriteAction.run<Throwable> {
            modificator.commitChanges()
            ProjectJdkTable.getInstance().addJdk(sdk, testRootDisposable)
        }
        return sdk
    }

    private fun folder(path: String): VirtualFile {
        val folder = File(project.basePath, path).apply { mkdirs() }
        return LocalFileSystem.getInstance().refreshAndFindFileByIoFile(folder)!!
    }

    // a module with [sdk] whose content root is the folder [name] of the project folder, holding [files]
    private fun moduleWith(name: String, sdk: Sdk?, vararg files: Pair<String, String>): Module {
        val root = File(project.basePath, name)
        files.forEach { (path, text) -> File(root, path).apply { parentFile.mkdirs() }.writeText(text) }
        val module = createModule(name)
        PsiTestUtil.addContentRoot(module, folder(name))
        sdk?.let { ModuleRootModificationUtil.setModuleSdk(module, it) }
        return module
    }

    // dispatches events for a second, so that work that should not start would have started
    private fun settle() {
        repeat(20) {
            PlatformTestUtil.dispatchAllEventsInIdeEventQueue()
            Thread.sleep(50)
        }
    }

    // the choice once the detection has finished
    private fun detectedChoice(): ModuleChoice {
        IndexingTestUtil.waitUntilIndexesAreReady(project)
        PlatformTestUtil.waitWithEventsDispatching(
            "the detection did not finish", { environment.moduleChoice != ModuleChoice.Detecting }, 10
        )
        return environment.moduleChoice
    }

    // the stored module once the detection has stored it
    private fun storedModule(expected: String): String {
        PlatformTestUtil.waitWithEventsDispatching(
            "the module was not stored", { settings.pythonModule == expected }, 10
        )
        return settings.pythonModule
    }

    // 1.2

    fun testRobotFrameworkFilesInTheSecondModuleChooseItAndStoreIt() {
        moduleWith("ModuleA", pythonSdk("Python A"), "main.py" to "print('a')\n")
        val sdkB = pythonSdk("Python B")
        moduleWith("ModuleB", sdkB, "tests/suite.robot" to suite)

        assertEquals(ModuleChoice.Resolved("ModuleB"), detectedChoice())
        assertEquals("ModuleB", storedModule("ModuleB"))
        assertEquals(pythonInterpreterOf(sdkB), environment.projectInterpreter)
    }

    fun testRobotFrameworkFilesInTwoModulesWaitForAChoiceAndStoreNothing() {
        moduleWith("ModuleA", pythonSdk("Python A"), "a.robot" to suite)
        moduleWith("ModuleB", pythonSdk("Python B"), "b.robot" to suite)

        val choice = detectedChoice() as ModuleChoice.Waiting

        assertEquals(setOf("ModuleA", "ModuleB"), choice.candidates.toSet())
        assertEquals("", settings.pythonModule)
        assertEquals(
            EnvironmentState.Checked(EnvironmentResult.ModuleNotChosen(choice.candidates)), environment.projectState
        )
        assertEquals(PythonInterpreter(InterpreterKind.NONE, null, null), environment.projectInterpreter)
    }

    fun testStoredModuleIsUsedWithoutTheDetection() {
        settings.pythonModule = "ModuleB"
        moduleWith("ModuleA", pythonSdk("Python A"), "a.robot" to suite)
        val sdkB = pythonSdk("Python B")
        moduleWith("ModuleB", sdkB, "b.robot" to suite)

        DumbModeTestUtils.runInDumbModeSynchronously(project) {
            assertEquals(ModuleChoice.Resolved("ModuleB"), environment.moduleChoice)
            assertEquals(pythonInterpreterOf(sdkB), environment.projectInterpreter)
        }
        assertEquals(0, environment.moduleDetections)
    }

    fun testRemovingTheStoredModuleDetectsAgain() {
        settings.pythonModule = "ModuleB"
        moduleWith("ModuleA", pythonSdk("Python A"), "main.py" to "print('a')\n")
        val moduleB = moduleWith("ModuleB", pythonSdk("Python B"), "b.robot" to suite)
        moduleWith("ModuleC", pythonSdk("Python C"), "c.robot" to suite)
        environment.watchWorkspaceModel()
        assertEquals(ModuleChoice.Resolved("ModuleB"), environment.moduleChoice)
        assertEquals(0, environment.moduleDetections)

        WriteAction.run<Throwable> { ModuleManager.getInstance(project).disposeModule(moduleB) }

        assertEquals(ModuleChoice.Resolved("ModuleC"), detectedChoice())
        assertTrue(environment.moduleDetections > 0)
        assertEquals("ModuleC", storedModule("ModuleC"))
    }

    fun testOneModuleIsUsedWithoutWaitingForTheIndex() {
        val sdk = pythonSdk("Python A")
        moduleWith("ModuleA", sdk, "a.robot" to suite)

        DumbModeTestUtils.runInDumbModeSynchronously(project) {
            assertEquals(ModuleChoice.Resolved("ModuleA"), environment.moduleChoice)
            assertEquals(pythonInterpreterOf(sdk), environment.projectInterpreter)
        }
        assertEquals(0, environment.moduleDetections)
    }

    // as PyCharm's pyproject.toml project model left it in a project on 2026-10-21
    fun testModuleWithoutRootsBeforeTheRobotFrameworkModule() {
        val sdk = pythonSdk("Python")
        ModuleRootModificationUtil.setModuleSdk(createModule("ModuleA"), sdk)
        File(project.basePath, "robot.toml").writeText("[tool.robot]\n")
        File(project.basePath, "shared/common.resource").apply { parentFile.mkdirs() }.writeText("*** Keywords ***\n")
        val projectFolder = folder("")
        val shared = folder("shared")
        val moduleB = createModule("ModuleB")
        PsiTestUtil.addContentRoot(moduleB, projectFolder)
        PsiTestUtil.addSourceRoot(moduleB, shared)
        ModuleRootModificationUtil.setModuleSdk(moduleB, sdk)

        assertEquals(ModuleChoice.Resolved("ModuleB"), detectedChoice())
        assertEquals(listOf(projectFolder.path, shared.path), project.rootPythonPath())
    }

    // 1.3

    private val notifications = mutableListOf<Notification>()

    private fun waitForAChoice(): VirtualFile {
        project.messageBus.connect(testRootDisposable).subscribe(Notifications.TOPIC, object : Notifications {
            override fun notify(notification: Notification) {
                if (notification.groupId == "RobotCode Module") {
                    notifications += notification
                }
            }
        })
        moduleWith("ModuleA", pythonSdk("Python A"), "a.robot" to suite)
        moduleWith("ModuleB", pythonSdk("Python B"), "b.robot" to suite)
        assertInstanceOf(detectedChoice(), ModuleChoice.Waiting::class.java)
        PlatformTestUtil.dispatchAllEventsInIdeEventQueue()
        return folder("ModuleB").findChild("b.robot")!!
    }

    private fun bannerFor(file: VirtualFile): EditorNotificationPanel? {
        val editor = FileEditorManager.getInstance(project).openFile(file, false).first()
        val data = EditorNotificationProvider().collectNotificationData(project, file)
        return data?.apply(editor) as EditorNotificationPanel?
    }

    fun testLanguageServerIsNotEnabledWhileWaitingForAChoice() {
        waitForAChoice()

        assertFalse(RobotCodeLanguageServerFactory().isEnabled(project))

        // a usable interpreter of the chosen module enables it
        settings.pythonModule = "ModuleB"
        environment.checks.setState(environment.projectInterpreter, EnvironmentState.Checked(EnvironmentResult.Usable))
        assertTrue(RobotCodeLanguageServerFactory().isEnabled(project))
    }

    fun testRequestToChooseHasOneActionPerModule() {
        val file = waitForAChoice()

        val panel = bannerFor(file)!!

        assertEquals(
            listOf("Use ModuleA", "Use ModuleB"),
            UIUtil.findComponentsOfType(panel, HyperlinkLabel::class.java).map { it.text }.sorted()
        )
        assertEquals(1, notifications.size)
        assertEquals(
            listOf("Use ModuleA", "Use ModuleB"), notifications.single().actions.map { it.templateText }.sorted()
        )
    }

    fun testChoosingAModuleStoresItAndAnnouncesASettingsChange() {
        val file = waitForAChoice()
        var settingsChanges = 0
        project.messageBus.connect(testRootDisposable)
            .subscribe(RobotCodeSettingsListener.TOPIC, RobotCodeSettingsListener { settingsChanges++ })

        bannerFor(file)!!.findLabelByName("Use ModuleB")!!.doClick()

        assertEquals("ModuleB", settings.pythonModule)
        assertEquals(1, settingsChanges)
        assertTrue(notifications.single().isExpired)
        assertEquals(ModuleChoice.Resolved("ModuleB"), environment.moduleChoice)
        assertFalse(bannerFor(file)?.text.orEmpty().contains("ModuleA"))
    }

    // 4

    fun testOnlyChangesOfModulesAndContentRootsDetectAgain() {
        val sdkA = pythonSdk("Python A")
        val moduleA = moduleWith("ModuleA", sdkA, "a.robot" to suite)
        moduleWith("ModuleB", pythonSdk("Python B"), "b.robot" to suite)
        environment.watchWorkspaceModel()
        assertInstanceOf(detectedChoice(), ModuleChoice.Waiting::class.java)
        settle()
        val detections = environment.moduleDetections

        val modificator = sdkA.sdkModificator
        modificator.versionString = "Python 3.12.9"
        WriteAction.run<Throwable> { modificator.commitChanges() }
        settle()
        assertEquals(detections, environment.moduleDetections)

        PsiTestUtil.addContentRoot(moduleA, folder("ModuleA-extra"))
        PlatformTestUtil.waitWithEventsDispatching(
            "no detection started", { environment.moduleDetections > detections }, 10
        )
    }

    fun testRunCheckOfTheProjectSaysThatTheModuleIsToBeChosen() {
        waitForAChoice()

        val error = Assert.assertThrows(CantRunException::class.java) { environment.ensureUsableForRun() }

        assertEquals(environment.projectState.message, error.message)
        assertTrue(error.message, error.message!!.startsWith("Several modules"))
        // a run configuration without an interpreter gets the result of its own interpreter, which is not the
        // project's while the module is not chosen
        val none = PythonInterpreter(InterpreterKind.NONE, null, null)
        environment.checks.setState(none, EnvironmentState.Checked(EnvironmentResult.NoInterpreter))
        val noInterpreter = Assert.assertThrows(CantRunException::class.java) { environment.ensureUsableForRun(none) }
        assertEquals(
            EnvironmentResult.NoInterpreter.messageFor(InterpreterOwner.RUN_CONFIGURATION), noInterpreter.message
        )
    }

    fun testRunCheckOfTheProjectDuringTheDetectionSaysThatRobotCodeStillChecks() {
        val moduleA = moduleWith("ModuleA", null, "a.robot" to suite)
        val moduleB = moduleWith("ModuleB", null, "b.robot" to suite)
        val sdkA = pythonSdk("Python A")
        val sdkB = pythonSdk("Python B")

        DumbModeTestUtils.runInDumbModeSynchronously(project) {
            ModuleRootModificationUtil.setModuleSdk(moduleA, sdkA)
            ModuleRootModificationUtil.setModuleSdk(moduleB, sdkB)
            assertEquals(ModuleChoice.Detecting, environment.moduleChoice)

            val error = Assert.assertThrows(CantRunException::class.java) { environment.ensureUsableForRun() }

            assertEquals(EnvironmentState.Checking.message, error.message)
        }
    }

    fun testSwitchingRobotCodeOffAndOnRemovesAndShowsTheRequestToChoose() {
        waitForAChoice()
        assertEquals(1, notifications.size)

        project.setRobotCodeDisabled(true)
        PlatformTestUtil.dispatchAllEventsInIdeEventQueue()
        assertTrue(notifications.single().isExpired)

        project.setRobotCodeDisabled(false)
        PlatformTestUtil.dispatchAllEventsInIdeEventQueue()
        assertEquals(2, notifications.size)
        assertFalse(notifications.last().isExpired)
    }
}
