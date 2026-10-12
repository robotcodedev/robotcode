package dev.robotcode.robotcode4ij.debugging

import com.intellij.codeInsight.AutoPopupController
import com.intellij.codeInsight.completion.CompletionContributor
import com.intellij.codeInsight.completion.CompletionParameters
import com.intellij.codeInsight.completion.CompletionResultSet
import com.intellij.codeInsight.completion.PlainPrefixMatcher
import com.intellij.codeInsight.lookup.LookupElement
import com.intellij.codeInsight.editorActions.TypedHandlerDelegate
import com.intellij.codeInsight.lookup.LookupElementBuilder
import com.intellij.icons.AllIcons
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.project.Project
import com.intellij.psi.PsiFile
import com.intellij.xdebugger.XDebuggerManager
import org.eclipse.lsp4j.debug.CompletionItem
import org.eclipse.lsp4j.debug.CompletionItemType

/**
 * Completes the debugger's expression editors and console with the keywords, libraries, resources and variables that
 * the RobotCode debugger reports for the selected frame of a paused run.
 */
class RobotCodeDebuggerCompletionContributor : CompletionContributor() {
    override fun fillCompletionVariants(parameters: CompletionParameters, result: CompletionResultSet) {
        val file = parameters.originalFile
        if (file.getUserData(DEBUGGER_EXPRESSION_FILE) != true) return
        val session = XDebuggerManager.getInstance(file.project).currentSession ?: return
        val process = session.debugProcess as? RobotCodeDebugProcess ?: return
        val frame = session.currentStackFrame as? RobotCodeStackFrame ?: return
        if (!session.isSuspended) return

        val text = parameters.editor.document.text
        val items = process.completions(frame.frame.id, text, parameters.offset) ?: return
        // the debugger answers with everything it knows, whatever the text, so the cell before the caret filters
        val matching = result.withPrefixMatcher(PlainPrefixMatcher(cellPrefix(text, parameters.offset), true))
        items.forEach { matching.addElement(lookupElementOf(it)) }
    }
}

/**
 * Opens the completion list of the debugger's expression editors and console when `{` is typed after a variable sign,
 * as the language server's trigger character `{` does in the editor.
 */
class RobotCodeDebuggerTypedHandler : TypedHandlerDelegate() {
    override fun checkAutoPopup(charTyped: Char, project: Project, editor: Editor, file: PsiFile): Result {
        if (charTyped != '{' || file.getUserData(DEBUGGER_EXPRESSION_FILE) != true) return Result.CONTINUE
        val offset = editor.caretModel.offset
        if (offset == 0 || editor.document.charsSequence[offset - 1] !in "$@&%") return Result.CONTINUE
        AutoPopupController.getInstance(project).scheduleAutoPopup(editor)
        return Result.STOP
    }
}

/**
 * The text before [offset] that the items must start with: the innermost variable still open in the cell before [offset],
 * such as `${me` in `value is ${me`, or else that cell. Robot Framework separates cells by two or more spaces, a tab or a
 * line break.
 */
internal fun cellPrefix(text: String, offset: Int): String {
    var start = offset
    while (start > 0) {
        val char = text[start - 1]
        if (char == '\n' || char == '\r' || char == '\t' || (char == ' ' && start >= 2 && text[start - 2] == ' ')) break
        start--
    }
    val cell = text.substring(start, offset)
    val brace = cell.lastIndexOf('{')
    return if (brace >= 1 && cell[brace - 1] in "$@&%" && '}' !in cell.substring(brace)) cell.substring(brace - 1) else cell
}

/** A lookup element for a completion item of the debugger, with an icon for its kind and its detail as tail text. */
internal fun lookupElementOf(item: CompletionItem): LookupElement {
    val icon = when (item.type) {
        CompletionItemType.FUNCTION -> AllIcons.Nodes.Function
        CompletionItemType.VARIABLE -> AllIcons.Nodes.Variable
        // libraries and resources
        CompletionItemType.MODULE -> AllIcons.Nodes.Module
        else -> null
    }
    return LookupElementBuilder.create(item.text ?: item.label)
        .withPresentableText(item.label)
        .withIcon(icon)
        .withTailText(item.detail?.let { " $it" }, true)
}
