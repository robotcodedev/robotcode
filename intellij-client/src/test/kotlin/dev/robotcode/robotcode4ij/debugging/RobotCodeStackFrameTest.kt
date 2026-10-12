package dev.robotcode.robotcode4ij.debugging

import com.intellij.ui.ColoredTextContainer
import com.intellij.ui.SimpleTextAttributes
import com.intellij.ui.SimpleTextAttributes.GRAYED_ATTRIBUTES
import com.intellij.ui.SimpleTextAttributes.REGULAR_ATTRIBUTES
import org.eclipse.lsp4j.debug.Source
import org.eclipse.lsp4j.debug.StackFrame
import org.eclipse.lsp4j.debug.StackFramePresentationHint
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import javax.swing.Icon

class RobotCodeStackFrameTest {

    // records what a frame renders in the Frames view
    private class Recorder : ColoredTextContainer {
        val fragments = mutableListOf<Pair<String, SimpleTextAttributes>>()
        var frameIcon: Icon? = null

        override fun append(fragment: String, attributes: SimpleTextAttributes) {
            fragments.add(fragment to attributes)
        }

        override fun setIcon(icon: Icon?) {
            frameIcon = icon
        }
    }

    private fun stackFrame(name: String, path: String?, line: Int, hint: StackFramePresentationHint) = StackFrame().apply {
        id = 1
        this.name = name
        source = path?.let { Source().apply { this.path = it } }
        this.line = line
        column = 1
        presentationHint = hint
    }

    private fun testFrame(line: Int, depth: Int) = RobotCodeStackFrame(
        stackFrame("Project.Tests.Sample.My Test", "/project/tests/sample.robot", line, StackFramePresentationHint.NORMAL),
        FakeDebugServer(),
        depth,
        innermost = false
    )

    private fun presentationOf(frame: StackFrame): Recorder {
        return Recorder().also { RobotCodeStackFrame(frame, FakeDebugServer(), 0, false).customizePresentation(it) }
    }

    @Test
    fun aFrameWithASourceShowsItsNameAndThenFileAndLineInGrey() {
        val presentation = presentationOf(
            stackFrame("Sample.Do Something", "/project/tests/sample.robot", 15, StackFramePresentationHint.NORMAL)
        )

        assertEquals(
            listOf("Sample.Do Something" to REGULAR_ATTRIBUTES, ", sample.robot:15" to GRAYED_ATTRIBUTES),
            presentation.fragments
        )
        assertNotNull(presentation.frameIcon)
    }

    @Test
    fun aFrameWithoutASourceIsGrey() {
        val presentation = presentationOf(stackFrame("Project.Tests", null, 1, StackFramePresentationHint.SUBTLE))

        assertEquals(listOf("Project.Tests" to GRAYED_ATTRIBUTES), presentation.fragments)
        assertNull(presentation.frameIcon)
    }

    @Test
    fun theSameFrameAfterAStepIsEqual() {
        assertEquals(testFrame(line = 15, depth = 4).equalityObject, testFrame(line = 16, depth = 4).equalityObject)
    }

    @Test
    fun theFramesOfOneStackEntryAtDifferentDepthsAreNotEqual() {
        // the current line of a test and its definition line are two frames of one stack entry
        assertNotEquals(testFrame(line = 15, depth = 4).equalityObject, testFrame(line = 13, depth = 3).equalityObject)
    }

    @Test
    fun aFrameWithoutScopesShowsNothing() {
        val node = RecordingNode()

        testFrame(line = 15, depth = 4).computeChildren(node)

        val children = node.children.single()
        assertEquals(0, children.size())
        assertTrue(children.bottomGroups.isEmpty())
    }
}
