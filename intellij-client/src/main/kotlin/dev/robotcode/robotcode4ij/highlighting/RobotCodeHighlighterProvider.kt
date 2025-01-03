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
import dev.robotcode.robotcode4ij.psi.ENVIRONMENT_VARIABLE_BEGIN
import dev.robotcode.robotcode4ij.psi.ENVIRONMENT_VARIABLE_END
import dev.robotcode.robotcode4ij.psi.RobotTextMateElementType
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
        val elementMap = mapOf(
            "comment.line.robotframework" to arrayOf(RobotColors.LINE_COMMENT),
            "comment.line.rest.robotframework" to arrayOf(RobotColors.LINE_COMMENT),
            "comment.block.robotframework" to arrayOf(RobotColors.BLOCK_COMMENT),
            "keyword.other.header.robotframework" to arrayOf(RobotColors.HEADER),
            "keyword.other.header.settings.robotframework" to arrayOf(RobotColors.HEADER),
            "keyword.other.header.variable.robotframework" to arrayOf(RobotColors.HEADER),
            "keyword.other.header.testcase.robotframework" to arrayOf(RobotColors.HEADER),
            "keyword.other.header.task.robotframework" to arrayOf(RobotColors.HEADER),
            "keyword.other.header.keyword.robotframework" to arrayOf(RobotColors.HEADER),
            "keyword.other.header.comment.robotframework" to arrayOf(RobotColors.HEADER),
            
            "keyword.control.settings.robotframework" to arrayOf(RobotColors.SETTING),
            "keyword.control.settings.documentation.robotframework" to arrayOf(RobotColors.SETTING),
            
            "entity.name.function.testcase.name.robotframework" to arrayOf(RobotColors.TESTCASE_NAME),
            "entity.name.function.keyword.name.robotframework" to arrayOf(RobotColors.KEYWORD_NAME),
            "entity.name.function.keyword-call.robotframework" to arrayOf(RobotColors.KEYWORD_CALL),
            "keyword.control.flow.robotframework" to arrayOf(RobotColors.CONTROL_FLOW),
            "keyword.other.robotframework" to arrayOf(RobotColors.SETTING),
            "punctuation.definition.variable.begin.robotframework" to arrayOf(RobotColors.VARIABLE_BEGIN),
            "punctuation.definition.variable.end.robotframework" to arrayOf(RobotColors.VARIABLE_END),
            "variable.name.readwrite.robotframework" to arrayOf(RobotColors.VARIABLE),
            "punctuation.definition.envvar.begin.robotframework" to arrayOf(RobotColors.VARIABLE_BEGIN),
            "punctuation.definition.envvar.end.robotframework" to arrayOf(RobotColors.VARIABLE_END),
            "keyword.operator.robotframework" to arrayOf(RobotColors.OPERATOR),
            "constant.character.robotframework" to arrayOf(RobotColors.ARGUMENT),
            "string.unquoted.argument.robotframework" to arrayOf(RobotColors.ARGUMENT),
            "keyword.operator.continue.robotframework" to arrayOf(RobotColors.CONTINUATION),
        )
        val elementTypeMap = mapOf(
            VARIABLE_BEGIN to arrayOf(RobotColors.VARIABLE_BEGIN),
            VARIABLE_END to arrayOf(RobotColors.VARIABLE_END),
            ENVIRONMENT_VARIABLE_BEGIN to arrayOf(RobotColors.VARIABLE_BEGIN),
            ENVIRONMENT_VARIABLE_END to arrayOf(RobotColors.VARIABLE_END),
        )
    }
    
    override fun getTokenHighlights(tokenType: IElementType?): Array<TextAttributesKey> {
        if (tokenType is RobotTextMateElementType) {
            val result = elementMap[tokenType.element.scope.scopeName]
            if (result != null) return result
        }
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
