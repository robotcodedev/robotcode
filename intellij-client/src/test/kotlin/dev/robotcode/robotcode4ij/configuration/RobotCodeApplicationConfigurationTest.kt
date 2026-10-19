package dev.robotcode.robotcode4ij.configuration

import com.intellij.openapi.components.State
import com.intellij.util.xmlb.XmlSerializer
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class RobotCodeApplicationConfigurationTest {

    @Test
    fun stateIsStoredInTheConfigurationOfTheIde() {
        val state = RobotCodeApplicationConfiguration::class.java.getAnnotation(State::class.java)

        assertEquals("RobotCodeApplicationSettings", state.name)
        assertEquals(listOf("robotcode.xml"), state.storages.map { it.value })
    }

    @Test
    fun onlyAChangedValueIsStored() {
        assertTrue(RobotCodeApplicationConfiguration.ApplicationState().showWhatsNewOnUpdate)
        assertTrue(XmlSerializer.serialize(RobotCodeApplicationConfiguration.ApplicationState()).children.isEmpty())

        val restored = XmlSerializer.deserialize(
            XmlSerializer.serialize(
                RobotCodeApplicationConfiguration.ApplicationState().apply { showWhatsNewOnUpdate = false }
            ),
            RobotCodeApplicationConfiguration.ApplicationState::class.java
        )

        assertFalse(restored.showWhatsNewOnUpdate)
    }
}
