package dev.robotcode.robotcode4ij.psi

import com.intellij.extapi.psi.ASTWrapperPsiElement
import com.intellij.lang.ASTNode
import com.intellij.psi.PsiComment
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiElementVisitor
import com.intellij.psi.tree.IElementType

open class SimpleASTWrapperPsiElement(tcNode: ASTNode) : ASTWrapperPsiElement(tcNode) {
    override fun getChildren(): Array<PsiElement> {
        return EMPTY_ARRAY
    }
    
    override fun getFirstChild(): PsiElement? {
        return null
    }
    
    override fun getLastChild(): PsiElement? {
        return null
    }
    
    override fun acceptChildren(visitor: PsiElementVisitor) {
    }
}

class TestCasePsiElement(private val tcNode: ASTNode) : SimpleASTWrapperPsiElement(tcNode) {
    override fun toString(): String {
        return "TestCase: ${tcNode.text}"
    }
}

open class CommentASTWrapperPsiElement(val commentNode: ASTNode) : SimpleASTWrapperPsiElement(commentNode), PsiComment {
    override fun getTokenType(): IElementType {
        return commentNode.elementType
    }
}

class LineCommentPsiElement(commentNode: ASTNode) : CommentASTWrapperPsiElement(commentNode) {
    override fun toString(): String {
        return "LineComment: ${commentNode.text}"
    }
}

class BlockCommentPsiElement(commentNode: ASTNode) : CommentASTWrapperPsiElement(commentNode) {
    override fun toString(): String {
        return "BlockComment: ${commentNode.text}"
    }
}

class ArgumentPsiElement(private val argumentNode: ASTNode) : SimpleASTWrapperPsiElement(argumentNode) {
    override fun toString(): String {
        return "Argument: ${argumentNode.text}"
    }
}
