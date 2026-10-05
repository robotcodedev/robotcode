package dev.robotcode.robotcode4ij.debugging.breakpoints

import com.intellij.testFramework.fixtures.BasePlatformTestCase

class RobotCodeLineBreakpointTypeTest : BasePlatformTestCase() {

    private val type = RobotCodeLineBreakpointType()

    private fun canPutAt(fileName: String, text: String): Boolean {
        val file = myFixture.configureByText(fileName, text).virtualFile
        return type.canPutAt(file, 1, project)
    }

    fun testRobotFrameworkFilesAcceptBreakpoints() {
        assertTrue(canPutAt("suite.robot", "*** Test Cases ***\nFirst\n    Log    hello\n"))
        assertTrue(canPutAt("common.resource", "*** Keywords ***\nGreet\n    Log    hello\n"))
    }

    fun testOtherFilesAreLeftToTheirDebuggers() {
        assertFalse(canPutAt("notes.txt", "first line\nsecond line\n"))
        assertFalse(canPutAt("robot.toml", "paths = [\"tests\"]\nlanguages = [\"en\"]\n"))
        assertFalse(canPutAt("Program.cs", "class Program {\n    static void Main() {}\n}\n"))
    }
}
