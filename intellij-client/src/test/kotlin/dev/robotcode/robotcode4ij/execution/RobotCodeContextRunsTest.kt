package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.PsiLocation
import com.intellij.execution.RunManager
import com.intellij.execution.actions.ConfigurationContext
import com.intellij.execution.actions.RunConfigurationProducer
import com.intellij.execution.configurations.runConfigurationType
import com.intellij.psi.PsiDocumentManager
import com.intellij.psi.PsiElement
import com.intellij.psi.search.GlobalSearchScope
import com.intellij.testFramework.fixtures.BasePlatformTestCase
import com.intellij.testFramework.fixtures.TempDirTestFixture
import com.intellij.testFramework.fixtures.impl.TempDirTestFixtureImpl
import com.intellij.util.Urls
import dev.robotcode.robotcode4ij.testing.Position
import dev.robotcode.robotcode4ij.testing.Range
import dev.robotcode.robotcode4ij.testing.RobotCodeTestItem
import dev.robotcode.robotcode4ij.testing.testManger
import dev.robotcode.robotcode4ij.testing.uri

class RobotCodeContextRunsTest : BasePlatformTestCase() {

    // files on disk, because a path target needs a file system path
    override fun createTempDirTestFixture(): TempDirTestFixture = TempDirTestFixtureImpl()

    private val producer get() = RunConfigurationProducer.getInstance(RobotCodeRunConfigurationProducer::class.java)

    private val template
        get() = RunManager.getInstance(project).getConfigurationTemplate(
            runConfigurationType<RobotCodeConfigurationType>().configurationFactories.first()
        ).configuration as RobotCodeRunConfiguration

    private fun context(element: PsiElement) = ConfigurationContext.createEmptyContextForLocation(PsiLocation(element))

    private fun configurationFor(element: PsiElement): RobotCodeRunConfiguration? =
        producer.createConfigurationFromContext(context(element))?.configuration as? RobotCodeRunConfiguration

    override fun setUp() {
        super.setUp()
        project.testManger.setTestItemsForTests(arrayOf())
        template.workingDirectory = myFixture.tempDirFixture.tempDirPath
    }

    override fun tearDown() {
        try {
            template.workingDirectory = ""
        } finally {
            super.tearDown()
        }
    }

    fun testFilesAndFoldersThatDiscoveryDoesNotKnowRunByPath() {
        val file = myFixture.addFileToProject("extra/new.robot", "*** Test Cases ***\nNew Test\n    Log    x\n")
        val init = myFixture.addFileToProject("pack/__init__.robot", "*** Settings ***\nDocumentation    pack\n")
        myFixture.addFileToProject("pack/inner/deep.robot", "*** Test Cases ***\nDeep\n    Log    x\n")
        val notes = myFixture.addFileToProject("notes/readme.txt", "no suites here")

        val forFile = configurationFor(file)!!
        assertEquals(RobotRunTargetKind.PATHS, forFile.options.targetKind)
        assertEquals(listOf("extra/new.robot"), forFile.options.targetPaths)
        assertEquals("Robot new.robot", forFile.name)
        assertEquals(listOf("extra"), configurationFor(file.containingDirectory)!!.options.targetPaths)
        // an initialization file stands for its folder, which holds a suite file below a subfolder
        assertEquals(listOf("pack"), configurationFor(init)!!.options.targetPaths)
        assertNull(configurationFor(notes.containingDirectory))

        // the same path is the same configuration
        assertTrue(producer.isConfigurationFromContext(forFile, context(file)))
        assertFalse(producer.isConfigurationFromContext(forFile, context(init)))
    }

    fun testFoldersSeeSuiteFilesAddedLater() {
        val folder = myFixture.addFileToProject("later/readme.txt", "no suites yet").containingDirectory
        assertNull(configurationFor(folder))

        myFixture.addFileToProject("later/deep/new.robot", "*** Test Cases ***\nNew Test\n    Log    x\n")

        assertEquals(listOf("later"), configurationFor(folder)!!.options.targetPaths)
    }

