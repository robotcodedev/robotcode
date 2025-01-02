package dev.robotcode.robotcode4ij.editor

import com.intellij.psi.impl.cache.CommentTokenSetProvider
import com.intellij.psi.tree.IElementType
import dev.robotcode.robotcode4ij.psi.RobotTextMateElementType

val COMMENT_SCOPES = setOf(
    "comment.line.robotframework",
    "comment.line.rest.robotframework",
    "comment.block.robotframework",
)

class RobotCodeCommentTokenSetProvider : CommentTokenSetProvider {
    override fun isInComments(elementType: IElementType?): Boolean {
        val scopeName = (elementType as? RobotTextMateElementType)?.element?.scope?.scopeName
        return COMMENT_SCOPES.contains(scopeName)
    }
}
