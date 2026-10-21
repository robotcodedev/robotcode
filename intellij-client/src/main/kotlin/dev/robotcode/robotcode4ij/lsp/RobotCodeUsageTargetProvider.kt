package dev.robotcode.robotcode4ij.lsp

import com.intellij.find.findUsages.PsiElement2UsageTargetAdapter
import com.intellij.openapi.editor.Editor
import com.intellij.psi.PsiFile
import com.intellij.usages.UsageTarget
import com.intellij.usages.UsageTargetProvider
import com.redhat.devtools.lsp4ij.usages.LSPUsageTriggeredPsiElement

/**
 * Lets Find Usages and Show Usages in a Robot Framework file search for the name at the caret as the language server
 * marks it. LSP4IJ takes the whole PSI element instead, such as `BuiltIn.Log` for `Log`, and searches from its start,
 * the library's name. Without a token at the caret, such as on a tag, LSP4IJ's own target is used.
 */
class RobotCodeUsageTargetProvider : UsageTargetProvider {
    override fun getTargets(editor: Editor, file: PsiFile): Array<UsageTarget>? {
        val tokens = file.viewProvider as? RobotCodeTokensFileViewProvider ?: return null
        val offset = editor.caretModel.offset
        // the caret right after a name belongs to it, as for the IDE's own targets
        val range = tokens.semanticTokenRangeAt(offset) ?: tokens.semanticTokenRangeAt(offset - 1) ?: return null
        return arrayOf(PsiElement2UsageTargetAdapter(LSPUsageTriggeredPsiElement(file, range), true))
    }
}