    // the location of a result node, with the hint and the metainfo that the test events converter builds
    private fun locate(source: String, line: Int, longname: String? = null): PsiElement? {
        val hint = Urls.newUrl("robotcode", "/", Urls.newLocalFileUrl(source).toString())
            .addParameters(mapOf("line" to line.toString())).toString()
        val locations = RobotSMTestLocator().getLocation(
            hint.substringBefore("://"), hint.substringAfter("://"), longname, project,
            GlobalSearchScope.allScope(project)
        )
        return locations.singleOrNull()?.psiElement
    }

    fun testResultNodesFindTheirTestAfterLinesMoved() {
        val file = myFixture.addFileToProject(
            "tests/moved.robot", "*** Settings ***\nDocumentation    added\n\n*** Test Cases ***\nFirst\n    Log    x\n"
        )
        // discovery sees "First" on line 4 now, while the result of an earlier run still says line 1
        val uri = file.virtualFile.uri
        val test = RobotCodeTestItem(
            type = "test", id = "t", name = "First", longname = "Moved.First", uri = uri,
            range = Range(Position(4u, 0u), Position(4u, 0u))
        )
        project.testManger.setTestItemsForTests(
            arrayOf(
                RobotCodeTestItem(
                    type = "suite", id = "s", name = "Moved", longname = "Moved", uri = uri,
                    source = file.virtualFile.path, children = arrayOf(test)
                )
            )
        )
        val document = PsiDocumentManager.getInstance(project).getDocument(file)!!
        fun lineOf(element: PsiElement?) = document.getLineNumber(element!!.textRange.startOffset)

        assertEquals(4, lineOf(locate(file.virtualFile.path, 1, "Moved.First")))
        // a name that discovery does not know keeps the line of the result
        assertEquals(1, lineOf(locate(file.virtualFile.path, 1, "Other.First")))
    }

    fun testResultNodesLocateTheirFileOrFolder() {
        val file = myFixture.addFileToProject("tests/sample.robot", "*** Test Cases ***\nFirst\n    Log    x\n")

        assertEquals(file.containingDirectory, locate(file.containingDirectory.virtualFile.path, 0))
        assertEquals(file, locate(file.virtualFile.path, 0))
        assertEquals(file, locate(file.virtualFile.path, 40))
        val leaf = locate(file.virtualFile.path, 1)!!
        assertEquals(file, leaf.containingFile)
        assertEquals("*** Test Cases ***\n".length, leaf.textRange.startOffset)
    }

    fun testRenamedFilesAreFollowedByTargetAndGeneratedName() {
        val file = myFixture.addFileToProject("extra/other.robot", "*** Test Cases ***\nOther\n    Log    x\n")
        val generated = configurationFor(file)!!
        val named = configurationFor(file)!!.apply {
            name = "Mine"
            setNameChangedByUser(true)
        }
        val manager = RunManager.getInstance(project)
        val settings = listOf(generated, named).map { configuration ->
            manager.createConfiguration(configuration, configuration.factory!!).also { manager.addConfiguration(it) }
        }
        try {
            myFixture.renameElement(file, "more.robot")

            assertEquals(listOf("extra/more.robot"), generated.options.targetPaths)
            assertEquals("Robot more.robot", generated.name)
            assertEquals(listOf("extra/more.robot"), named.options.targetPaths)
            assertEquals("Mine", named.name)
        } finally {
            settings.forEach { manager.removeConfiguration(it) }
        }
    }

    fun testConfigurationsFromContextKeepTheValuesOfTheTemplate() {
        val file = myFixture.addFileToProject("extra/new.robot", "*** Test Cases ***\nNew Test\n    Log    x\n")
        template.envs = mapOf("FOO" to "bar")
        template.options.robotArguments = "--loglevel DEBUG"
        try {
            val configuration = configurationFor(file)!!

            assertEquals("bar", configuration.envs["FOO"])
            assertEquals(myFixture.tempDirFixture.tempDirPath, configuration.workingDirectory)
            assertEquals("--loglevel DEBUG", configuration.options.robotArguments)
            assertEquals(listOf("extra/new.robot"), configuration.options.targetPaths)
        } finally {
            template.envs = mapOf()
            template.options.robotArguments = null
        }
    }
}
