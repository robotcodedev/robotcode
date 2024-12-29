package dev.robotcode.robotcode4ij

import com.intellij.extapi.psi.PsiFileBase
import com.intellij.lang.ASTNode
import com.intellij.lang.ParserDefinition
import com.intellij.lang.PsiBuilder
import com.intellij.lang.PsiParser
import com.intellij.lexer.EmptyLexer
import com.intellij.lexer.Lexer
import com.intellij.openapi.fileTypes.FileType
import com.intellij.openapi.project.Project
import com.intellij.openapi.util.registry.Registry
import com.intellij.psi.FileViewProvider
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiFile
import com.intellij.psi.impl.source.tree.CompositePsiElement
import com.intellij.psi.stubs.PsiFileStub
import com.intellij.psi.tree.IElementType
import com.intellij.psi.tree.IFileElementType
import com.intellij.psi.tree.IStubFileElementType
import com.intellij.psi.tree.TokenSet
import org.jetbrains.plugins.textmate.TextMateService
import org.jetbrains.plugins.textmate.language.syntax.lexer.TextMateHighlightingLexer

val FILE = IStubFileElementType<PsiFileStub<RobotFile>>("RobotSuiteFile", RobotFrameworkLanguage)

class RobotCodeParserDefinition : ParserDefinition {
    
    override fun createLexer(project: Project?): Lexer {
        val descriptor = TextMateService.getInstance().getLanguageDescriptorByExtension("robot")
        if (descriptor != null) {
            
            return TextMateHighlightingLexer(
                descriptor,
                Registry.get("textmate.line.highlighting.limit").asInteger()
            )
        }
        return EmptyLexer()
    }
    
    override fun createParser(project: Project?): PsiParser {
        return RobotPsiParser()
    }
    
    override fun getFileNodeType(): IFileElementType {
        return FILE
    }
    
    override fun getCommentTokens(): TokenSet {
        return TokenSet.EMPTY
    }
    
    override fun getStringLiteralElements(): TokenSet {
        return TokenSet.EMPTY
    }
    
    override fun createElement(node: ASTNode): PsiElement {
        return RobotPsiElement(node.elementType)
    }
    
    override fun createFile(viewProvider: FileViewProvider): PsiFile {
        return RobotFile(viewProvider)
    }
}

class RobotFile(viewProvider: FileViewProvider) : PsiFileBase(viewProvider, RobotFrameworkLanguage) {
    override fun getFileType(): FileType {
        return RobotSuiteFileType
    }
}

class RobotPsiParser : PsiParser {
    override fun parse(root: IElementType, builder: PsiBuilder): ASTNode {
        val mark = builder.mark()
        while (!builder.eof()) {
            builder.advanceLexer()
        }
        mark.done(root)
        
        return builder.treeBuilt
    }
}

class RobotPsiElement(type: IElementType) : CompositePsiElement(type)
