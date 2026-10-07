package dev.robotcode.robotcode4ij.configuration

import com.google.gson.Gson
import com.google.gson.JsonObject
import com.intellij.openapi.project.Project
import com.intellij.openapi.project.getProjectDataPath

/**
 * The settings below the `robotcode` key that the language server reads with `workspace/configuration`.
 *
 * Key names and defaults are those of the VS Code extension (`contributes.configuration` in `package.json`), for every
 * setting in the sections the server reads, apart from the inlay hints and `documentationServer.startOnDemand`.
 * Settings that only the clients use, for example for the debugger, runs, profiles or the language server process, are
 * not part of it.
 */
data class RobotCodeServerSettings(
    val robot: Robot = Robot(),
    val completion: Completion = Completion(),
    val inlayHints: InlayHints = InlayHints(),
    val analysis: Analysis = Analysis(),
    val robocop: Robocop = Robocop(),
    val workspace: Workspace = Workspace(),
    val documentationServer: DocumentationServer = DocumentationServer(),
    val experimental: Experimental = Experimental()
) {
    data class Robot(
        val args: List<String> = emptyList(),
        val paths: List<String> = emptyList(),
        val pythonPath: List<String> = emptyList(),
        val env: Map<String, String> = emptyMap(),
        val languages: List<String> = emptyList(),
        val variables: Map<String, String> = emptyMap(),
        val variableFiles: List<String> = emptyList(),
        val outputDir: String = "",
        val mode: String = "default"
    )

    data class Completion(
        val filterDefaultLanguage: Boolean = false,
        val headerStyle: String? = null,
        val hidePrivateKeywords: Boolean = true,
        val hideDeprecatedKeywords: Boolean = false
    )

    // Unlike in VS Code, off by default: IntelliJ shows inlay hints all the time once they are on, and has no mode that
    // shows them only while a key is held.
    data class InlayHints(
        val parameterNames: Boolean = false,
        val namespaces: Boolean = false
    )

    data class Analysis(
        val cache: AnalysisCache = AnalysisCache(),
        val robot: AnalysisRobot = AnalysisRobot(),
        val diagnosticModifiers: AnalysisDiagnosticModifiers = AnalysisDiagnosticModifiers(),
        val findUnusedReferences: Boolean = false,
        val diagnosticMode: String = DiagnosticMode.OPEN_FILES_ONLY.value,
        val progressMode: String = ProgressMode.OFF.value,
        val referencesCodeLens: Boolean = false
    )

    data class AnalysisCache(
        val saveLocation: String = CacheSaveLocation.WORKSPACE_STORAGE.value,
        val ignoredLibraries: List<String> = emptyList(),
        val ignoredVariables: List<String> = emptyList(),
        val ignoreArgumentsForLibrary: List<String> = emptyList(),
        val cacheNamespaces: Boolean = true
    )

    data class AnalysisRobot(
        val globalLibrarySearchOrder: List<String> = emptyList(),
        val loadLibraryTimeout: Int? = null
    )

    data class AnalysisDiagnosticModifiers(
        val ignore: List<String> = emptyList(),
        val error: List<String> = emptyList(),
        val warning: List<String> = emptyList(),
        val information: List<String> = emptyList(),
        val hint: List<String> = emptyList()
    )

    data class Robocop(
        val enabled: Boolean = true,
        val ignoreGitDir: Boolean = false,
        val configFile: String? = null,
        val ignoreFileConfig: Boolean = false
    )

    data class Workspace(
        val excludePatterns: List<String> = DEFAULT_EXCLUDE_PATTERNS
    ) {
        companion object {
            val DEFAULT_EXCLUDE_PATTERNS = listOf(
                ".hatch/",
                ".venv/",
                "node_modules/",
                ".pytest_cache/",
                "__pycache__/",
                ".mypy_cache/",
                ".robotcode_cache/"
            )
        }
    }

    data class DocumentationServer(
        val startPort: Int = 3100,
        val endPort: Int = 3199
    ) {
        // Unlike in VS Code, always true: IntelliJ has no documentation viewer, and the server still starts its
        // documentation server when something needs a documentation URL.
        val startOnDemand: Boolean = true
    }

    data class Experimental(
        val semanticModel: Boolean = false
    )

    /**
     * A choice of a setting with fixed choices, where [value] is the string the server reads. The first choice is the
     * default.
     */
    interface Choice {
        val value: String
    }

    enum class DiagnosticMode(override val value: String) : Choice {
        OPEN_FILES_ONLY("openFilesOnly"),
        WORKSPACE("workspace")
    }

    enum class ProgressMode(override val value: String) : Choice {
        OFF("off"),
        SIMPLE("simple"),
        DETAILED("detailed")
    }

    enum class CacheSaveLocation(override val value: String) : Choice {
        WORKSPACE_STORAGE("workspaceStorage"),
        WORKSPACE_FOLDER("workspaceFolder")
    }
}

/**
 * The choice stored as [value], or the default when [value] is none of the choices.
 */
