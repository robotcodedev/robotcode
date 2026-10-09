package dev.robotcode.robotcode4ij.execution

import dev.robotcode.robotcode4ij.testing.RobotCodeTestItem
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class RobotCodeRunMarkerKindTest {

    private fun item(type: String, children: Array<RobotCodeTestItem>? = null) =
        RobotCodeTestItem(type = type, id = type, name = type, longname = type, children = children)

    @Test
    fun testsAndTasksAreLeaves() {
        assertEquals(RunMarkerKind.LEAF, runMarkerKind(item("test")))
        assertEquals(RunMarkerKind.LEAF, runMarkerKind(item("task")))
    }

    @Test
    fun suiteNeedsChildren() {
        assertEquals(RunMarkerKind.SUITE, runMarkerKind(item("suite", arrayOf(item("task")))))
        assertNull(runMarkerKind(item("suite", arrayOf())))
        assertNull(runMarkerKind(item("suite")))
    }

    @Test
    fun otherTypesGetNoMarker() {
        assertNull(runMarkerKind(item("keyword")))
        assertNull(runMarkerKind(item("workspace", arrayOf(item("suite")))))
    }
}
