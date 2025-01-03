package dev.robotcode.robotcode4ij.psi

import com.intellij.psi.stubs.PsiFileStub
import com.intellij.psi.tree.IElementType
import com.intellij.psi.tree.IStubFileElementType
import com.intellij.psi.tree.TokenSet
import dev.robotcode.robotcode4ij.RobotFrameworkLanguage
import org.jetbrains.plugins.textmate.language.syntax.lexer.TextMateElementType

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
val ENVIRONMENT_VARIABLE_BEGIN = IRobotFrameworkElementType("VARIABLE_BEGIN")
val ENVIRONMENT_VARIABLE_END = IRobotFrameworkElementType("VARIABLE_END")

val KEYWORD_CALL = IRobotFrameworkElementType("KEYWORD_CALL")
val CONTROL_FLOW = IRobotFrameworkElementType("CONTROL_FLOW")
val VARIABLE = IRobotFrameworkElementType("VARIABLE")

val OPERATOR = IRobotFrameworkElementType("OPERATOR")
val CONTINUATION = IRobotFrameworkElementType("CONTINUATION")


val COMMENT_TOKENS = TokenSet.create(COMMENT_LINE, COMMENT_BLOCK)
val STRING_TOKENS = TokenSet.create(ARGUMENT)


class RobotTextMateElementType(
    val element: TextMateElementType, debugName: String = "ROBOT_TEXTMATE_ELEMENT_TYPE", register: Boolean = false
) : IElementType(
    debugName, RobotFrameworkLanguage, register
)

