package dev.robotcode.robotcode4ij.configuration

import com.intellij.openapi.components.BaseState
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.SimplePersistentStateComponent
import com.intellij.openapi.components.State
import com.intellij.openapi.components.Storage
import com.intellij.openapi.components.service
import com.intellij.openapi.options.Configurable
import com.intellij.openapi.options.ConfigurableProvider
import com.intellij.openapi.project.Project
import com.intellij.util.xmlb.annotations.XMap
import dev.robotcode.robotcode4ij.RobotCodeBundle
import dev.robotcode.robotcode4ij.configuration.SimplePersistentStateComponentHelper.delegate
import dev.robotcode.robotcode4ij.configuration.SimplePersistentStateComponentHelper.stringDelegate
import dev.robotcode.robotcode4ij.execution.RobotOpenOutput
import dev.robotcode.robotcode4ij.execution.RobotOpenOutputTarget
import dev.robotcode.robotcode4ij.publishRobotCodeSettingsChanged
import javax.swing.JComponent


class RobotCodeProjectSettingsConfigurableProvider : ConfigurableProvider() {
    override fun createConfigurable(): Configurable {
        return RobotCodeProjectSettingsConfigurable()
    }
}


/**
 * The "Robot Framework" node under Languages & Frameworks. It has no settings of its own yet, so it has no content, and
 * the settings dialog lists its sub-pages on its page instead.
 */
class RobotCodeProjectSettingsConfigurable : Configurable {
    override fun getDisplayName(): String = RobotCodeBundle.message("settings.robotframework.displayName")

    override fun createComponent(): JComponent? = null

    override fun isModified(): Boolean = false

    override fun apply() {
    }
}

