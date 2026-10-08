package dev.robotcode.robotcode4ij.lsp

import com.google.gson.JsonParser
import org.eclipse.lsp4j.Position
import org.eclipse.lsp4j.Range
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class RobotCodeShowDocumentArgumentsTest {

    private val uri = "file:///project/keywords.resource"
    private val range = """{"start": {"line": 4, "character": 0}, "end": {"line": 4, "character": 10}}"""

    private fun json(text: String) = JsonParser.parseString(text)

    @Test
    fun threeArguments() {
        val arguments = showDocumentArguments(listOf(json("\"$uri\""), json(range), json("false")))

        assertEquals(ShowDocumentArguments(uri, Range(Position(4, 0), Position(4, 10)), false), arguments)
    }

    @Test
    fun withoutTheRenameArgumentTheNewTextIsRenamed() {
        assertEquals(true, showDocumentArguments(listOf(json("\"$uri\""), json(range)))?.rename)
        assertEquals(true, showDocumentArguments(listOf(json("\"$uri\""), json(range), json("true")))?.rename)
    }

    @Test
    fun argumentsThatAreNotJson() {
        val arguments = showDocumentArguments(listOf(uri, Range(Position(1, 2), Position(1, 5)), false))

        assertEquals(ShowDocumentArguments(uri, Range(Position(1, 2), Position(1, 5)), false), arguments)
    }

    @Test
    fun missingOrBrokenArguments() {
        assertNull(showDocumentArguments(emptyList()))
        assertNull(showDocumentArguments(listOf(json("\"$uri\""))))
        assertNull(showDocumentArguments(listOf(json("\"$uri\""), json("\"not a range\""))))
    }
}
