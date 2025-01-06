package dev.robotcode.robotcode4ij.psi

import com.intellij.psi.stubs.PsiFileStub
import com.intellij.psi.tree.IElementType
import com.intellij.psi.tree.IStubFileElementType
import com.intellij.psi.tree.TokenSet
import dev.robotcode.robotcode4ij.RobotFrameworkLanguage
import org.jetbrains.plugins.textmate.language.syntax.lexer.TextMateScope

val FILE = IStubFileElementType<PsiFileStub<RobotSuiteFile>>("RobotFrameworkFile", RobotFrameworkLanguage)

class IRobotFrameworkElementType(debugName: String) : IElementType(debugName, RobotFrameworkLanguage)

val HEADER = IRobotFrameworkElementType("HEADER")
val SETTING = IRobotFrameworkElementType("SETTING")

val TESTCASE_NAME = IRobotFrameworkElementType("TESTCASE_NAME")
val KEYWORD_NAME = IRobotFrameworkElementType("TESTCASE_NAME")

val COMMENT_LINE = IRobotFrameworkElementType("COMMENT_LINE")
val COMMENT_BLOCK = IRobotFrameworkElementType("COMMENT_BLOCK")

val ARGUMENT = IRobotFrameworkElementType("ARGUMENT")

val VARIABLE_BEGIN = IRobotFrameworkElementType("VARIABLE_BEGIN")
val VARIABLE_END = IRobotFrameworkElementType("VARIABLE_END")
val EXPRESSION_VARIABLE_BEGIN = IRobotFrameworkElementType("EXPRESSION_VARIABLE_BEGIN")
val EXPRESSION_VARIABLE_END = IRobotFrameworkElementType("EXPRESSION_VARIABLE_END")
val ENVIRONMENT_VARIABLE_BEGIN = IRobotFrameworkElementType("VARIABLE_BEGIN")
val ENVIRONMENT_VARIABLE_END = IRobotFrameworkElementType("VARIABLE_END")

val KEYWORD_CALL = IRobotFrameworkElementType("KEYWORD_CALL")
val CONTROL_FLOW = IRobotFrameworkElementType("CONTROL_FLOW")
val VARIABLE = IRobotFrameworkElementType("VARIABLE")

val OPERATOR = IRobotFrameworkElementType("OPERATOR")
val CONTINUATION = IRobotFrameworkElementType("CONTINUATION")


val COMMENT_TOKENS = TokenSet.create(COMMENT_LINE, COMMENT_BLOCK)
val STRING_TOKENS = TokenSet.create(ARGUMENT)


class RobotTextMateElementType private constructor (
    val scope: TextMateScope,
    debugName: String = "ROBOT_TEXTMATE_ELEMENT_TYPE(${scope.scopeName})",
    register: Boolean = false
) : IElementType(
    debugName, RobotFrameworkLanguage, register
) {
    override fun toString(): String {
        return "RobotTextMateElementType($scope)"
    }
    
    override fun hashCode(): Int {
        return scope.hashCode()
    }
    
    override fun equals(other: Any?): Boolean {
        return other is RobotTextMateElementType && other.scope == scope
    }
    
    companion object {
        private val cache = mutableMapOf<TextMateScope, RobotTextMateElementType>()
        fun create(scope: TextMateScope?): RobotTextMateElementType {
            return cache.getOrPut(scope!!) {
                RobotTextMateElementType(scope, register = true)
            }
        }
    }
}

