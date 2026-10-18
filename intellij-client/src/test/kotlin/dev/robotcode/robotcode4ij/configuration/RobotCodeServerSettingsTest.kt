package dev.robotcode.robotcode4ij.configuration

import com.google.gson.JsonElement
import com.google.gson.JsonParser
import com.google.gson.JsonPrimitive
import com.intellij.openapi.util.JDOMUtil
import com.intellij.util.xmlb.XmlSerializer
import dev.robotcode.robotcode4ij.execution.RobotOpenOutput
import dev.robotcode.robotcode4ij.execution.RobotOpenOutputTarget
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
                  "referencesCodeLens": true,
                  "fileCheckInterval": 2
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

    // every value of the Robot page differs from its default; the maps are not in alphabetical order
    private fun stateWithAllRobotValues(): RobotCodeProjectConfiguration.ProjectState {
        return RobotCodeProjectConfiguration.ProjectState().apply {
            robotArgs = "--loglevel DEBUG --name \"My Suite\""
            robotPaths = mutableListOf("tests")
            robotPythonPath = mutableListOf("libs")
            robotEnv = linkedMapOf("ZED" to "1", "ALPHA" to "2")
            robotLanguages = mutableListOf("de")
            robotVariables = linkedMapOf("SERVER" to "localhost", "ACCOUNT" to "admin")
            robotVariableFiles = mutableListOf("vars.py")
            robotOutputDir = "results/ide"
            robotMode = RobotCodeServerSettings.RobotMode.RPA.value
        }
    }

    @Test
    fun robotValuesSurviveASaveAndReloadInTheirOrder() {
        val state = stateWithAllRobotValues()

        val reloaded = saveAndReload(state)

        assertEquals(state, reloaded)
        assertEquals(listOf("ZED", "ALPHA"), reloaded.robotEnv.keys.toList())
        assertEquals(listOf("SERVER", "ACCOUNT"), reloaded.robotVariables.keys.toList())
    }

    // every value of the Run and Debug pages differs from its default
    private fun stateWithAllRunAndDebugValues() = RobotCodeProjectConfiguration.ProjectState().apply {
        debugLaunchWrapper = "xvfb-run -a"
        debugOutputMessages = true
        debugOutputLog = false
        debugOutputTimestamps = true
        runOpenOutputAfterRun = RobotOpenOutput.REPORT
        runOpenOutputTarget = RobotOpenOutputTarget.BROWSER
        runOpenOutputBrowser = "98ca6bdf-8d26-46d9-a5c7-41b1b6c44eb5"
    }

    @Test
    fun runAndDebugDefaultsAreThoseOfVSCode() {
        val state = RobotCodeProjectConfiguration.ProjectState()

        assertTrue(state.debugLaunchWrapper.isNullOrEmpty())
        assertFalse(state.debugOutputMessages)
        assertTrue(state.debugOutputLog)
        assertFalse(state.debugOutputTimestamps)
        assertEquals(RobotOpenOutput.NONE, state.runOpenOutputAfterRun)
        assertEquals(RobotOpenOutputTarget.BUILT_IN_PREVIEW, state.runOpenOutputTarget)
        assertTrue(state.runOpenOutputBrowser.isNullOrEmpty())
    }

    @Test
    fun runAndDebugValuesSurviveASaveAndReload() {
        val state = stateWithAllRunAndDebugValues()

        assertEquals(state, saveAndReload(state))
    }

    @Test
    fun runAndDebugValuesAreNotSentToTheLanguageServer() {
        assertEquals(
            RobotCodeServerSettingsMapper.toJsonTree(RobotCodeProjectConfiguration.ProjectState()),
            RobotCodeServerSettingsMapper.toJsonTree(stateWithAllRunAndDebugValues())
        )
    }

    @Test
    fun storedRobotValuesArrive() {
        val tree = RobotCodeServerSettingsMapper.toJsonTree(stateWithAllRobotValues())

        assertEquals(
            JsonParser.parseString(
                """
                {
                  "args": ["--loglevel", "DEBUG", "--name", "My Suite"],
                  "paths": ["tests"],
                  "pythonPath": ["libs"],
                  "env": {"ZED": "1", "ALPHA": "2"},
                  "languages": ["de"],
                  "variables": {"SERVER": "localhost", "ACCOUNT": "admin"},
                  "variableFiles": ["vars.py"],
                  "outputDir": "results/ide",
                  "mode": "rpa"
                }
                """
            ),
            tree["robotcode"].asJsonObject["robot"]
        )
        assertValueTypes(tree)
    }

    @Test
    fun blankRobotEntriesAndPairsWithoutANameAreLeftOut() {
        val state = RobotCodeProjectConfiguration.ProjectState().apply {
            robotArgs = "  "
            robotPaths = mutableListOf("", " tests ", " ")
            robotEnv = linkedMapOf("" to "x", " STAGE " to "dev")
            robotVariables = linkedMapOf(" " to "y")
            robotOutputDir = " "
        }

        val robot = robotcodeOf(state)["robot"].asJsonObject

        assertEquals(JsonParser.parseString("[]"), robot["args"])
        assertEquals(JsonParser.parseString("""["tests"]"""), robot["paths"])
        assertEquals(JsonParser.parseString("""{"STAGE": "dev"}"""), robot["env"])
        assertEquals(JsonParser.parseString("{}"), robot["variables"])
        assertEquals("", robot["outputDir"].asString)
    }

    @Test
    fun anUnknownModeIsTheDefault() {
        assertEquals(listOf("default", "rpa", "norpa"), RobotCodeServerSettings.RobotMode.entries.map { it.value })

        val state = RobotCodeProjectConfiguration.ProjectState().apply { robotMode = "RPA" }

        assertEquals("default", robotcodeOf(state)["robot"].asJsonObject["mode"].asString)
    }

    private val robocopConfigFile = File("robocop.toml").absolutePath

    // every value of the Analysis, Diagnostics and Robocop pages differs from its default
    private fun stateWithAllAnalysisValues(): RobotCodeProjectConfiguration.ProjectState {
        return RobotCodeProjectConfiguration.ProjectState().apply {
            analysisDiagnosticMode = RobotCodeServerSettings.DiagnosticMode.WORKSPACE.value
            analysisProgressMode = RobotCodeServerSettings.ProgressMode.DETAILED.value
            analysisFindUnusedReferences = true
            analysisReferencesCodeLens = true
            analysisFileCheckInterval = 2
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

    @Test
    fun rootsFollowThePythonPathEntries() {
        val state = RobotCodeProjectConfiguration.ProjectState().apply { robotPythonPath = mutableListOf("libs") }

        val withRoots = RobotCodeServerSettingsMapper.toJsonTree(state, listOf("/p", "/p/src"))
        assertEquals(
            JsonParser.parseString("""["libs", "/p", "/p/src"]"""),
            withRoots["robotcode"].asJsonObject["robot"].asJsonObject["pythonPath"]
        )
        // without roots, as with both switches off
        assertEquals(JsonParser.parseString("""["libs"]"""), robotcodeOf(state)["robot"].asJsonObject["pythonPath"])
    }
}
