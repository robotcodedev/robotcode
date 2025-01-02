package dev.robotcode.robotcode4ij.editor

import com.intellij.lang.Commenter

class RobotCodeCommenter : Commenter {
    override fun getLineCommentPrefix(): String {
        return "#"
    }
    
    override fun getBlockCommentPrefix(): String? {
        return null
    }
    
    override fun getBlockCommentSuffix(): String? {
        return null
    }
    
    override fun getCommentedBlockCommentPrefix(): String? {
        return null
    }
    
    override fun getCommentedBlockCommentSuffix(): String? {
        return null
    }
}
