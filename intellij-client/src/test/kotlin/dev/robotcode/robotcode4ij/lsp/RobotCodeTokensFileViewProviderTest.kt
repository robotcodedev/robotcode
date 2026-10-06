package dev.robotcode.robotcode4ij.lsp

import com.intellij.openapi.util.TextRange
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class RobotCodeTokensFileViewProviderTest {

    // `    common.Start Case    Start` with `common` at 4..10 and `Start Case` at 11..21
    private val namespace = TextRange(4, 10)
    private val keyword = TextRange(11, 21)
    private val wholeCall = TextRange(4, 21)

    private fun tokensAt(vararg ranges: TextRange): (Int) -> TextRange? = { offset ->
        ranges.firstOrNull { it.startOffset <= offset && offset < it.endOffset }
    }

    @Test
    fun tokenAddedAfterGoToDeclarationDoesNotHideServerTokens() {
        assertTrue(hidesServerTokens(wholeCall, null, tokensAt(namespace, keyword)))
    }

    @Test
    fun tokenAddedAfterGoToDeclarationWhereTheServerSentNone() {
        assertFalse(hidesServerTokens(wholeCall, null, tokensAt()))
    }

    @Test
    fun serverTokensAreAlwaysAdded() {
        assertFalse(hidesServerTokens(keyword, emptyList<String>(), tokensAt(wholeCall)))
        assertFalse(hidesServerTokens(keyword, listOf("declaration"), tokensAt(keyword)))
    }
}
