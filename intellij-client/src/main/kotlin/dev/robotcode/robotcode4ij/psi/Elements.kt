package dev.robotcode.robotcode4ij.psi

import com.intellij.extapi.psi.ASTWrapperPsiElement
import com.intellij.lang.ASTNode
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiElementVisitor

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

