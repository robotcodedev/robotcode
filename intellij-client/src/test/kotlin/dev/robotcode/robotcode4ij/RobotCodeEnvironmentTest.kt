package dev.robotcode.robotcode4ij

import com.intellij.execution.CantRunException
import com.intellij.ide.plugins.PluginManagerCore
import com.intellij.openapi.application.PathManager
import com.intellij.openapi.application.WriteAction
import com.intellij.openapi.extensions.PluginId
import com.intellij.openapi.fileEditor.FileEditorManager
import com.intellij.openapi.projectRoots.ProjectJdkTable
import com.intellij.openapi.projectRoots.Sdk
import com.intellij.openapi.projectRoots.SdkAdditionalData
import com.intellij.openapi.roots.ModuleRootManager
import com.intellij.openapi.roots.ModuleRootModificationUtil
import com.intellij.openapi.roots.ProjectRootManager
import com.intellij.testFramework.PlatformTestUtil
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.intellij.ui.EditorNotificationPanel
import com.jetbrains.python.sdk.PyRemoteSdkAdditionalDataMarker
import com.jetbrains.python.sdk.PythonSdkType
import dev.robotcode.robotcode4ij.editor.EditorNotificationProvider
import dev.robotcode.robotcode4ij.editor.bannerText
import dev.robotcode.robotcode4ij.lsp.langServerManager
import org.junit.Assert
import java.lang.reflect.Proxy
import java.nio.file.Path
import java.util.Collections

class RobotCodeEnvironmentTest : BasePlatformTestCase() {

    private val environment get() = project.robotCodeEnvironment
    private val noInterpreter = PythonInterpreter(InterpreterKind.NONE, null, null)
    private val tooOld = EnvironmentState.Checked(EnvironmentResult.PythonTooOld("3.9"))
    private val usable = EnvironmentState.Checked(EnvironmentResult.Usable)

    private var originalSdk: Sdk? = null
    private var originalSdkInherited = false
    private val checksStarted: MutableList<PythonInterpreter> = Collections.synchronizedList(mutableListOf())

    override fun setUp() {
        super.setUp()
        val rootManager = ModuleRootManager.getInstance(module)
        originalSdk = rootManager.sdk
        originalSdkInherited = rootManager.isSdkInherited
        environment.resetForTests()
        project.messageBus.connect(testRootDisposable).subscribe(
            RobotCodeEnvironment.TOPIC,
            RobotCodeEnvironmentListener { interpreter, state ->
                if (state == EnvironmentState.Checking) checksStarted.add(interpreter)
            }
        )
    }

    override fun tearDown() {
        try {
            // a restart that a test requested would otherwise run during the next test
            PlatformTestUtil.waitWithEventsDispatching(
                "the requested restart did not finish", { !project.langServerManager.restartPending }, 10
            )
            if (originalSdkInherited) {
                ModuleRootModificationUtil.setSdkInherited(module)
            } else {
                ModuleRootModificationUtil.setModuleSdk(module, originalSdk)
            }
            WriteAction.run<Throwable> { ProjectRootManager.getInstance(project).projectSdk = null }
            environment.resetForTests()
        } finally {
            super.tearDown()
        }
    }

    private fun pythonSdk(name: String, homePath: String): Sdk {
        val sdk = ProjectJdkTable.getInstance().createSdk(name, PythonSdkType.getInstance())
        val modificator = sdk.sdkModificator
        modificator.homePath = homePath
        WriteAction.run<Throwable> { modificator.commitChanges() }
        return sdk
    }

    private fun registeredPythonSdk(name: String, homePath: String): Sdk {
        val sdk = pythonSdk(name, homePath)
        WriteAction.run<Throwable> { ProjectJdkTable.getInstance().addJdk(sdk, testRootDisposable) }
        return sdk
    }

