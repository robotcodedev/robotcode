package dev.robotcode.robotcode4ij.lsp

import com.intellij.codeInsight.TargetElementEvaluatorEx2
import com.intellij.psi.PsiElement
import com.intellij.psi.impl.source.tree.LeafPsiElement
import com.redhat.devtools.lsp4ij.usages.LSPUsageTriggeredPsiElement

/**
 * Tells the IDE that the name of a keyword definition is a declaration, so that Ctrl+click and Navigate | Declaration
 * or Usages on it show the keyword's usages. RobotCode's PSI has only the leaves of the lexer, and LSP4IJ names
 * declarations only in files without a language of their own.
 *
 * The named element lies over the name as the language server marks it, like the target that Find Usages gets from
 * [RobotCodeUsageTargetProvider]. Test and task names and everything else get none.
 */
class RobotCodeTargetElementEvaluator : TargetElementEvaluatorEx2() {
    override fun getNamedElement(element: PsiElement): PsiElement? {
        if (element !is LeafPsiElement) return null
        val file = element.containingFile ?: return null
        val tokens = file.viewProvider as? RobotCodeTokensFileViewProvider ?: return null
        val name = tokens.keywordNameRangeIn(element.textRange) ?: return null
        return LSPUsageTriggeredPsiElement(file, name)
    }
}
