package dev.robotcode.robotcode4ij.configuration

import com.intellij.openapi.components.State
import com.intellij.openapi.components.StoragePathMacros
import com.intellij.util.xmlb.XmlSerializer
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class RobotCodePersonalConfigurationTest {

    @Test
    fun stateIsStoredInTheWorkspaceFile() {
        val state = RobotCodePersonalConfiguration::class.java.getAnnotation(State::class.java)

        assertEquals("RobotCodePersonalSettings", state.name)
        assertEquals(listOf(StoragePathMacros.WORKSPACE_FILE), state.storages.map { it.value })
    }

    @Test
    fun stateSurvivesTheXmlSerializer() {
        val state = RobotCodePersonalConfiguration.PersonalState().apply {
            extraArgs = "--config \"team settings.toml\""
            languageServerExtraArgs = "--log --log-level INFO"
            profiles = mutableListOf("dev", "ci")
        }

        val restored = XmlSerializer.deserialize(
            XmlSerializer.serialize(state),
            RobotCodePersonalConfiguration.PersonalState::class.java
        )

        assertEquals(state, restored)
        assertTrue(XmlSerializer.serialize(RobotCodePersonalConfiguration.PersonalState()).children.isEmpty())
    }

    @Test
    fun quotedArgumentStaysOneArgument() {
        val settings = RobotCodePersonalConfiguration().apply { extraArgs = "--config \"team settings.toml\"" }

        assertEquals(listOf("--config", "team settings.toml"), settings.extraArgsList)
        assertEquals(emptyList<String>(), settings.languageServerExtraArgsList)
    }
}