    private fun waitForChecks(interpreter: PythonInterpreter, count: Int) {
        PlatformTestUtil.waitWithEventsDispatching(
            "expected $count checks of $interpreter, got ${checksStarted.count { it == interpreter }}",
            { checksStarted.count { it == interpreter } >= count && environment.state(interpreter) !is EnvironmentState.Checking },
            10
        )
        // a check that should not run would start meanwhile
        repeat(10) {
            PlatformTestUtil.dispatchAllEventsInIdeEventQueue()
            Thread.sleep(50)
        }
        assertEquals(count, checksStarted.count { it == interpreter })
    }

    private fun java(): String {
        return ProcessHandle.current().info().command()
            .orElse(Path.of(System.getProperty("java.home"), "bin", "java").toString())
    }

    // 1.2

    fun testNoSdkGivesNoInterpreter() {
        val interpreter = pythonInterpreterOf(null)

        assertEquals(noInterpreter, interpreter)
        assertEquals(EnvironmentResult.NoInterpreter, classifyInterpreter(interpreter))
    }

    // A registered SDK keeps only additional data that its type can store, so the remote SDK is a stand-in.
    fun testRemoteSdkIsRecognizedWithoutProbingItsLocalPath() {
        val remoteData = object : SdkAdditionalData, PyRemoteSdkAdditionalDataMarker {}
        val sdk = Proxy.newProxyInstance(javaClass.classLoader, arrayOf(Sdk::class.java)) { _, method, _ ->
            when (method.name) {
                "getName" -> "Remote Python"
                "getHomePath" -> java()
                "getSdkAdditionalData" -> remoteData
                else -> null
            }
        } as Sdk
        val interpreter = pythonInterpreterOf(sdk)

        assertEquals(PythonInterpreter(InterpreterKind.REMOTE, "Remote Python", java()), interpreter)
        assertEquals(EnvironmentResult.Remote, classifyInterpreter(interpreter))
    }

    fun testLocalSdkWhosePathDoesNotExist() {
        val path = Path.of(myFixture.tempDirPath, "missing", "python").toString()
        val interpreter = pythonInterpreterOf(pythonSdk("Missing Python", path))

        assertEquals(InterpreterKind.LOCAL, interpreter.kind)
        assertEquals(EnvironmentResult.PathNotFound(path), classifyInterpreter(interpreter))
    }

    fun testLocalSdkWithAnExistingPathIsProbed() {
        assertNull(classifyInterpreter(pythonInterpreterOf(pythonSdk("Local Python", java()))))
    }

    // 2.2

    fun testBannerFollowsTheResultWithoutStartingACheck() {
        val file = myFixture.addFileToProject("suite.robot", "*** Test Cases ***\n").virtualFile
        val provider = EditorNotificationProvider()

        environment.checks.setState(noInterpreter, usable)
        assertNull(provider.collectNotificationData(project, file))

        for (state in listOf(tooOld, EnvironmentState.Failed("it ended with exit code 1."))) {
            environment.checks.setState(noInterpreter, state)
            val editor = FileEditorManager.getInstance(project).openFile(file, false).first()
            val panel = provider.collectNotificationData(project, file)!!.apply(editor) as EditorNotificationPanel

            assertEquals(bannerText(state, noInterpreter.homePath), panel.text)
        }
        assertEmpty(checksStarted)
    }

    fun testBannerRequestsACheckWithoutAResult() {
        val file = myFixture.addFileToProject("suite.robot", "*** Test Cases ***\n").virtualFile

        assertNull(EditorNotificationProvider().collectNotificationData(project, file))

        waitForChecks(noInterpreter, 1)
        assertEquals(EnvironmentState.Checked(EnvironmentResult.NoInterpreter), environment.state(noInterpreter))
    }

    // 2.3

    fun testBuilderThrowsTheTextOfAnUnusableResult() {
        environment.checks.setState(noInterpreter, tooOld)

        val error = Assert.assertThrows(CantRunException::class.java) {
            project.buildRobotCodeCommandLine(arrayOf("discover", "all"))
        }

        assertEquals(tooOld.message, error.message)
    }

