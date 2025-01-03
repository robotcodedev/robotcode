package dev.robotcode.robotcode4ij.highlighting

import com.intellij.openapi.editor.colors.EditorColorsScheme
import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.openapi.editor.ex.util.DataStorage
import com.intellij.openapi.editor.ex.util.LexerEditorHighlighter
import com.intellij.openapi.editor.highlighter.EditorHighlighter
import com.intellij.openapi.fileTypes.EditorHighlighterProvider
import com.intellij.openapi.fileTypes.FileType
import com.intellij.openapi.fileTypes.SyntaxHighlighter
import com.intellij.openapi.fileTypes.SyntaxHighlighterFactory
import com.intellij.openapi.project.Project
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.psi.tree.IElementType
import dev.robotcode.robotcode4ij.psi.ARGUMENT
import dev.robotcode.robotcode4ij.psi.COMMENT_BLOCK
import dev.robotcode.robotcode4ij.psi.COMMENT_LINE
import dev.robotcode.robotcode4ij.psi.CONTINUATION
import dev.robotcode.robotcode4ij.psi.CONTROL_FLOW
import dev.robotcode.robotcode4ij.psi.ENVIRONMENT_VARIABLE_BEGIN
import dev.robotcode.robotcode4ij.psi.ENVIRONMENT_VARIABLE_END
import dev.robotcode.robotcode4ij.psi.HEADER
import dev.robotcode.robotcode4ij.psi.KEYWORD_CALL
import dev.robotcode.robotcode4ij.psi.KEYWORD_NAME
import dev.robotcode.robotcode4ij.psi.OPERATOR
import dev.robotcode.robotcode4ij.psi.RobotTextMateElementType
import dev.robotcode.robotcode4ij.psi.SETTING
import dev.robotcode.robotcode4ij.psi.TESTCASE_NAME
import dev.robotcode.robotcode4ij.psi.VARIABLE
import dev.robotcode.robotcode4ij.psi.VARIABLE_BEGIN
import dev.robotcode.robotcode4ij.psi.VARIABLE_END
import org.jetbrains.plugins.textmate.language.syntax.highlighting.TextMateHighlighter
import org.jetbrains.plugins.textmate.language.syntax.lexer.TextMateLexerDataStorage

class RobotCodeHighlighterProvider : EditorHighlighterProvider {
    override fun getEditorHighlighter(
        project: Project?, fileType: FileType, virtualFile: VirtualFile?, colors: EditorColorsScheme
    ): EditorHighlighter {
        val highlighter = SyntaxHighlighterFactory.getSyntaxHighlighter(fileType, project, virtualFile)
        return RobotCodeEditorHighlighter(highlighter, colors)
    }
}

class RobotCodeHighlighter : TextMateHighlighter(RobotTextMateHighlightingLexer()) {
    companion object {
        val elementTypeMap = mapOf(
            COMMENT_LINE to arrayOf(RobotColors.LINE_COMMENT),
            COMMENT_BLOCK to arrayOf(RobotColors.BLOCK_COMMENT),
            VARIABLE_BEGIN to arrayOf(RobotColors.VARIABLE_BEGIN),
            VARIABLE_END to arrayOf(RobotColors.VARIABLE_END),
            ENVIRONMENT_VARIABLE_BEGIN to arrayOf(RobotColors.VARIABLE_BEGIN),
            ENVIRONMENT_VARIABLE_END to arrayOf(RobotColors.VARIABLE_END),
            TESTCASE_NAME to arrayOf(RobotColors.TESTCASE_NAME),
            KEYWORD_NAME to arrayOf(RobotColors.KEYWORD_NAME),
            HEADER to arrayOf(RobotColors.HEADER),
            SETTING to arrayOf(RobotColors.SETTING),
            KEYWORD_CALL to arrayOf(RobotColors.KEYWORD_CALL),
            CONTROL_FLOW to arrayOf(RobotColors.CONTROL_FLOW),
            VARIABLE to arrayOf(RobotColors.VARIABLE),
            OPERATOR to arrayOf(RobotColors.OPERATOR),
            ARGUMENT to arrayOf(RobotColors.ARGUMENT),
            CONTINUATION to arrayOf(RobotColors.CONTINUATION),
        )
    }
    
    override fun getTokenHighlights(tokenType: IElementType?): Array<TextAttributesKey> {
        if (tokenType in elementTypeMap) {
            val result = elementTypeMap[tokenType]
            if (result != null) return result
        }
        return super.getTokenHighlights(tokenType)
    }
}

class RobotCodeEditorHighlighter(highlighter: SyntaxHighlighter?, scheme: EditorColorsScheme) :
    LexerEditorHighlighter(highlighter ?: RobotCodeHighlighter(), scheme) {
    
    override fun createStorage(): DataStorage {
        return TextMateLexerDataStorage()
    }
    
}
