package dev.robotcode.robotcode4ij.lsp.features

import com.intellij.psi.PsiElement
import com.intellij.psi.util.elementType
import com.redhat.devtools.lsp4ij.client.features.LSPSemanticTokensFeature
import dev.robotcode.robotcode4ij.psi.IRobotFrameworkElementType

@Suppress("UnstableApiUsage") class RobotSemanticTokensFeature : LSPSemanticTokensFeature() {
    
    override fun isEligibleForSemanticHighlighting(element: PsiElement): Boolean {
        return element.elementType is IRobotFrameworkElementType
    }
}
