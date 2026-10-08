package dev.robotcode.robotcode4ij.testing

import com.intellij.testFramework.fixtures.BasePlatformTestCase
import dev.robotcode.robotcode4ij.EnvironmentResult
import dev.robotcode.robotcode4ij.EnvironmentState
import dev.robotcode.robotcode4ij.InterpreterKind
import dev.robotcode.robotcode4ij.PythonInterpreter
import dev.robotcode.robotcode4ij.RobotCodeEnvironment
import dev.robotcode.robotcode4ij.execution.RobotCodeRunLineMarkerContributor
import dev.robotcode.robotcode4ij.robotCodeEnvironment

class RobotCodeTestManagerEnvironmentTest : BasePlatformTestCase() {

    private val notInstalled = EnvironmentState.Checked(EnvironmentResult.RobotNotInstalled)

    // A result for the project interpreter, so that opening a Robot file starts no check whose result would clear the
    // tests of the test.
    override fun setUp() {
        super.setUp()
        val environment = project.robotCodeEnvironment
        environment.resetForTests()
        val tooOld = EnvironmentState.Checked(EnvironmentResult.PythonTooOld("3.9"))
        environment.checks.setState(environment.projectInterpreter, tooOld)
    }

    override fun tearDown() {
        try {
            project.testManger.setTestItemsForTests(arrayOf())
            project.robotCodeEnvironment.resetForTests()
        } finally {
            super.tearDown()
        }
    }

    private fun publish(interpreter: PythonInterpreter, state: EnvironmentState) {
        project.messageBus.syncPublisher(RobotCodeEnvironment.TOPIC).stateChanged(interpreter, state)
    }

    // a test "First" on the second line of a suite file
    private fun suiteWithOneTest(): RobotCodeTestItem {
        val file = myFixture.configureByText("suite.robot", "*** Test Cases ***\nFirst\n    Log    first\n").virtualFile
        val test = RobotCodeTestItem(
            type = "test", id = "suite.First", name = "First", longname = "Suite.First", lineno = 2,
            uri = file.uri, source = file.path, range = Range(Position(1u, 0u), Position(1u, 5u))
        )
        val suite = RobotCodeTestItem(
            type = "suite", id = "suite", name = "Suite", longname = "Suite", uri = file.uri, source = file.path,
            children = arrayOf(test)
        )
        project.testManger.setTestItemsForTests(arrayOf(suite))
        return suite
    }

    fun testProblemResultOrFailedCheckOfTheProjectInterpreterClearsTheTests() {
        val projectInterpreter = project.robotCodeEnvironment.projectInterpreter
        for (state in listOf(notInstalled, EnvironmentState.Failed("it did not answer within 30 seconds."))) {
            suiteWithOneTest()

            publish(projectInterpreter, state)

            assertEmpty(state.toString(), project.testManger.testItems.toList())
        }
    }

    fun testOtherStatesAndOtherInterpretersKeepTheTests() {
        val projectInterpreter = project.robotCodeEnvironment.projectInterpreter
        val other = PythonInterpreter(InterpreterKind.LOCAL, "Other Python", "/usr/bin/python3")
        val suite = suiteWithOneTest()

        publish(projectInterpreter, EnvironmentState.Checking)
        publish(projectInterpreter, EnvironmentState.Checked(EnvironmentResult.Usable))
        publish(other, notInstalled)

        assertEquals(listOf(suite), project.testManger.testItems.toList())
    }

    fun testRunMarkerDisappearsWithTheTests() {
        suiteWithOneTest()
        val element = myFixture.file.findElementAt(myFixture.editor.document.getLineStartOffset(1))!!
        val contributor = RobotCodeRunLineMarkerContributor()
        assertNotNull(contributor.getInfo(element))

        publish(project.robotCodeEnvironment.projectInterpreter, notInstalled)

        assertNull(contributor.getInfo(element))
    }
}
