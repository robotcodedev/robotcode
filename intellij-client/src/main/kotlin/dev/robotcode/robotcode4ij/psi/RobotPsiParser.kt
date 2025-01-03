package dev.robotcode.robotcode4ij.psi

import com.intellij.lang.ASTNode
import com.intellij.lang.LightPsiParser
import com.intellij.lang.PsiBuilder
import com.intellij.lang.PsiParser
import com.intellij.psi.tree.IElementType

class RobotPsiParser : PsiParser, LightPsiParser {
    override fun parse(root: IElementType, builder: PsiBuilder): ASTNode {
        parseLight(root, builder)
        return builder.treeBuilt
    }
    
    override fun parseLight(root: IElementType, builder: PsiBuilder) {
        val mark = builder.mark()
        while (!builder.eof()) {
            (builder.tokenType as? IRobotFrameworkElementType)?.let {
                val token = builder.mark()
                builder.advanceLexer()
                token.done(it)
            } ?: run {
                builder.advanceLexer()
            }
            
        }
        mark.done(root)
    }
}
