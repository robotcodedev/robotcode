package dev.robotcode.robotcode4ij.lsp

import com.intellij.psi.ElementDescriptionLocation
import com.intellij.psi.ElementDescriptionProvider
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiFile
import com.intellij.psi.util.elementType
import com.intellij.usageView.UsageViewLongNameLocation
import com.intellij.usageView.UsageViewTypeLocation
import com.redhat.devtools.lsp4ij.features.LSPPsiElement
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.RobotFrameworkLanguage
import dev.robotcode.robotcode4ij.psi.KEYWORD_CALL
import dev.robotcode.robotcode4ij.psi.KEYWORD_NAME
import dev.robotcode.robotcode4ij.psi.VARIABLE

/**
 * Names what Show Usages and Find Usages search for in a Robot Framework file: by its kind, such as keyword, and by its
 * name as written. LSP4IJ describes only its own elements and gives up where it finds RobotCode's PSI, so the IDE
 * would show the class name of LSP4IJ's element instead.
 */
class RobotCodeUsageDescriptionProvider : ElementDescriptionProvider {
    override fun getElementDescription(element: PsiElement, location: ElementDescriptionLocation): String? {
        if (element !is LSPPsiElement) return null
        val file = element.containingFile ?: return null
        if (file.language != RobotFrameworkLanguage) return null
        return when (location) {
            is UsageViewTypeLocation -> RobotCodeBundle.message(kindAt(file, element.textOffset))
            // the name in the element's range: a variable's token holds its name without `${` and `}`
            is UsageViewLongNameLocation -> element.text
            else -> null
        }
    }
}

private val kindsOfTokenTypes = mapOf(
    "keywordCall" to "usages.kind.keyword",
    "keywordCallInner" to "usages.kind.keyword",
    "keywordName" to "usages.kind.keyword",
    "bddPrefix" to "usages.kind.keyword",
    "parameter" to "usages.kind.argument",
    "variable" to "usages.kind.variable",
    "namespace" to "usages.kind.namespace",
)

// the language server's token knows the kind; without one, the lexer tells keywords and variables apart
private fun kindAt(file: PsiFile, offset: Int): String {
    (file.viewProvider as? RobotCodeTokensFileViewProvider)?.semanticTokenTypeAt(offset)
        ?.let { type -> kindsOfTokenTypes[type]?.let { return it } }
    return when (file.findElementAt(offset).elementType) {
        KEYWORD_CALL, KEYWORD_NAME -> "usages.kind.keyword"
        VARIABLE -> "usages.kind.variable"
        else -> "usages.kind.symbol"
    }
}