inline fun <reified E> choiceOf(value: String?): E where E : Enum<E>, E : RobotCodeServerSettings.Choice {
    return enumValues<E>().firstOrNull { it.value == value } ?: enumValues<E>().first()
}

/**
 * Builds the settings tree that the plugin sends to the language server, with the `robotcode` key at its root.
 */
object RobotCodeServerSettingsMapper {
    // Without serializeNulls, so settings without a value, such as the header style, are left out.
    private val gson = Gson()

    fun toJsonTree(project: Project): JsonObject {
        return toJsonTree(RobotCodeProjectConfiguration.getInstance(project).state)
    }

    /**
     * The settings from the settings pages; every setting without a control keeps its default.
     */
    fun toJsonTree(state: RobotCodeProjectConfiguration.ProjectState): JsonObject {
        return toJsonTree(
            RobotCodeServerSettings(
                completion = RobotCodeServerSettings.Completion(
                    filterDefaultLanguage = state.completionFilterDefaultLanguage,
                    // the server would use a header style of only spaces as it is
                    headerStyle = state.completionHeaderStyle?.takeIf { it.isNotBlank() },
                    hidePrivateKeywords = state.completionHidePrivateKeywords,
                    hideDeprecatedKeywords = state.completionHideDeprecatedKeywords
                ),
                inlayHints = RobotCodeServerSettings.InlayHints(
                    parameterNames = state.inlayHintsParameterNames,
                    namespaces = state.inlayHintsNamespaces
                ),
                analysis = RobotCodeServerSettings.Analysis(
                    cache = RobotCodeServerSettings.AnalysisCache(
                        saveLocation = choiceOf<RobotCodeServerSettings.CacheSaveLocation>(
                            state.analysisCacheSaveLocation
                        ).value,
                        ignoredLibraries = entries(state.analysisCacheIgnoredLibraries),
                        ignoredVariables = entries(state.analysisCacheIgnoredVariables),
                        ignoreArgumentsForLibrary = entries(state.analysisCacheIgnoreArgumentsForLibrary)
                    ),
                    robot = RobotCodeServerSettings.AnalysisRobot(
                        globalLibrarySearchOrder = entries(state.analysisRobotGlobalLibrarySearchOrder),
                        loadLibraryTimeout = state.analysisRobotLoadLibraryTimeout.takeIf { it > 0 }
                    ),
                    diagnosticModifiers = RobotCodeServerSettings.AnalysisDiagnosticModifiers(
                        ignore = entries(state.analysisDiagnosticModifiersIgnore),
                        error = entries(state.analysisDiagnosticModifiersError),
                        warning = entries(state.analysisDiagnosticModifiersWarning),
                        information = entries(state.analysisDiagnosticModifiersInformation),
                        hint = entries(state.analysisDiagnosticModifiersHint)
                    ),
                    findUnusedReferences = state.analysisFindUnusedReferences,
                    diagnosticMode = choiceOf<RobotCodeServerSettings.DiagnosticMode>(
                        state.analysisDiagnosticMode
                    ).value,
                    progressMode = choiceOf<RobotCodeServerSettings.ProgressMode>(state.analysisProgressMode).value,
                    referencesCodeLens = state.analysisReferencesCodeLens
                ),
                robocop = RobotCodeServerSettings.Robocop(
                    enabled = state.robocopEnabled,
                    ignoreGitDir = state.robocopIgnoreGitDir,
                    configFile = state.robocopConfigFile?.takeIf { it.isNotBlank() },
                    ignoreFileConfig = state.robocopIgnoreFileConfig
                ),
                workspace = RobotCodeServerSettings.Workspace(
                    excludePatterns = entries(state.workspaceExcludePatterns)
                ),
                experimental = RobotCodeServerSettings.Experimental(
                    semanticModel = state.experimentalSemanticModel
                )
            )
        )
    }

    fun toJsonTree(settings: RobotCodeServerSettings): JsonObject {
        return JsonObject().apply { add("robotcode", gson.toJsonTree(settings)) }
    }

    /**
     * The initialization options of the `initialize` request: the storage folder of the project, which the server keeps
     * its analysis cache in unless the cache location is the project folder, the Python path and environment variables
     * that the server applies before it checks Robot Framework, and the settings tree.
     */
    fun toInitializationOptions(project: Project): JsonObject {
        val settings = toJsonTree(project)
        val robot = settings.getAsJsonObject("robotcode").getAsJsonObject("robot")
        return JsonObject().apply {
            addProperty("storageUri", project.getProjectDataPath("robotcode").toUri().toString())
            add("pythonPath", robot["pythonPath"].deepCopy())
            add("env", robot["env"].deepCopy())
            add("settings", settings)
        }
    }

    // The settings pages store trimmed entries without blank ones; a blank entry from an edited settings file would
    // reach the server as it is.
    private fun entries(list: List<String>): List<String> {
        return list.map { it.trim() }.filter { it.isNotEmpty() }
    }
}
