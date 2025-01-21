package dev.robotcode.robotcode4ij.editor

import com.intellij.application.options.CodeStyle
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.actionSystem.DataContext
import com.intellij.openapi.command.CommandProcessor
import com.intellij.openapi.editor.Caret
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.editor.EditorBundle
import com.intellij.openapi.editor.EditorModificationUtil
import com.intellij.openapi.editor.actionSystem.EditorActionHandler
import com.intellij.openapi.editor.actionSystem.EditorWriteActionHandler
import com.intellij.openapi.editor.actions.EditorActionUtil
import com.intellij.openapi.editor.ex.util.EditorUIUtil
import com.intellij.openapi.project.Project
import com.intellij.openapi.util.text.StringUtil
import dev.robotcode.robotcode4ij.RobotResourceFileType
import dev.robotcode.robotcode4ij.RobotSuiteFileType
import dev.robotcode.robotcode4ij.configuration.RobotCodeCodeStyleSettings
import kotlin.math.max

class RobotCodeEditorTabActionHandler(val baseHandler: EditorActionHandler) : EditorWriteActionHandler.ForEachCaret() {
    override fun isEnabledForCaret(editor: Editor, caret: Caret, dataContext: DataContext?): Boolean {
        return baseHandler.isEnabled(editor, caret, dataContext)
    }
    
    override fun doExecute(editor: Editor, caret: Caret?, dataContext: DataContext?) {
        if ((editor.virtualFile?.fileType == RobotSuiteFileType) || (editor
                .virtualFile?.fileType == RobotResourceFileType)
        ) {
            return super.doExecute(editor, caret, dataContext)
        }
        
        return baseHandler.execute(editor, caret, dataContext)
    }
    
    override fun executeWriteAction(editor: Editor, caret: Caret?, dataContext: DataContext?) {
        CommandProcessor.getInstance().currentCommandGroupId = EditorActionUtil.EDIT_COMMAND_GROUP
        CommandProcessor.getInstance().currentCommandName = EditorBundle.message("typing.command.name")
        val project = CommonDataKeys.PROJECT.getData(dataContext!!)
        insertTabAtCaret(editor, caret, project)
    }
    
    private fun insertTabAtCaret(editor: Editor, caret: Caret?, project: Project?) {
        if (caret == null) return
        
        EditorUIUtil.hideCursorInEditor(editor)
        
        val columnNumber: Int = if (caret.hasSelection()) {
            editor.visualToLogicalPosition(caret.selectionStartPosition).column
        } else {
            editor.caretModel.logicalPosition.column
        }
        
        val settings = if (project != null) CodeStyle.getSettings(project) else CodeStyle.getDefaultSettings()
        var robotSettings = settings.getCustomSettings(RobotCodeCodeStyleSettings::class.java)
        val doc = editor.document
        val indentOptions = settings.getIndentOptionsByDocument(project, doc)
        
        val tabSize = indentOptions.INDENT_SIZE
        val spacesToAddCount: Int =
            if (robotSettings.use4SpacesIndentation) tabSize else tabSize - columnNumber % max(1, tabSize)
        
        var useTab = editor.settings.isUseTabCharacter(project)
        
        val chars = doc.charsSequence
        if (useTab && indentOptions.SMART_TABS) {
            var offset = editor.caretModel.offset
            while (offset > 0) {
                offset--
                if (chars[offset] == '\t') continue
                if (chars[offset] == '\n') break
                useTab = false
                break
            }
        }
        
        EditorModificationUtil.insertStringAtCaret(
            editor,
            if (useTab) "\t" else StringUtil.repeatSymbol(
                ' ',
                spacesToAddCount
            ),
            false,
            true
        )
    }
}

