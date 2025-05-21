package dev.robotcode.robotcode4ij.psi

import com.intellij.extapi.psi.ASTWrapperPsiElement
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
import dev.robotcode.robotcode4ij.RobotResourceFileType
import dev.robotcode.robotcode4ij.RobotSuiteFileType
import dev.robotcode.robotcode4ij.highlighting.RobotCodeLexer

class RobotCodeParserDefinition : ParserDefinition {
    
    override fun createLexer(project: Project?): Lexer {
        return RobotCodeLexer()
    }
    
    override fun createParser(project: Project?): PsiParser {
        return RobotPsiParser()
    }
    
    override fun getFileNodeType(): IFileElementType {
        return FILE
    }
    
    override fun getCommentTokens(): TokenSet {
        return COMMENT_TOKENS
    }
    
    override fun getStringLiteralElements(): TokenSet {
        return STRING_TOKENS
    }
    
    override fun createElement(node: ASTNode): PsiElement {
        return when (node.elementType) {
            is IRobotFrameworkElementType -> ASTWrapperPsiElement(node)
            
            else -> throw IllegalArgumentException("Unknown element type: ${node.elementType}")
        }
    }
    
    override fun createFile(viewProvider: FileViewProvider): PsiFile {
        return when (viewProvider.fileType) {
            RobotSuiteFileType -> RobotSuiteFile(viewProvider)
            RobotResourceFileType -> RobotResourceFile(viewProvider)
            else -> throw IllegalArgumentException("Invalid file type: ${viewProvider.fileType}")
        }
    }
}

