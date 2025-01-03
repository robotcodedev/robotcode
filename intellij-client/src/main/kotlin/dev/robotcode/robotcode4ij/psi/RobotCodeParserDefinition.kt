package dev.robotcode.robotcode4ij.psi

import com.intellij.lang.ASTNode
import com.intellij.lang.ParserDefinition
import com.intellij.lang.PsiParser
import com.intellij.lexer.Lexer
import com.intellij.openapi.project.Project
import com.intellij.psi.FileViewProvider
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiFile
import com.intellij.psi.tree.IFileElementType
import com.intellij.psi.tree.TokenSet
import dev.robotcode.robotcode4ij.highlighting.RobotTextMateHighlightingLexer

class RobotCodeParserDefinition : ParserDefinition {
    
    override fun createLexer(project: Project?): Lexer {
        return RobotTextMateHighlightingLexer()
    }
    
    override fun createParser(project: Project?): PsiParser {
        return RobotPsiParser()
    }
    
    override fun getFileNodeType(): IFileElementType {
        return FILE
    }
    
    override fun getCommentTokens(): TokenSet {
        // return COMMENT_TOKENS
        return TokenSet.EMPTY
    }
    
    override fun getStringLiteralElements(): TokenSet {
        // return STRING_TOKENS
        return TokenSet.EMPTY
    }
    
    override fun createElement(node: ASTNode): PsiElement {
        return when (node.elementType) {
            // COMMENT_LINE -> LineCommentPsiElement(node)
            // COMMENT_BLOCK -> BlockCommentPsiElement(node)
            // ARGUMENT -> ArgumentPsiElement(node)
            TESTCASE_NAME -> TestCasePsiElement(node)
            is RobotTextMateElementType -> SimpleASTWrapperPsiElement(node)
            VARIABLE_BEGIN, VARIABLE_END -> SimpleASTWrapperPsiElement(node)
            ENVIRONMENT_VARIABLE_BEGIN, ENVIRONMENT_VARIABLE_END -> SimpleASTWrapperPsiElement(node)
            
            else -> throw IllegalArgumentException("Unknown element type: ${node.elementType}")
        }
    }
    
    override fun createFile(viewProvider: FileViewProvider): PsiFile {
        return RobotFile(viewProvider)
    }
}

