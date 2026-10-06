package dev.robotcode.robotcode4ij.lsp

import com.intellij.openapi.application.WriteAction
import com.intellij.openapi.projectRoots.ProjectJdkTable
import com.intellij.openapi.roots.ModuleRootModificationUtil
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.jetbrains.python.sdk.PythonSdkType
import dev.robotcode.robotcode4ij.CheckPythonAndRobotVersionResult
import dev.robotcode.robotcode4ij.RobotCodeHelpers

class RobotCodeLanguageServerTest : BasePlatformTestCase() {

    override fun setUp() {
        super.setUp()
        val sdk = ProjectJdkTable.getInstance().createSdk("Python for RobotCodeLanguageServerTest", PythonSdkType.getInstance())
        WriteAction.run<Throwable> {
            sdk.sdkModificator.apply { homePath = "/python/that/is/never/started" }.commitChanges()
            ProjectJdkTable.getInstance().addJdk(sdk, testRootDisposable)
        }
        ModuleRootModificationUtil.setModuleSdk(module, sdk)
        project.putUserData(RobotCodeHelpers.PYTHON_AND_ROBOT_OK_KEY, CheckPythonAndRobotVersionResult.OK)
    }

    override fun tearDown() {
        try {
            project.putUserData(RobotCodeHelpers.PYTHON_AND_ROBOT_OK_KEY, null)
            ModuleRootModificationUtil.setModuleSdk(module, null)
        } finally {
            super.tearDown()
        }
    }

    // LSP4IJ stops a server that has not connected yet when the project closes or the server restarts during its start
    // (issue #630).
    fun testStopBeforeTheServerConnected() {
        val server = RobotCodeLanguageServer(project)
        server.stop()
        server.stop()
    }
}
