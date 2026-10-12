package dev.robotcode.robotcode4ij.debugging.breakpoints

import com.intellij.util.xmlb.XmlSerializer
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Test

class RobotCodeLineBreakpointPropertiesTest {

    // stores the properties as the project does and loads them into new ones
    private fun storedAndLoaded(properties: RobotCodeLineBreakpointProperties): RobotCodeLineBreakpointProperties {
        val element = XmlSerializer.serialize(properties.state)
        val stored = XmlSerializer.deserialize(element, RobotCodeLineBreakpointProperties::class.java)
        return RobotCodeLineBreakpointProperties().apply { loadState(stored) }
    }

    @Test
    fun aHitCountIsKept() {
        val loaded = storedAndLoaded(RobotCodeLineBreakpointProperties().apply { hitCount = ">= 3" })

        assertEquals(">= 3", loaded.hitCount)
    }

    @Test
    fun propertiesWithoutAHitCountLoad() {
        val loaded = storedAndLoaded(RobotCodeLineBreakpointProperties())

        assertNull(loaded.hitCount)
    }

    // the IDE loads the stored breakpoints of a project into the properties that the type creates
    @Test
    fun theTypeCreatesPropertiesForStoredBreakpoints() {
        assertNotNull(RobotCodeLineBreakpointType().createProperties())
    }
}
