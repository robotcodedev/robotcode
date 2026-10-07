package dev.robotcode.robotcode4ij.configuration

import com.google.gson.JsonElement
import com.google.gson.JsonParser
import com.intellij.openapi.util.JDOMUtil
import com.intellij.util.xmlb.XmlSerializer
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class RobotCodeServerSettingsTest {

    // default-settings.json holds the defaults of the VS Code extension's settings (contributes.configuration in
    // package.json), with two exceptions: documentationServer.startOnDemand is always true in IntelliJ, and the inlay
    // hints are off. When a default changes in package.json, change it there and in RobotCodeServerSettings.
    private val defaultSettings: JsonElement =
        javaClass.getResourceAsStream("/settings/default-settings.json")!!.reader().use { JsonParser.parseReader(it) }

    @Test
    fun defaultSettingsAreTheDefaultsOfVSCode() {
        val tree = RobotCodeServerSettingsMapper.toJsonTree(RobotCodeServerSettings())

        assertEquals(defaultSettings, tree)
        assertValueTypes(tree)
    }

    @Test
    fun projectWithoutStoredSettingsGetsTheDefaults() {
        val tree = RobotCodeServerSettingsMapper.toJsonTree(RobotCodeProjectConfiguration.ProjectState())

        assertEquals(defaultSettings, tree)
    }

    // Earlier versions stored only values that differ from their defaults, here a switched-on namespace hint.
    @Test
    fun settingsStoredByAnEarlierVersionKeepTheirMeaning() {
        val state = XmlSerializer.deserialize(
            JDOMUtil.load(
                """
                <component name="ProjectSettings">
                  <option name="completionFilterDefaultLanguage" value="true" />
                  <option name="completionHeaderStyle" value="*** {name}" />
                  <option name="inlayHintsNamespaces" value="true" />
                </component>
                """
            ),
            RobotCodeProjectConfiguration.ProjectState::class.java
        )

        assertTrue(state.completionFilterDefaultLanguage)
        assertEquals("*** {name}", state.completionHeaderStyle)
        assertTrue(state.completionHidePrivateKeywords)
        assertFalse(state.completionHideDeprecatedKeywords)
        assertFalse(state.inlayHintsParameterNames)
        assertTrue(state.inlayHintsNamespaces)

        val robotcode = RobotCodeServerSettingsMapper.toJsonTree(state)["robotcode"].asJsonObject
        assertEquals(
            JsonParser.parseString(
                """
                {
                  "filterDefaultLanguage": true,
                  "headerStyle": "*** {name}",
                  "hidePrivateKeywords": true,
                  "hideDeprecatedKeywords": false
                }
                """
            ),
            robotcode["completion"]
        )
        assertEquals(
            JsonParser.parseString("""{"parameterNames": false, "namespaces": true}"""),
            robotcode["inlayHints"]
        )
    }

    @Test
    fun storedValuesArrive() {
        val state = RobotCodeProjectConfiguration.ProjectState().apply {
            completionFilterDefaultLanguage = true
            completionHeaderStyle = "*** {name}"
            completionHidePrivateKeywords = false
            completionHideDeprecatedKeywords = true
            inlayHintsParameterNames = true
            inlayHintsNamespaces = true
        }

        val tree = RobotCodeServerSettingsMapper.toJsonTree(state)

        val expected = defaultSettings.deepCopy().asJsonObject
        expected["robotcode"].asJsonObject.apply {
            add(
                "completion",
                JsonParser.parseString(
                    """
                    {
                      "filterDefaultLanguage": true,
                      "headerStyle": "*** {name}",
                      "hidePrivateKeywords": false,
                      "hideDeprecatedKeywords": true
                    }
                    """
                )
            )
            add("inlayHints", JsonParser.parseString("""{"parameterNames": true, "namespaces": true}"""))
        }
        assertEquals(expected, tree)
        assertValueTypes(tree)
    }

    @Test
    fun blankHeaderStyleIsLeftOut() {
        for (headerStyle in listOf("", " ", " \t ")) {
            val state = RobotCodeProjectConfiguration.ProjectState().apply { completionHeaderStyle = headerStyle }

            val completion = RobotCodeServerSettingsMapper.toJsonTree(state)["robotcode"].asJsonObject["completion"]

            assertFalse("header style '$headerStyle' is sent", completion.asJsonObject.has("headerStyle"))
        }
    }

    // The server parses integers only, and equality of JsonElements would take 3100.0 for 3100.
    private fun assertValueTypes(element: JsonElement, path: String = "") {
        when {
            element.isJsonObject -> element.asJsonObject.entrySet().forEach { (key, value) ->
                assertValueTypes(value, "$path.$key")
            }

            element.isJsonArray -> element.asJsonArray.forEachIndexed { index, item ->
                assertFalse("$path[$index] is null", item.isJsonNull)
                assertFalse("$path[$index] is empty", item.isJsonPrimitive && item.asString.isBlank())
                assertValueTypes(item, "$path[$index]")
            }

            element.isJsonPrimitive && element.asJsonPrimitive.isNumber ->
                assertTrue("$path is not an integer: $element", element.asString.matches(Regex("-?\\d+")))
        }
    }
}
