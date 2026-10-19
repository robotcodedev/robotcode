package dev.robotcode.robotcode4ij.lsp

import com.intellij.openapi.actionSystem.ActionManager
import com.intellij.testFramework.fixtures.BasePlatformTestCase

/** The client command of RobotCode's code actions: LSP4IJ finds the action by its id, Find Action leaves it out. */
class RobotCodeShowDocumentSelectAndRenameActionTest : BasePlatformTestCase() {

    fun testTheClientCommandIsAnActionWithoutText() {
        val action = ActionManager.getInstance().getAction("_robotcode.codeActionShowDocumentSelectAndRename")

        assertInstanceOf(action, RobotCodeShowDocumentSelectAndRenameAction::class.java)
        assertTrue(action.templatePresentation.text.isNullOrEmpty())
    }
}
