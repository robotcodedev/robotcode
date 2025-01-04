package dev.robotcode.robotcode4ij.editor

import com.intellij.lang.BracePair
import com.intellij.lang.PairedBraceMatcher
import com.intellij.psi.PsiFile
import com.intellij.psi.tree.IElementType
import dev.robotcode.robotcode4ij.psi.ENVIRONMENT_VARIABLE_BEGIN
import dev.robotcode.robotcode4ij.psi.ENVIRONMENT_VARIABLE_END
import dev.robotcode.robotcode4ij.psi.VARIABLE_BEGIN
import dev.robotcode.robotcode4ij.psi.VARIABLE_END

private val PAIRS = arrayOf(
    BracePair(VARIABLE_BEGIN, VARIABLE_END, false),
    BracePair(ENVIRONMENT_VARIABLE_BEGIN, ENVIRONMENT_VARIABLE_END, false)
)

class RobotCodeBraceMatcher : PairedBraceMatcher {
    
    override fun getPairs(): Array<BracePair> {
        return PAIRS
    }
    
    override fun isPairedBracesAllowedBeforeType(lbraceType: IElementType, contextType: IElementType?): Boolean {
        return true
    }
    
    override fun getCodeConstructStart(file: PsiFile?, openingBraceOffset: Int): Int {
        return openingBraceOffset
    }
}
