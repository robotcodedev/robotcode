package dev.robotcode.robotcode4ij.markdown

import com.intellij.lang.injection.InjectedLanguageManager
import com.intellij.testFramework.fixtures.BasePlatformTestCase

/** The language of Markdown code blocks by the word after the opening backticks. */
class RobotCodeFenceLanguageProviderTest : BasePlatformTestCase() {

    private fun injectedLanguage(infoString: String, code: String): String? {
        val text = "# Notes\n\n```$infoString\n$code\n```\n"
        val file = myFixture.configureByText("notes.md", text)
        val element = InjectedLanguageManager.getInstance(project).findInjectedElementAt(file, text.indexOf(code) + 1)
        return element?.containingFile?.language?.id
    }

    private fun robotLanguage(infoString: String) =
        injectedLanguage(infoString, "*** Keywords ***\nMy Keyword\n    Log    x")

    fun testBlockMarkedRobotIsRobotFramework() {
        assertEquals("robotframework", robotLanguage("robot"))
    }

    fun testBlockMarkedRobotInAnotherCaseIsRobotFramework() {
        assertEquals("robotframework", robotLanguage("Robot"))
    }

    fun testBlockMarkedRobotframeworkIsRobotFramework() {
        assertEquals("robotframework", robotLanguage("robotframework"))
    }

    fun testBlockMarkedRobotWithAnAttributeIsRobotFramework() {
        assertEquals("robotframework", robotLanguage("robot title=\"example\""))
    }

    fun testBlockOfAnotherLanguageStaysThatLanguage() {
        assertEquals("Python", injectedLanguage("python", "print(1)"))
    }
}
