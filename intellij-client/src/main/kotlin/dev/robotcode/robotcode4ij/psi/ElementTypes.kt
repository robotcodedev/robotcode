package dev.robotcode.robotcode4ij.psi

import com.intellij.psi.stubs.PsiFileStub
import com.intellij.psi.tree.IElementType
import com.intellij.psi.tree.IStubFileElementType
import com.intellij.psi.tree.TokenSet
import dev.robotcode.robotcode4ij.RobotFrameworkLanguage
import org.jetbrains.plugins.textmate.language.syntax.lexer.TextMateElementType

val FILE = IStubFileElementType<PsiFileStub<RobotFile>>("RobotFrameworkFile", RobotFrameworkLanguage)
val TESTCASE_NAME = IElementType("TESTCASE", RobotFrameworkLanguage)
val COMMENT_LINE = IElementType("COMMENT_LINE", RobotFrameworkLanguage)
val COMMENT_BLOCK = IElementType("COMMENT_BLOCK", RobotFrameworkLanguage)
val ARGUMENT = IElementType("ARGUMENT", RobotFrameworkLanguage)

val VARIABLE_BEGIN = IElementType("VARIABLE_BEGIN", RobotFrameworkLanguage)
val VARIABLE_END = IElementType("VARIABLE_END", RobotFrameworkLanguage)
val ENVIRONMENT_VARIABLE_BEGIN = IElementType("VARIABLE_BEGIN", RobotFrameworkLanguage)
val ENVIRONMENT_VARIABLE_END = IElementType("VARIABLE_END", RobotFrameworkLanguage)

val COMMENT_TOKENS = TokenSet.create(COMMENT_LINE, COMMENT_BLOCK)
val STRING_TOKENS = TokenSet.create(ARGUMENT)


class RobotTextMateElementType(
    val element: TextMateElementType, debugName: String = "ROBOT_TEXTMATE_ELEMENT_TYPE",
    register: Boolean = false
) :
    IElementType(
        debugName,
        RobotFrameworkLanguage,
        register
    )

