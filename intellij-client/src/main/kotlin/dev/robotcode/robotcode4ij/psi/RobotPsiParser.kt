package dev.robotcode.robotcode4ij.psi

import com.intellij.lang.ASTNode
import com.intellij.lang.LightPsiParser
import com.intellij.lang.PsiBuilder
import com.intellij.lang.PsiParser
import com.intellij.psi.tree.IElementType

class RobotPsiParser : PsiParser, LightPsiParser {
    companion object {
        val ELEMENT_MAP = mapOf(
            "entity.name.function.testcase.name.robotframework" to TESTCASE_NAME,
            // "comment.block.robotframework" to COMMENT_BLOCK,
            // "comment.line.robotframework" to COMMENT_LINE,
            // "string.unquoted.argument.robotframework" to ARGUMENT
        )
    }
    
    override fun parse(root: IElementType, builder: PsiBuilder): ASTNode {
        parseLight(root, builder)
        return builder.treeBuilt
    }
    
    override fun parseLight(root: IElementType, builder: PsiBuilder) {
        val mark = builder.mark()
        while (!builder.eof()) {
            val tokenType = builder.tokenType as? RobotTextMateElementType
            ELEMENT_MAP[tokenType?.element?.scope?.scopeName]?.let {
                val token = builder.mark()
                builder.advanceLexer()
                token.done(it)
            } ?: run {
                val tokenType1 = builder.tokenType
                if (tokenType1 != null) {
                    val token = builder.mark()
                    builder.advanceLexer()
                    token.done(tokenType1)
                } else {
                    builder.advanceLexer()
                }
            }
            
        }
        mark.done(root)
    }
}
