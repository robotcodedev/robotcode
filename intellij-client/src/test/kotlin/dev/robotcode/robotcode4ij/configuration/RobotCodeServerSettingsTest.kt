package dev.robotcode.robotcode4ij.configuration

import com.google.gson.JsonElement
import com.google.gson.JsonParser
import com.google.gson.JsonPrimitive
import com.intellij.openapi.util.JDOMUtil
import com.intellij.util.xmlb.XmlSerializer
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

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
        val defaults = defaultSettings.asJsonObject["robotcode"].asJsonObject
        for (section in listOf("robot", "analysis", "robocop", "workspace", "documentationServer", "experimental")) {
            assertEquals(section, defaults[section], robotcode[section])
        }
    }

    @Test
    fun everyStoredValueSurvivesASaveAndReload() {
        val state = stateWithAllAnalysisValues().apply {
            completionFilterDefaultLanguage = true
            completionHeaderStyle = "*** {name}"
            completionHidePrivateKeywords = false
            completionHideDeprecatedKeywords = true
            inlayHintsParameterNames = true
            inlayHintsNamespaces = true
        }

        val reloaded = saveAndReload(state)

        assertEquals(state, reloaded)
        assertEquals(robotcodeOf(state), robotcodeOf(reloaded))
    }

    @Test
    fun defaultsAreNotStored() {
        assertTrue(XmlSerializer.serialize(RobotCodeProjectConfiguration.ProjectState()).children.isEmpty())
    }

    @Test
    fun emptiedExcludePatternsStayEmpty() {
        val state = RobotCodeProjectConfiguration.ProjectState().apply { workspaceExcludePatterns = mutableListOf() }

        val reloaded = saveAndReload(state)

        assertTrue(reloaded.workspaceExcludePatterns.isEmpty())
        val workspace = robotcodeOf(reloaded)["workspace"]
        assertEquals(JsonParser.parseString("""{"excludePatterns": []}"""), workspace)
    }

    @Test
    fun storedAnalysisValuesArrive() {
        val tree = RobotCodeServerSettingsMapper.toJsonTree(stateWithAllAnalysisValues())

        val robotcode = tree["robotcode"].asJsonObject
        assertEquals(
            JsonParser.parseString(
                """
                {
                  "cache": {
                    "saveLocation": "workspaceFolder",
                    "ignoredLibraries": ["MyLib"],
                    "ignoredVariables": ["**/variables/*.py"],
                    "ignoreArgumentsForLibrary": ["OtherLib"],
                    "cacheNamespaces": true
                  },
                  "robot": {
                    "globalLibrarySearchOrder": ["SeleniumLibrary", "Browser"],
                    "loadLibraryTimeout": 120
                  },
                  "diagnosticModifiers": {
                    "ignore": ["KeywordNotFound"],
                    "error": ["MultipleKeywords"],
                    "warning": ["VariableNotFound"],
                    "information": ["DeprecatedKeyword"],
                    "hint": ["PossibleCircularImport"]
                  },
                  "findUnusedReferences": true,
                  "diagnosticMode": "workspace",
                  "progressMode": "detailed",
                  "referencesCodeLens": true
                }
                """
            ),
            robotcode["analysis"]
        )
        assertEquals(
            JsonParser.parseString(
                """
                {
                  "enabled": false,
                  "ignoreGitDir": true,
                  "configFile": ${JsonPrimitive(robocopConfigFile)},
                  "ignoreFileConfig": true
                }
                """
            ),
            robotcode["robocop"]
        )
        assertEquals(JsonParser.parseString("""{"excludePatterns": ["generated/"]}"""), robotcode["workspace"])
        assertEquals(JsonParser.parseString("""{"semanticModel": true}"""), robotcode["experimental"])
        assertValueTypes(tree)
    }

    // The server reads these strings; a different one breaks the whole robotcode section there.
    @Test
    fun choicesAreTheStringsTheServerReads() {
        assertEquals(
            listOf("openFilesOnly", "workspace"),
            RobotCodeServerSettings.DiagnosticMode.entries.map { it.value }
        )
        assertEquals(listOf("off", "simple", "detailed"), RobotCodeServerSettings.ProgressMode.entries.map { it.value })
        assertEquals(
            listOf("workspaceStorage", "workspaceFolder"),
            RobotCodeServerSettings.CacheSaveLocation.entries.map { it.value }
        )

        val state = RobotCodeProjectConfiguration.ProjectState().apply {
            analysisDiagnosticMode = "Workspace"
            analysisProgressMode = "verbose"
            analysisCacheSaveLocation = null
        }
        val analysis = robotcodeOf(state)["analysis"].asJsonObject
        assertEquals("openFilesOnly", analysis["diagnosticMode"].asString)
        assertEquals("off", analysis["progressMode"].asString)
        assertEquals("workspaceStorage", analysis["cache"].asJsonObject["saveLocation"].asString)
    }

    @Test
    fun blankListEntriesAreLeftOut() {
        val state = RobotCodeProjectConfiguration.ProjectState().apply {
            analysisDiagnosticModifiersIgnore = mutableListOf("", " KeywordNotFound ", " \t ")
            workspaceExcludePatterns = mutableListOf(" ", "generated/")
        }

        val robotcode = robotcodeOf(state)

        val modifiers = robotcode["analysis"].asJsonObject["diagnosticModifiers"].asJsonObject
        assertEquals(JsonParser.parseString("""["KeywordNotFound"]"""), modifiers["ignore"])
        val excludePatterns = robotcode["workspace"].asJsonObject["excludePatterns"]
        assertEquals(JsonParser.parseString("""["generated/"]"""), excludePatterns)
    }

    @Test
    fun unsetTimeoutAndConfigurationFileAreLeftOut() {
        val robotcode = robotcodeOf(RobotCodeProjectConfiguration.ProjectState())

        assertFalse(robotcode["analysis"].asJsonObject["robot"].asJsonObject.has("loadLibraryTimeout"))
        assertFalse(robotcode["robocop"].asJsonObject.has("configFile"))
    }

    private val robocopConfigFile = File("robocop.toml").absolutePath

    // every value of the Analysis, Diagnostics and Robocop pages differs from its default
    private fun stateWithAllAnalysisValues(): RobotCodeProjectConfiguration.ProjectState {
        return RobotCodeProjectConfiguration.ProjectState().apply {
            analysisDiagnosticMode = RobotCodeServerSettings.DiagnosticMode.WORKSPACE.value
            analysisProgressMode = RobotCodeServerSettings.ProgressMode.DETAILED.value
            analysisFindUnusedReferences = true
            analysisReferencesCodeLens = true
            analysisDiagnosticModifiersIgnore = mutableListOf("KeywordNotFound")
            analysisDiagnosticModifiersError = mutableListOf("MultipleKeywords")
            analysisDiagnosticModifiersWarning = mutableListOf("VariableNotFound")
            analysisDiagnosticModifiersInformation = mutableListOf("DeprecatedKeyword")
            analysisDiagnosticModifiersHint = mutableListOf("PossibleCircularImport")
            analysisRobotGlobalLibrarySearchOrder = mutableListOf("SeleniumLibrary", "Browser")
            analysisRobotLoadLibraryTimeout = 120
            analysisCacheSaveLocation = RobotCodeServerSettings.CacheSaveLocation.WORKSPACE_FOLDER.value
            analysisCacheIgnoredLibraries = mutableListOf("MyLib")
            analysisCacheIgnoredVariables = mutableListOf("**/variables/*.py")
            analysisCacheIgnoreArgumentsForLibrary = mutableListOf("OtherLib")
            workspaceExcludePatterns = mutableListOf("generated/")
            experimentalSemanticModel = true
            robocopEnabled = false
            robocopConfigFile = this@RobotCodeServerSettingsTest.robocopConfigFile
            robocopIgnoreGitDir = true
            robocopIgnoreFileConfig = true
        }
    }

    private fun robotcodeOf(state: RobotCodeProjectConfiguration.ProjectState) =
        RobotCodeServerSettingsMapper.toJsonTree(state)["robotcode"].asJsonObject

    private fun saveAndReload(
        state: RobotCodeProjectConfiguration.ProjectState
    ): RobotCodeProjectConfiguration.ProjectState {
        val element = XmlSerializer.serialize(state)
        assertNotEquals(0, element.children.size)
        return XmlSerializer.deserialize(
            JDOMUtil.load(JDOMUtil.write(element)),
            RobotCodeProjectConfiguration.ProjectState::class.java
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