    // 3.1

    fun testAnotherModuleSdkStartsOneCheck() {
        environment.watchWorkspaceModel()
        environment.markRobotProject()
        waitForChecks(noInterpreter, 1)
        val sdk = registeredPythonSdk("Python A", Path.of(myFixture.tempDirPath, "a", "python").toString())

        ModuleRootModificationUtil.setModuleSdk(module, sdk)

        waitForChecks(pythonInterpreterOf(sdk), 1)
    }

    fun testSdkChangeChecksOnlyAnUnusableInterpreter() {
        environment.watchWorkspaceModel()
        val sdk = registeredPythonSdk("Python B", Path.of(myFixture.tempDirPath, "b", "python").toString())
        ModuleRootModificationUtil.setModuleSdk(module, sdk)
        val interpreter = pythonInterpreterOf(sdk)
        PlatformTestUtil.dispatchAllEventsInIdeEventQueue()

        environment.checks.setState(interpreter, usable)
        changeSdk(sdk, "Python 3.12.1")
        waitForChecks(interpreter, 0)

        environment.checks.setState(interpreter, tooOld)
        changeSdk(sdk, "Python 3.12.2")
        waitForChecks(interpreter, 1)
    }

    fun testProjectSdkInheritedByTheModuleStartsOneCheck() {
        environment.watchWorkspaceModel()
        environment.markRobotProject()
        ModuleRootModificationUtil.setSdkInherited(module)
        val sdk = registeredPythonSdk("Python C", Path.of(myFixture.tempDirPath, "c", "python").toString())

        WriteAction.run<Throwable> { ProjectRootManager.getInstance(project).projectSdk = sdk }

        waitForChecks(pythonInterpreterOf(sdk), 1)
    }

    // Changing the roots of a Python SDK starts PyCharm's language level pusher, which fails in light tests. A new version
    // string changes the SDK entity just as well, without a new identity.
    private fun changeSdk(sdk: Sdk, version: String) {
        val modificator = sdk.sdkModificator
        modificator.versionString = version
        WriteAction.run<Throwable> { modificator.commitChanges() }
    }

    // 3.2 (light tests run on the EDT, which may read the indexes)

    fun testProjectWithoutRobotFrameworkFiles() {
        myFixture.addFileToProject("main.py", "print('hello')\n")

        assertFalse(containsRobotFrameworkFiles(project))
    }

    fun testProjectWithASuite() {
        myFixture.addFileToProject("tests/sample.robot", "*** Test Cases ***\n")

        assertTrue(containsRobotFrameworkFiles(project))
    }

    fun testProjectWithOnlyARobotToml() {
        myFixture.addFileToProject("robot.toml", "[tool.robot]\n")

        assertTrue(containsRobotFrameworkFiles(project))
    }

    fun testOpeningARobotFrameworkFileMarksTheProject() {
        environment.checks.setState(noInterpreter, tooOld)

        myFixture.configureByText("first.robot", "*** Test Cases ***\n")

        assertTrue(environment.isRobotProject)
    }

    // 3.3

    fun testBundledRobotCodeComesFromThePluginInstallation() {
        val pluginPath = PluginManagerCore.getPlugin(PluginId.getId("dev.robotcode.robotcode4ij"))!!.pluginPath
        val classes = RobotCodeHelpers::class.java.getResource("RobotCodeHelpers.class")!!

        // the tests load the classes from the build output, the IDE from the plugin's jar
        if (classes.protocol == "jar") {
            assertTrue(RobotCodeHelpers.robotCodePath.toString(), RobotCodeHelpers.robotCodePath.startsWith(pluginPath))
        } else {
            assertTrue(RobotCodeHelpers.robotCodePath.startsWith(PathManager.getPluginsDir()))
        }
    }
}