@Service(Service.Level.PROJECT) @State(name = "ProjectSettings", storages = [Storage("robotcodeSettings.xml")])
class RobotCodeProjectConfiguration(private val project: Project) :
    SimplePersistentStateComponent<RobotCodeProjectConfiguration.ProjectState>(ProjectState()) {
    companion object {
        fun getInstance(project: Project): RobotCodeProjectConfiguration = project.service()
    }

    // also called when the settings file changes outside the IDE, for example through a VCS update
    override fun loadState(state: ProjectState) {
        super.loadState(state)
        project.publishRobotCodeSettingsChanged()
    }

    class ProjectState : BaseState() {
        var completionFilterDefaultLanguage by property(defaultValue = false)
        var completionHeaderStyle by string()
        var completionHidePrivateKeywords by property(defaultValue = true)
        var completionHideDeprecatedKeywords by property(defaultValue = false)
        var inlayHintsParameterNames by property(defaultValue = false)
        var inlayHintsNamespaces by property(defaultValue = false)

        // The choices are stored as the strings the server reads.
        var analysisDiagnosticMode by string(RobotCodeServerSettings.DiagnosticMode.OPEN_FILES_ONLY.value)
        var analysisProgressMode by string(RobotCodeServerSettings.ProgressMode.OFF.value)
        var analysisFindUnusedReferences by property(defaultValue = false)
        var analysisReferencesCodeLens by property(defaultValue = false)
        var analysisDiagnosticModifiersIgnore by list<String>()
        var analysisDiagnosticModifiersError by list<String>()
        var analysisDiagnosticModifiersWarning by list<String>()
        var analysisDiagnosticModifiersInformation by list<String>()
        var analysisDiagnosticModifiersHint by list<String>()
        var analysisRobotGlobalLibrarySearchOrder by list<String>()

        // 0 when no timeout is set
        var analysisRobotLoadLibraryTimeout by property(defaultValue = 0)
        var analysisCacheSaveLocation by string(RobotCodeServerSettings.CacheSaveLocation.WORKSPACE_STORAGE.value)
        var analysisCacheIgnoredLibraries by list<String>()
        var analysisCacheIgnoredVariables by list<String>()
        var analysisCacheIgnoreArgumentsForLibrary by list<String>()

        // Unlike the other lists, the default is not empty, so an emptied list differs from the default and is stored.
        var workspaceExcludePatterns by property(
            RobotCodeServerSettings.Workspace.DEFAULT_EXCLUDE_PATTERNS.toMutableList()
        ) { it == RobotCodeServerSettings.Workspace.DEFAULT_EXCLUDE_PATTERNS }
        var experimentalSemanticModel by property(defaultValue = false)
        var robocopEnabled by property(defaultValue = true)

        // an absolute path
        var robocopConfigFile by string()
        var robocopIgnoreGitDir by property(defaultValue = false)
        var robocopIgnoreFileConfig by property(defaultValue = false)

        // the "Robot" page; the arguments as the command line the user typed, the mode as the string the server reads
        var robotArgs by string()
        var robotPaths by list<String>()
        var robotPythonPath by list<String>()

        // ordered maps keep their order only with XMap
        @get:XMap(
            propertyElementName = "robotEnv", entryTagName = "variable", keyAttributeName = "name",
            valueAttributeName = "value"
        )
        var robotEnv: MutableMap<String, String> by linkedMap()
        var robotLanguages by list<String>()

        @get:XMap(
            propertyElementName = "robotVariables", entryTagName = "variable", keyAttributeName = "name",
            valueAttributeName = "value"
        )
        var robotVariables: MutableMap<String, String> by linkedMap()
        var robotVariableFiles by list<String>()
        var robotOutputDir by string()
        var robotMode by string(RobotCodeServerSettings.RobotMode.DEFAULT.value)

        // the "Debug" page, with the defaults of VS Code; the launch wrapper as the command line the user typed
        var debugLaunchWrapper by string()
        var debugOutputMessages by property(defaultValue = false)
        var debugOutputLog by property(defaultValue = true)
        var debugOutputTimestamps by property(defaultValue = false)

        // the "Run" page, with the browser's id for RobotOpenOutputTarget.BROWSER
        var runOpenOutputAfterRun by enum(RobotOpenOutput.NONE)
        var runOpenOutputTarget by enum(RobotOpenOutputTarget.BUILT_IN_PREVIEW)
        var runOpenOutputBrowser by string()
    }

    var completionFilterDefaultLanguage by delegate(ProjectState::completionFilterDefaultLanguage)
    var completionHeaderStyle by stringDelegate(ProjectState::completionHeaderStyle)
    var completionHidePrivateKeywords by delegate(ProjectState::completionHidePrivateKeywords)
    var completionHideDeprecatedKeywords by delegate(ProjectState::completionHideDeprecatedKeywords)
    var inlayHintsParameterNames by delegate(ProjectState::inlayHintsParameterNames)
    var inlayHintsNamespaces by delegate(ProjectState::inlayHintsNamespaces)
    var analysisDiagnosticMode by stringDelegate(ProjectState::analysisDiagnosticMode)
    var analysisProgressMode by stringDelegate(ProjectState::analysisProgressMode)
    var analysisFindUnusedReferences by delegate(ProjectState::analysisFindUnusedReferences)
    var analysisReferencesCodeLens by delegate(ProjectState::analysisReferencesCodeLens)
    var analysisDiagnosticModifiersIgnore by delegate(ProjectState::analysisDiagnosticModifiersIgnore)
    var analysisDiagnosticModifiersError by delegate(ProjectState::analysisDiagnosticModifiersError)
    var analysisDiagnosticModifiersWarning by delegate(ProjectState::analysisDiagnosticModifiersWarning)
    var analysisDiagnosticModifiersInformation by delegate(ProjectState::analysisDiagnosticModifiersInformation)
    var analysisDiagnosticModifiersHint by delegate(ProjectState::analysisDiagnosticModifiersHint)
    var analysisRobotGlobalLibrarySearchOrder by delegate(ProjectState::analysisRobotGlobalLibrarySearchOrder)
    var analysisRobotLoadLibraryTimeout by delegate(ProjectState::analysisRobotLoadLibraryTimeout)
    var analysisCacheSaveLocation by stringDelegate(ProjectState::analysisCacheSaveLocation)
    var analysisCacheIgnoredLibraries by delegate(ProjectState::analysisCacheIgnoredLibraries)
    var analysisCacheIgnoredVariables by delegate(ProjectState::analysisCacheIgnoredVariables)
    var analysisCacheIgnoreArgumentsForLibrary by delegate(ProjectState::analysisCacheIgnoreArgumentsForLibrary)
    var workspaceExcludePatterns by delegate(ProjectState::workspaceExcludePatterns)
    var experimentalSemanticModel by delegate(ProjectState::experimentalSemanticModel)
    var robocopEnabled by delegate(ProjectState::robocopEnabled)
    var robocopConfigFile by stringDelegate(ProjectState::robocopConfigFile)
    var robocopIgnoreGitDir by delegate(ProjectState::robocopIgnoreGitDir)
    var robocopIgnoreFileConfig by delegate(ProjectState::robocopIgnoreFileConfig)
    var robotArgs by stringDelegate(ProjectState::robotArgs)
    var robotPaths by delegate(ProjectState::robotPaths)
    var robotPythonPath by delegate(ProjectState::robotPythonPath)
    var robotEnv by delegate(ProjectState::robotEnv)
    var robotLanguages by delegate(ProjectState::robotLanguages)
    var robotVariables by delegate(ProjectState::robotVariables)
    var robotVariableFiles by delegate(ProjectState::robotVariableFiles)
    var robotOutputDir by stringDelegate(ProjectState::robotOutputDir)
    var robotMode by stringDelegate(ProjectState::robotMode)
    var debugLaunchWrapper by stringDelegate(ProjectState::debugLaunchWrapper)
    var debugOutputMessages by delegate(ProjectState::debugOutputMessages)
    var debugOutputLog by delegate(ProjectState::debugOutputLog)
    var debugOutputTimestamps by delegate(ProjectState::debugOutputTimestamps)
    var runOpenOutputAfterRun by delegate(ProjectState::runOpenOutputAfterRun)
    var runOpenOutputTarget by delegate(ProjectState::runOpenOutputTarget)
    var runOpenOutputBrowser by stringDelegate(ProjectState::runOpenOutputBrowser)
}
