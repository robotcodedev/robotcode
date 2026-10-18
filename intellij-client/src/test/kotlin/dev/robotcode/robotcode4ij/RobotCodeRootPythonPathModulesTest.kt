package dev.robotcode.robotcode4ij

import com.intellij.openapi.application.runReadActionBlocking
import com.intellij.openapi.module.Module
import com.intellij.openapi.roots.ModuleRootModificationUtil
import com.intellij.openapi.vfs.LocalFileSystem
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.testFramework.HeavyPlatformTestCase
import com.intellij.testFramework.PsiTestUtil
import dev.robotcode.robotcode4ij.configuration.RobotCodeProjectConfiguration
import java.io.File

/** The roots of real modules, which the light test fixture with its single module cannot have. */
class RobotCodeRootPythonPathModulesTest : HeavyPlatformTestCase() {

    private lateinit var base: File

    override fun setUp() {
        super.setUp()
        base = createTempDirectory()
    }

    private fun dir(path: String): VirtualFile {
        val file = File(base, path).apply { mkdirs() }
        return LocalFileSystem.getInstance().refreshAndFindFileByIoFile(file)!!
    }

    private fun entries(
        module: Module, block: RobotCodeProjectConfiguration.ProjectState.() -> Unit = {}
    ): List<String> {
        val state = RobotCodeProjectConfiguration.ProjectState().apply(block)
        return runReadActionBlocking { rootPythonPath(module, state) }
    }

    private fun mainModule(): Module {
        val root = dir("main")
        PsiTestUtil.addContentRoot(module, root)
        PsiTestUtil.addSourceRoot(module, dir("main/src"))
        PsiTestUtil.addSourceRoot(module, dir("main/tests"), true)
        return module
    }

    fun testContentRootThenSourceAndTestSourceRoots() {
        val main = mainModule()

        assertEquals(listOf(dir("main").path, dir("main/src").path, dir("main/tests").path), entries(main))
    }

    fun testRootsOfModulesItDependsOnButNotOfOthers() {
        val main = mainModule()
        val shared = createModule("shared")
        PsiTestUtil.addContentRoot(shared, dir("shared"))
        PsiTestUtil.addSourceRoot(shared, dir("shared/src"))
        val other = createModule("other")
        PsiTestUtil.addContentRoot(other, dir("other"))
        PsiTestUtil.addSourceRoot(other, dir("other/src"))
        ModuleRootModificationUtil.addDependency(main, shared)

        val entries = entries(main)

        assertEquals(
            listOf(
                dir("main").path, dir("shared").path, dir("main/src").path, dir("main/tests").path,
                dir("shared/src").path
            ),
            entries
        )
        assertFalse(entries.any { it.startsWith(dir("other").path) })
    }

    fun testSwitchesTurnTheirRootsOff() {
        val main = mainModule()

        assertEquals(
            listOf(dir("main/src").path, dir("main/tests").path), entries(main) { robotAddContentRoots = false }
        )
        assertEquals(listOf(dir("main").path), entries(main) { robotAddSourceRoots = false })
        assertEquals(
            emptyList<String>(),
            entries(main) {
                robotAddContentRoots = false
                robotAddSourceRoots = false
            }
        )
    }

    fun testFolderThatIsContentAndSourceRootComesOnce() {
        val root = dir("flat")
        PsiTestUtil.addContentRoot(module, root)
        PsiTestUtil.addSourceRoot(module, root)

        assertEquals(listOf(root.path), entries(module))
    }

    fun testNoEntriesWithoutAModuleThatHasAnInterpreter() {
        mainModule()

        assertEquals(emptyList<String>(), project.rootPythonPath(RobotCodeProjectConfiguration.ProjectState()))
    }
}
