package dev.robotcode.robotcode4ij.highlighting

import com.intellij.lexer.LexerBase
import com.intellij.openapi.util.registry.Registry
import com.intellij.psi.TokenType
import com.intellij.psi.tree.IElementType
import dev.robotcode.robotcode4ij.TextMateBundleHolder
import dev.robotcode.robotcode4ij.psi.ARGUMENT
import dev.robotcode.robotcode4ij.psi.COMMENT_BLOCK
import dev.robotcode.robotcode4ij.psi.COMMENT_LINE
import dev.robotcode.robotcode4ij.psi.CONTINUATION
import dev.robotcode.robotcode4ij.psi.CONTROL_FLOW
import dev.robotcode.robotcode4ij.psi.ENVIRONMENT_VARIABLE_BEGIN
import dev.robotcode.robotcode4ij.psi.ENVIRONMENT_VARIABLE_END
import dev.robotcode.robotcode4ij.psi.EXPRESSION_VARIABLE_BEGIN
import dev.robotcode.robotcode4ij.psi.EXPRESSION_VARIABLE_END
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
import org.jetbrains.plugins.textmate.language.syntax.lexer.TextMateLexer
import org.jetbrains.plugins.textmate.language.syntax.lexer.TextMateScope
import java.util.*
import kotlin.math.min

class RobotCodeLexer : LexerBase() {
    companion object {
        val mapping by lazy {
            mapOf(
                "comment.line.robotframework" to COMMENT_LINE,
                "comment.line.rest.robotframework" to COMMENT_LINE,
                "comment.block.robotframework" to COMMENT_BLOCK,
                
                "punctuation.definition.variable.begin.robotframework" to VARIABLE_BEGIN,
                "punctuation.definition.variable.end.robotframework" to VARIABLE_END,
                "punctuation.definition.envvar.begin.robotframework" to ENVIRONMENT_VARIABLE_BEGIN,
                "punctuation.definition.envvar.end.robotframework" to ENVIRONMENT_VARIABLE_END,
                "punctuation.definition.expression.begin.robotframework" to EXPRESSION_VARIABLE_BEGIN,
                "punctuation.definition.expression.end.robotframework" to EXPRESSION_VARIABLE_END,
                
                "entity.name.function.testcase.name.robotframework" to TESTCASE_NAME,
                "entity.name.function.keyword.name.robotframework" to KEYWORD_NAME,
                
                "keyword.other.header.robotframework" to HEADER,
                "keyword.other.header.settings.robotframework" to HEADER,
                "keyword.other.header.variable.robotframework" to HEADER,
                "keyword.other.header.testcase.robotframework" to HEADER,
                "keyword.other.header.task.robotframework" to HEADER,
                "keyword.other.header.keyword.robotframework" to HEADER,
                "keyword.other.header.comment.robotframework" to HEADER,
                
                "keyword.control.settings.robotframework" to SETTING,
                "keyword.control.settings.documentation.robotframework" to SETTING,
                
                "entity.name.function.keyword-call.robotframework" to KEYWORD_CALL,
                "keyword.control.flow.robotframework" to CONTROL_FLOW,
                
                "keyword.other.robotframework" to SETTING,
                
                "variable.name.readwrite.robotframework" to VARIABLE,
                "keyword.operator.robotframework" to OPERATOR,
                
                "constant.character.robotframework" to ARGUMENT,
                "string.unquoted.argument.robotframework" to ARGUMENT,
                
                "keyword.operator.continue.robotframework" to CONTINUATION,
                
                "punctuation.definition.variable.python.begin.robotframework" to VARIABLE_BEGIN,
            )
        }
    }
    
    
    private val myLexer =
        TextMateLexer(TextMateBundleHolder.descriptor, Registry.get("textmate.line.highlighting.limit").asInteger())
    private var currentLineTokens = LinkedList<TextMateLexer.Token?>()
    private lateinit var buffer: CharSequence
    private var endOffset = 0
    private var currentOffset = 0
    private var tokenType: IElementType? = null
    private var tokenStart = 0
    private var tokenEnd = 0
    private var restartable = false
    
    override fun start(buffer: CharSequence, startOffset: Int, endOffset: Int, initialState: Int) {
        this.buffer = buffer
        this.endOffset = endOffset
        this.currentOffset = startOffset
        this.endOffset = endOffset
        this.currentLineTokens.clear()
        this.restartable = initialState == 0
        myLexer.init(buffer, startOffset)
        this.advance()
    }
    
    override fun getState(): Int {
        return if (restartable) 0 else 1
    }
    
    override fun getTokenType(): IElementType? {
        return tokenType
    }
    
    override fun getTokenStart(): Int {
        return tokenStart
    }
    
    override fun getTokenEnd(): Int {
        return tokenEnd
    }
    
    override fun advance() {
        if (this.currentOffset >= this.endOffset) {
            this.updateState(null as TextMateLexer.Token?, this.endOffset)
        } else {
            if (currentLineTokens.isEmpty()) {
                myLexer.advanceLine(this.currentLineTokens)
            }
            
            this.updateState(
                currentLineTokens.poll(),
                myLexer.currentOffset
            )
        }
    }
    
    private fun updateState(token: TextMateLexer.Token?, fallbackOffset: Int) {
        if (token != null) {
            this.tokenType =
                (if (token.scope === TextMateScope.WHITESPACE) TokenType.WHITE_SPACE else mapping[token.scope.scopeName]
                    ?: RobotTextMateElementType.create(token.scope))
            
            tokenStart = token.startOffset
            tokenEnd = min(token.endOffset.toDouble(), endOffset.toDouble()).toInt()
            currentOffset = token.endOffset
            restartable = token.restartable
        } else {
            tokenType = null
            tokenStart = fallbackOffset
            tokenEnd = fallbackOffset
            currentOffset = fallbackOffset
            restartable = true
        }
    }
    
    override fun getBufferSequence(): CharSequence {
        return buffer
    }
    
    override fun getBufferEnd(): Int {
        return endOffset
    }
}


