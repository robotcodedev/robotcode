package dev.robotcode.robotcode4ij.lsp

import com.google.gson.Gson
import com.google.gson.JsonElement
import com.google.gson.JsonParseException
import com.intellij.openapi.actionSystem.ActionManager
import com.intellij.openapi.actionSystem.ActionPlaces
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.IdeActions
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.editor.ScrollType
import com.intellij.openapi.fileEditor.FileEditorManager
import com.intellij.openapi.fileEditor.OpenFileDescriptor
import com.intellij.openapi.project.Project
import com.intellij.psi.PsiDocumentManager
import com.redhat.devtools.lsp4ij.LSPIJUtils
import com.redhat.devtools.lsp4ij.commands.LSPCommand
import com.redhat.devtools.lsp4ij.commands.LSPCommandAction
import org.eclipse.lsp4j.Range

/**
 * The arguments of `_robotcode.codeActionShowDocumentSelectAndRename`: the document, the range to select in it, and
 * whether to rename at it, which is the default when the argument is missing.
 */
internal data class ShowDocumentArguments(val uri: String, val range: Range, val rename: Boolean)

private val gson = Gson()

internal fun showDocumentArguments(arguments: List<Any?>): ShowDocumentArguments? {
    fun tree(index: Int): JsonElement? {
        val argument = arguments.getOrNull(index) ?: return null
        return (argument as? JsonElement ?: gson.toJsonTree(argument)).takeUnless { it.isJsonNull }
    }
    return try {
        val uri = tree(0)?.takeIf { it.isJsonPrimitive }?.asString ?: return null
        val range = tree(1)?.let { gson.fromJson(it, Range::class.java) } ?: return null
        if (range.start == null || range.end == null) {
            return null
        }
        val rename = tree(2)?.takeIf { it.isJsonPrimitive }?.asBoolean ?: true
        ShowDocumentArguments(uri, range, rename)
    } catch (_: JsonParseException) {
        null
    }
}

/**
 * Carries out the client command with which RobotCode's quick fixes and refactorings ask the editor to show the text
 * they inserted: after the edit, it opens the document, selects the range from its end to its start, as VS Code does,
 * and starts renaming at it when asked to.
 */
class RobotCodeShowDocumentSelectAndRenameAction : LSPCommandAction() {
    override fun commandPerformed(command: LSPCommand, e: AnActionEvent) {
        val project = e.project ?: return
        val arguments = showDocumentArguments(command.arguments) ?: return
        // runs after the write action of the intention that applied the edit
        ApplicationManager.getApplication().invokeLater({ showAndSelect(project, arguments) }, project.disposed)
    }

    private fun showAndSelect(project: Project, arguments: ShowDocumentArguments) {
        PsiDocumentManager.getInstance(project).commitAllDocuments()
        val file = LSPIJUtils.findResourceFor(arguments.uri) ?: return
        val editor = FileEditorManager.getInstance(project).openTextEditor(OpenFileDescriptor(project, file), true)
            ?: return
        val start = LSPIJUtils.toOffset(arguments.range.start, editor.document)
        val end = LSPIJUtils.toOffset(arguments.range.end, editor.document)
        editor.caretModel.moveToOffset(start)
        editor.selectionModel.setSelection(start, end)
        editor.scrollingModel.scrollToCaret(ScrollType.MAKE_VISIBLE)
        if (arguments.rename) {
            val actionManager = ActionManager.getInstance()
            actionManager.tryToExecute(
                actionManager.getAction(IdeActions.ACTION_RENAME), null, editor.contentComponent, ActionPlaces.UNKNOWN,
                true
            )
        }
    }
}
