package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.CantRunException
import com.intellij.execution.configurations.RuntimeConfigurationError
import com.intellij.execution.configurations.runConfigurationType
import com.intellij.execution.executors.DefaultRunExecutor
import com.intellij.execution.runners.ExecutionEnvironmentBuilder
import com.intellij.openapi.application.WriteAction
import com.intellij.openapi.module.Module
import com.intellij.openapi.projectRoots.ProjectJdkTable
import com.intellij.openapi.projectRoots.Sdk
import com.intellij.openapi.roots.ModuleRootModificationUtil
import com.intellij.openapi.vfs.LocalFileSystem
import com.intellij.testFramework.HeavyPlatformTestCase
import com.intellij.testFramework.IndexingTestUtil
import com.intellij.testFramework.PlatformTestUtil
import com.intellij.testFramework.PsiTestUtil
import com.jetbrains.python.sdk.PythonSdkType
import dev.robotcode.robotcode4ij.EnvironmentResult
import dev.robotcode.robotcode4ij.EnvironmentState
import dev.robotcode.robotcode4ij.InterpreterOwner
import dev.robotcode.robotcode4ij.ModuleChoice
import dev.robotcode.robotcode4ij.pythonInterpreterOf
import dev.robotcode.robotcode4ij.robotCodeEnvironment
import org.jdom.Element
import org.junit.Assert
import java.io.File

/** The interpreter of new Robot Framework run configurations in a project with several modules, as in #489. */
class RobotCodeRunConfigurationModulesTest : HeavyPlatformTestCase() {

    private val factory get() = runConfigurationType<RobotCodeConfigurationType>().configurationFactories.first()

    private lateinit var moduleA: Module
    private lateinit var sdkB: Sdk

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

    private fun moduleWith(name: String, sdk: Sdk, file: String, text: String): Module {
        val folder = File(project.basePath, name)
        File(folder, file).apply { parentFile.mkdirs() }.writeText(text)
        val module = createModule(name)
        PsiTestUtil.addContentRoot(module, LocalFileSystem.getInstance().refreshAndFindFileByIoFile(folder)!!)
        ModuleRootModificationUtil.setModuleSdk(module, sdk)
        return module
    }

    // "ModuleA" without Robot Framework files, "ModuleB" with them, each with its interpreter
    override fun setUp() {
        super.setUp()
        moduleA = moduleWith("ModuleA", pythonSdk("Python A"), "main.py", "print('a')\n")
        sdkB = pythonSdk("Python B")
        moduleWith("ModuleB", sdkB, "tests/suite.robot", "*** Test Cases ***\nFirst\n    No Operation\n")
        IndexingTestUtil.waitUntilIndexesAreReady(project)
        PlatformTestUtil.waitWithEventsDispatching(
            "the detection did not finish", { project.robotCodeEnvironment.moduleChoice != ModuleChoice.Detecting }, 10
        )
        assertEquals(ModuleChoice.Resolved("ModuleB"), project.robotCodeEnvironment.moduleChoice)
    }

    fun testNewConfigurationsTheTemplateAndEarlierConfigurationsGetTheChosenModule() {
        val configurations = mapOf(
            "new" to RobotCodeRunConfiguration(project, factory),
            "template" to factory.createTemplateConfiguration(project) as RobotCodeRunConfiguration,
            // earlier versions stored no interpreter options
            "earlier" to RobotCodeRunConfiguration(project, factory).apply { readExternal(Element("configuration")) }
        )

        for ((kind, configuration) in configurations) {
            assertEquals(kind, "ModuleB", configuration.module?.name)
            assertTrue(kind, configuration.isUseModuleSdk)
            assertEquals(kind, pythonInterpreterOf(sdkB), pythonInterpreterOf(configuration.sdk))
        }
    }

    // the texts name the project only for the interpreter of the chosen module, before a run and when it starts
    fun testTextsNameTheRunConfigurationUnlessItHasTheInterpreterOfTheProject() {
        val environment = project.robotCodeEnvironment
        val notInstalled = EnvironmentState.Checked(EnvironmentResult.RobotNotInstalled)
        val texts = listOf(
            RobotCodeRunConfiguration(project, factory) to notInstalled.message,
            RobotCodeRunConfiguration(project, factory).apply { module = moduleA } to
                notInstalled.messageFor(InterpreterOwner.RUN_CONFIGURATION),
        )

        for ((configuration, text) in texts) {
            environment.checks.setState(pythonInterpreterOf(configuration.sdk), notInstalled)
            val problem = Assert.assertThrows(RuntimeConfigurationError::class.java) {
                configuration.checkConfiguration()
            }
            val error = Assert.assertThrows(CantRunException::class.java) {
                configuration.getState(
                    DefaultRunExecutor.getRunExecutorInstance(),
                    ExecutionEnvironmentBuilder.create(
                        project, DefaultRunExecutor.getRunExecutorInstance(), configuration
                    ).build()
                )
            }

            assertEquals(configuration.module?.name, text, problem.localizedMessage)
            assertEquals(configuration.module?.name, text, error.message)
        }
    }

    fun testConfigurationThatStoresAnotherModuleKeepsIt() {
        val configuration = RobotCodeRunConfiguration(project, factory).apply { module = moduleA }
        val element = Element("configuration")
        configuration.writeExternal(element)

        val restored = RobotCodeRunConfiguration(project, factory).apply { readExternal(element) }

        assertEquals("ModuleA", restored.module?.name)
    }
}
