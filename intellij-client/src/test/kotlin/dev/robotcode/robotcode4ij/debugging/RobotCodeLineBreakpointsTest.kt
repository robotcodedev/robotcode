package dev.robotcode.robotcode4ij.debugging

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class RobotCodeLineBreakpointsTest {

    // a line breakpoint whose position the IDE changes when it is moved
    private class Breakpoint(var file: String?, var line: Int)

    private val breakpoints = RobotCodeLineBreakpoints<Breakpoint, String>({ it.file }, { it.line })

    private fun lines(file: String) = breakpoints.entries(file).map { it.line }

    @Test
    fun registeredBreakpointsMakeUpTheListOfTheirFile() {
        val first = Breakpoint("a.robot", 3)
        val second = Breakpoint("a.robot", 1)
        val other = Breakpoint("b.robot", 5)

        assertEquals(setOf("a.robot"), breakpoints.register(first))
        breakpoints.register(second)
        breakpoints.register(other)

        assertEquals(listOf(3, 1), lines("a.robot"))
        assertEquals(listOf(5), lines("b.robot"))
        assertEquals(setOf("a.robot", "b.robot"), breakpoints.files)
    }

    @Test
    fun disablingTheLastBreakpointOfAFileLeavesAnEmptyList() {
        val only = Breakpoint("a.robot", 3)
        breakpoints.register(only)

        assertEquals(setOf("a.robot"), breakpoints.unregister(only))

        assertEquals(listOf<Int>(), lines("a.robot"))
        assertEquals(setOf("a.robot"), breakpoints.files)
    }

    @Test
    fun mutingAndUnmutingUnregistersAndRegistersAll() {
        val all = listOf(Breakpoint("a.robot", 3), Breakpoint("a.robot", 7), Breakpoint("b.robot", 5))
        all.forEach { breakpoints.register(it) }

        all.forEach { breakpoints.unregister(it) }
        assertEquals(listOf<Int>(), lines("a.robot"))
        assertEquals(listOf<Int>(), lines("b.robot"))

        all.forEach { breakpoints.register(it) }
        assertEquals(listOf(3, 7), lines("a.robot"))
        assertEquals(listOf(5), lines("b.robot"))
    }

    @Test
    fun aMovedBreakpointIsListedAtItsNewLine() {
        val moved = Breakpoint("a.robot", 3)
        breakpoints.register(moved)

        // the IDE moves the breakpoint, then unregisters and registers it again
        moved.line = 8
        breakpoints.unregister(moved)
        breakpoints.register(moved)

        assertEquals(listOf(8), lines("a.robot"))
    }

    @Test
    fun aBreakpointMovedToAnotherFileLeavesAnEmptyListBehind() {
        val moved = Breakpoint("a.robot", 3)
        breakpoints.register(moved)

        moved.file = "b.robot"
        assertEquals(setOf("a.robot"), breakpoints.unregister(moved))
        assertEquals(setOf("b.robot"), breakpoints.register(moved))

        assertEquals(listOf<Int>(), lines("a.robot"))
        assertEquals(listOf(3), lines("b.robot"))
    }

    @Test
    fun aRemovedBreakpointIsNoLongerListed() {
        val kept = Breakpoint("a.robot", 3)
        val removed = Breakpoint("a.robot", 5)
        breakpoints.register(kept)
        breakpoints.register(removed)

        breakpoints.unregister(removed)

        assertEquals(listOf(3), lines("a.robot"))
        assertEquals(setOf<String>(), breakpoints.unregister(removed))
    }

    @Test
    fun theRunToCursorTargetIsListedUntilItIsCleared() {
        breakpoints.register(Breakpoint("a.robot", 3))

        assertTrue(breakpoints.setTarget("a.robot", 9))
        assertEquals(listOf(3, 9), lines("a.robot"))
        assertNull(breakpoints.entries("a.robot").last().breakpoint)

        assertEquals("a.robot", breakpoints.clearTarget())
        assertEquals(listOf(3), lines("a.robot"))
        assertNull(breakpoints.clearTarget())
    }

    @Test
    fun aTargetInAnotherFileIsListedThere() {
        assertTrue(breakpoints.setTarget("c.robot", 2))

        assertEquals(setOf("c.robot"), breakpoints.files)
        assertEquals(listOf(2), lines("c.robot"))
    }

    @Test
    fun noTargetOnALineWithABreakpoint() {
        breakpoints.register(Breakpoint("a.robot", 3))

        assertFalse(breakpoints.setTarget("a.robot", 3))

        assertEquals(listOf(3), lines("a.robot"))
        assertNull(breakpoints.clearTarget())
    }
}
