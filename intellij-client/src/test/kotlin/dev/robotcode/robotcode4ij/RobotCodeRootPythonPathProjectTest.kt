package dev.robotcode.robotcode4ij

import com.google.gson.JsonArray
import com.intellij.openapi.application.WriteAction
import com.intellij.openapi.projectRoots.ProjectJdkTable
import com.intellij.openapi.roots.ModuleRootModificationUtil
import com.intellij.openapi.vfs.LocalFileSystem
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.testFramework.HeavyPlatformTestCase
import com.intellij.testFramework.PlatformTestUtil
import com.intellij.testFramework.PsiTestUtil
import com.jetbrains.python.sdk.PythonSdkType
import dev.robotcode.robotcode4ij.configuration.RobotCodeProjectConfiguration
import dev.robotcode.robotcode4ij.configuration.RobotCodeServerSettingsMapper
import java.io.File

/** The roots of a project whose module has a Python interpreter, as the language server and discovery get them. */
class RobotCodeRootPythonPathProjectTest : HeavyPlatformTestCase() {

    private lateinit var base: File
    private lateinit var projectFolder: VirtualFile

    override fun setUp() {
        super.setUp()
        base = createTempDirectory()
        projectFolder = dir("project")
        PsiTestUtil.addContentRoot(module, projectFolder)

        // a path that does not exist: the environment check ends without starting a process
        val sdk = ProjectJdkTable.getInstance().createSdk("Python roots test", PythonSdkType.getInstance())
        val modificator = sdk.sdkModificator
        modificator.homePath = File(base, "python-not-there").path
        WriteAction.run<Throwable> {
            modificator.commitChanges()
            ProjectJdkTable.getInstance().addJdk(sdk, testRootDisposable)
        }
        ModuleRootModificationUtil.setModuleSdk(module, sdk)
    }

    override fun tearDown() {
        try {
            RobotCodeProjectConfiguration.getInstance(project).loadState(RobotCodeProjectConfiguration.ProjectState())
        } catch (e: Throwable) {
            addSuppressedException(e)
        } finally {
            super.tearDown()
        }
    }

    private fun dir(path: String): VirtualFile {
        val file = File(base, path).apply { mkdirs() }
        return LocalFileSystem.getInstance().refreshAndFindFileByIoFile(file)!!
    }

    // what the running server and the last discovery got, built while the interpreter counts as usable
    private fun snapshots(): Pair<ServerSnapshot?, DiscoverySnapshot?> {
        val environment = project.robotCodeEnvironment
        val interpreter = environment.projectInterpreter
        PlatformTestUtil.waitWithEventsDispatching(
            "the environment check did not end", { environment.state(interpreter) !is EnvironmentState.Checking }, 10
        )
        environment.checks.setState(interpreter, EnvironmentState.Checked(EnvironmentResult.Usable))
        return project.serverSnapshot() to project.discoverySnapshot()
    }

    fun testInitializationOptionsCarryTheProjectFolder() {
        val options = RobotCodeServerSettingsMapper.toInitializationOptions(project)

        assertEquals(JsonArray().apply { add(projectFolder.path) }, options["pythonPath"])
    }

    fun testInitializationOptionsWithoutPythonPathAndRoots() {
        RobotCodeProjectConfiguration.getInstance(project).state.apply {
            robotAddContentRoots = false
            robotAddSourceRoots = false
        }

        assertEquals(JsonArray(), RobotCodeServerSettingsMapper.toInitializationOptions(project)["pythonPath"])
    }

    fun testNewSourceRootChangesWhatServerAndDiscoveryGet() {
        val (server, discovery) = snapshots()
        assertNotNull(server)
        assertNotNull(discovery)

        PsiTestUtil.addSourceRoot(module, dir("project/src"))
        val (newServer, newDiscovery) = snapshots()

        assertTrue(newDiscovery!!.commandLine.containsAll(listOf("-P", dir("project/src").path)))
        assertEquals(
            RestartWork(server = true, discovery = true), decideRestart(server, newServer, discovery, newDiscovery)
        )
    }

    fun testExcludedFolderChangesNothing() {
        val (server, discovery) = snapshots()

        PsiTestUtil.addExcludedRoot(module, dir("project/build"))
        val (newServer, newDiscovery) = snapshots()

        assertEquals(
            RestartWork(server = false, discovery = false), decideRestart(server, newServer, discovery, newDiscovery)
        )
    }

    fun testRootChangesAreAnnouncedAsSettingsChanges() {
        var announced = 0
        project.messageBus.connect(testRootDisposable)
            .subscribe(RobotCodeSettingsListener.TOPIC, RobotCodeSettingsListener { announced++ })

        PsiTestUtil.addSourceRoot(module, dir("project/src"))

        assertTrue(announced > 0)
    }
}
