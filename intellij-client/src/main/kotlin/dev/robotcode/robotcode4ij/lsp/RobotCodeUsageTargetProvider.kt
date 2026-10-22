package dev.robotcode.robotcode4ij.lsp

import com.intellij.find.findUsages.PsiElement2UsageTargetAdapter
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.fileEditor.FileEditorManager
import com.intellij.openapi.fileEditor.TextEditor
import com.intellij.psi.PsiDocumentManager
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiFile
import com.intellij.usages.UsageTarget
import com.intellij.usages.UsageTargetProvider
import com.redhat.devtools.lsp4ij.features.LSPPsiElement
import com.redhat.devtools.lsp4ij.usages.LSPUsageTriggeredPsiElement

/**
 * Lets Find Usages and Show Usages in a Robot Framework file search for the name at the caret as the language server
 * marks it. LSP4IJ takes the whole PSI element instead, such as `BuiltIn.Log` for `Log`, and searches from its start,
 * the library's name. Without a token at the caret, such as on a tag, LSP4IJ's own target is used.
 *
 * Find Usages prefers the targets of the element the name resolves to, LSP4IJ's `LSPPsiElement` at the definition.
 * On a resource import that is the start of the resource file, which has no usages. For that element the provider
 * also answers with the name at the caret of the selected editor.
 */
class RobotCodeUsageTargetProvider : UsageTargetProvider {
    override fun getTargets(editor: Editor, file: PsiFile): Array<UsageTarget>? {
        val tokens = file.viewProvider as? RobotCodeTokensFileViewProvider ?: return null
        val offset = editor.caretModel.offset
        // the caret right after a name belongs to it, as for the IDE's own targets
        val range = tokens.semanticTokenRangeAt(offset) ?: tokens.semanticTokenRangeAt(offset - 1) ?: return null
        return arrayOf(PsiElement2UsageTargetAdapter(LSPUsageTriggeredPsiElement(file, range), true))
    }

    override fun getTargets(element: PsiElement): Array<UsageTarget>? {
        // exactly the class of the resolved definition; usages, usage targets, the entries of the Structure tool
        // window and of Go to Symbol, and the calls in a hierarchy are subclasses or other classes
        if (element.javaClass != LSPPsiElement::class.java) return null
        val project = element.project
        // not getSelectedTextEditor(), which needs the EDT; usage targets are computed in a background read action
        val editor = (FileEditorManager.getInstance(project).selectedEditor as? TextEditor)?.editor ?: return null
        val file = PsiDocumentManager.getInstance(project).getPsiFile(editor.document) ?: return null
        return getTargets(editor, file)
    }
}
